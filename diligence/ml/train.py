"""Reproducible training and evaluation for the startup outcome model.

Run with ``python -m diligence.ml.train``. The script:

1. Loads ``data/CleanStartups.csv`` through the same ingestion code the API uses.
2. Audits data quality (duplicates, missing values, class balance).
3. Makes one stratified 80/20 train/test split (``random_state=42``).
4. Tunes a class-weighted Random Forest with 5-fold CV on the training split.
5. Wraps it in sigmoid probability calibration (5-fold, training split only).
6. Compares it with baselines using repeated stratified 5x3 CV and the hold-out set.
7. Measures grouped permutation importance on the hold-out set.
8. Saves the pipeline, metadata, metrics and per-record evaluation splits.

All numbers shown by the application come from the files written here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import (
    GridSearchCV,
    RepeatedStratifiedKFold,
    StratifiedKFold,
    cross_val_predict,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from diligence.data.ingest import build_records, map_columns, read_csv_bytes
from diligence.ml.features import StartupFeatureBuilder
from diligence.ml.schema import MODEL_COLUMNS

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "CleanStartups.csv"
MODEL_DIR = ROOT / "model"
RANDOM_STATE = 42
TEST_SIZE = 0.2
CLASSES = ["Dead", "Exited", "Operating"]
EXCLUDED_COLUMNS = {
    "Unnamed: 0": "row index from an earlier export; ordered in a way that correlates with outcome",
    "Company": "identifier, not a predictive attribute",
    "Description": "free text; not used by this model",
    "Logo": "URL that tends to disappear when a company shuts down (outcome leakage)",
    "Website": "URL that tends to disappear when a company shuts down (outcome leakage)",
    "SeedDBMattermarkProfile": "profile URL, identifier only",
    "CrunchBaseAngelListProfile": "profile URL, identifier only",
    "Founders1-4": "listing completeness depends on how well a company is documented after the fact",
    "Investors1-4": "listing completeness depends on how well a company is documented after the fact",
}


def load_training_frame(path: Path = DATA_PATH) -> tuple[pd.DataFrame, pd.Series, list[dict[str, Any]]]:
    """Return model inputs, target labels and the parsed records."""
    frame = read_csv_bytes(path.read_bytes())
    records = build_records(frame, map_columns(list(frame.columns)))
    unusable = [record["row_number"] for record in records if record["issues"] or record["status"] not in CLASSES]
    if unusable:
        raise ValueError(f"Rows without a valid model input or outcome label: {unusable[:10]}")
    inputs = pd.DataFrame([record["model_input"] for record in records], columns=MODEL_COLUMNS)
    target = pd.Series([record["status"] for record in records], name="status")
    return inputs, target, records


def data_quality_report(path: Path, inputs: pd.DataFrame, target: pd.Series) -> dict[str, Any]:
    raw = pd.read_csv(path)
    raw = raw.drop(columns=[column for column in raw.columns if column.startswith("Unnamed:")])
    hashable = inputs.assign(markets=inputs["markets"].map(lambda items: "|".join(sorted(items))))
    return {
        "rows": int(len(raw)),
        "columns": int(raw.shape[1]),
        "duplicate_rows": int(raw.duplicated().sum()),
        "duplicate_company_names": int(raw["Company"].duplicated().sum()),
        "identical_model_inputs": int(hashable.duplicated().sum()),
        "missing_share": {column: round(float(raw[column].isna().mean()), 4) for column in raw.columns},
        "funding_reported_zero": int((inputs["total_funding"] == 0).sum()),
        "funding_missing": int(inputs["total_funding"].isna().sum()),
        "class_counts": {label: int(count) for label, count in target.value_counts().items()},
        "year_range": [int(inputs["year"].min()), int(inputs["year"].max())],
        "status_by_year": {
            str(year): {label: int(count) for label, count in group.value_counts().items()}
            for year, group in target.groupby(inputs["year"])
        },
    }


def random_forest() -> Pipeline:
    return Pipeline(
        [
            ("features", StartupFeatureBuilder()),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=300,
                    class_weight="balanced_subsample",
                    random_state=RANDOM_STATE,
                    n_jobs=1,
                ),
            ),
        ]
    )


def calibrated(estimator: Pipeline) -> CalibratedClassifierCV:
    return CalibratedClassifierCV(
        estimator,
        method="sigmoid",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    )


def candidates(rf_params: dict[str, Any]) -> dict[str, tuple[Any, str]]:
    """Return ``name -> (estimator, decision rule)``.

    Models with probability estimates on the natural scale use the balanced
    rule; the class-weighted forest already rebalances inside training, and
    the dummy baselines are defined by their own prediction strategy, so
    those use plain argmax.
    """
    rf = random_forest().set_params(**rf_params)
    return {
        "majority_class": (
            Pipeline([("features", StartupFeatureBuilder()), ("model", DummyClassifier(strategy="prior"))]),
            "argmax",
        ),
        "stratified_random": (
            Pipeline(
                [("features", StartupFeatureBuilder()), ("model", DummyClassifier(strategy="stratified", random_state=RANDOM_STATE))]
            ),
            "argmax",
        ),
        "logistic_regression": (
            Pipeline(
                [
                    ("features", StartupFeatureBuilder()),
                    ("scale", StandardScaler()),
                    ("model", LogisticRegression(C=0.3, max_iter=5000)),
                ]
            ),
            "balanced",
        ),
        "random_forest_uncalibrated": (rf, "argmax"),
        "random_forest_calibrated": (calibrated(clone(rf)), "balanced"),
    }


def balanced_decision(probabilities: np.ndarray, priors: np.ndarray) -> np.ndarray:
    """Pick the class whose probability most exceeds its training base rate.

    For calibrated probabilities this is the decision that maximises expected
    balanced accuracy, so minority outcomes are not drowned out by the
    73% "Operating" majority.
    """
    return np.argmax(probabilities / priors, axis=1)


def score(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    classes: list[str],
    priors: np.ndarray,
    decision: str = "balanced",
) -> dict[str, float]:
    argmax = np.asarray(classes)[probabilities.argmax(axis=1)]
    predicted = np.asarray(classes)[balanced_decision(probabilities, priors)] if decision == "balanced" else argmax
    onehot = (y_true[:, None] == np.asarray(classes)[None, :]).astype(float)
    return {
        "accuracy": float(accuracy_score(y_true, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predicted)),
        "f1_macro": float(f1_score(y_true, predicted, average="macro", zero_division=0)),
        "precision_macro": float(precision_score(y_true, predicted, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, predicted, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, predicted, average="weighted", zero_division=0)),
        "argmax_accuracy": float(accuracy_score(y_true, argmax)),
        "argmax_balanced_accuracy": float(balanced_accuracy_score(y_true, argmax)),
        "roc_auc_ovr_macro": float(roc_auc_score(y_true, probabilities, multi_class="ovr", average="macro", labels=classes)),
        "log_loss": float(log_loss(y_true, np.clip(probabilities, 1e-6, 1), labels=classes)),
        "brier_multiclass": float(np.mean(np.sum((probabilities - onehot) ** 2, axis=1))),
    }


def cross_validated_comparison(models: dict[str, Any], x: pd.DataFrame, y: pd.Series, priors: np.ndarray) -> dict[str, Any]:
    splitter = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=RANDOM_STATE)
    results: dict[str, list[dict[str, float]]] = {name: [] for name in models}
    for fold, (train_idx, test_idx) in enumerate(splitter.split(x, y)):
        for name, (model, decision) in models.items():
            fitted = clone(model).fit(x.iloc[train_idx], y.iloc[train_idx])
            probabilities = fitted.predict_proba(x.iloc[test_idx])
            results[name].append(
                score(y.iloc[test_idx].to_numpy(), probabilities, list(fitted.classes_), priors, decision)
            )
        LOGGER.info("CV fold %d/15 done", fold + 1)
    summary = {}
    for name, folds in results.items():
        frame = pd.DataFrame(folds)
        summary[name] = {
            metric: {"mean": round(float(frame[metric].mean()), 4), "std": round(float(frame[metric].std()), 4)}
            for metric in frame.columns
        } | {"decision_rule": models[name][1]}
    return {"scheme": "RepeatedStratifiedKFold(n_splits=5, n_repeats=3) on the training split", "models": summary}


def holdout_evaluation(model, x_test: pd.DataFrame, y_test: pd.Series, priors: np.ndarray) -> dict[str, Any]:
    classes = list(model.classes_)
    probabilities = model.predict_proba(x_test)
    predicted = np.asarray(classes)[balanced_decision(probabilities, priors)]
    y = y_test.to_numpy()
    roc = {}
    for index, label in enumerate(classes):
        fpr, tpr, _ = roc_curve(y == label, probabilities[:, index])
        roc[label] = {
            "auc": float(roc_auc_score(y == label, probabilities[:, index])),
            "points": [{"fpr": round(float(a), 4), "tpr": round(float(b), 4)} for a, b in zip(fpr, tpr)],
        }
    reliability = {}
    for index, label in enumerate(classes):
        bins = np.linspace(0, 1, 6)
        which = np.clip(np.digitize(probabilities[:, index], bins) - 1, 0, 4)
        reliability[label] = [
            {
                "bin": f"{bins[b]:.1f}-{bins[b + 1]:.1f}",
                "mean_predicted": round(float(probabilities[which == b, index].mean()), 4),
                "observed_rate": round(float((y[which == b] == label).mean()), 4),
                "count": int((which == b).sum()),
            }
            for b in range(5)
            if (which == b).any()
        ]
    return {
        "test_rows": int(len(y)),
        "metrics": score(y, probabilities, classes, priors),
        "confusion_matrix": {
            "labels": classes,
            "matrix": confusion_matrix(y, predicted, labels=classes).tolist(),
        },
        "classification_report": classification_report(y, predicted, labels=classes, output_dict=True, zero_division=0),
        "per_class_brier": {
            label: float(brier_score_loss(y == label, probabilities[:, index])) for index, label in enumerate(classes)
        },
        "roc_curves": roc,
        "reliability": reliability,
    }


def grouped_permutation_importance(model, x_test: pd.DataFrame, y_test: pd.Series) -> pd.DataFrame:
    """Permute each raw input column (not each engineered column) on the hold-out set."""
    result = permutation_importance(
        model,
        x_test,
        y_test,
        scoring="neg_log_loss",
        n_repeats=30,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    frame = pd.DataFrame(
        {
            "feature": x_test.columns,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
        }
    )
    return frame.sort_values("importance_mean", ascending=False, ignore_index=True)


def year_sensitivity(rf_params: dict[str, Any], x: pd.DataFrame, y: pd.Series, priors: np.ndarray) -> dict[str, Any]:
    """Re-run CV with batch year neutralised to show how much the model relies on it."""
    neutral = x.assign(year=int(x["year"].median()))
    models = {"with_year": (calibrated(random_forest().set_params(**rf_params)), "balanced")}
    with_year = cross_validated_comparison(models, x, y, priors)["models"]["with_year"]
    without_year = cross_validated_comparison({"without_year": models["with_year"]}, neutral, y, priors)["models"]["without_year"]
    return {
        "description": "Same calibrated Random Forest, batch year replaced by a constant.",
        "with_year": with_year,
        "without_year": without_year,
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def train(output_dir: Path = MODEL_DIR, run_sensitivity: bool = True) -> dict[str, Any]:
    inputs, target, records = load_training_frame()
    quality = data_quality_report(DATA_PATH, inputs, target)
    LOGGER.info("Loaded %d rows; class counts %s", len(inputs), quality["class_counts"])

    indices = np.arange(len(inputs))
    train_idx, test_idx = train_test_split(
        indices, test_size=TEST_SIZE, stratify=target, random_state=RANDOM_STATE
    )
    x_train, x_test = inputs.iloc[train_idx], inputs.iloc[test_idx]
    y_train, y_test = target.iloc[train_idx], target.iloc[test_idx]
    priors = np.array([float((y_train == label).mean()) for label in CLASSES])

    search = GridSearchCV(
        random_forest(),
        param_grid={
            "model__max_depth": [4, 6, 10, None],
            "model__min_samples_leaf": [1, 3, 5],
        },
        scoring="roc_auc_ovr",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
        n_jobs=1,
    )
    search.fit(x_train, y_train)
    rf_params = search.best_params_
    LOGGER.info("Best Random Forest parameters %s (CV ROC-AUC %.3f)", rf_params, search.best_score_)

    models = candidates(rf_params)
    comparison = cross_validated_comparison(models, x_train, y_train, priors)

    holdout = {}
    fitted_models = {}
    for name, (model, decision) in models.items():
        fitted_models[name] = clone(model).fit(x_train, y_train)
        holdout[name] = score(y_test.to_numpy(), fitted_models[name].predict_proba(x_test), CLASSES, priors, decision) | {
            "decision_rule": decision
        }

    final = fitted_models["random_forest_calibrated"]
    assert list(final.classes_) == CLASSES
    evaluation = holdout_evaluation(final, x_test, y_test, priors)
    importance = grouped_permutation_importance(final, x_test, y_test)

    # Out-of-fold probabilities for every reference record: an honest estimate
    # for companies the deployed model was trained on.
    oof = cross_val_predict(
        calibrated(random_forest().set_params(**rf_params)),
        inputs,
        target,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
        method="predict_proba",
    )
    splits = np.where(np.isin(indices, test_idx), "test", "train")
    reference = pd.DataFrame(
        {
            "id": [record["id"] for record in records],
            "split": splits,
            **{f"oof_{label.lower()}": oof[:, i].round(4) for i, label in enumerate(CLASSES)},
        }
    )

    sensitivity = year_sensitivity(rf_params, x_train, y_train, priors) if run_sensitivity else None

    rf_inner = fitted_models["random_forest_uncalibrated"]
    impurity = pd.DataFrame(
        {
            "feature": rf_inner.named_steps["features"].get_feature_names_out(),
            "importance": rf_inner.named_steps["model"].feature_importances_,
        }
    ).sort_values("importance", ascending=False, ignore_index=True)

    trained_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metadata = {
        "model_name": "Calibrated Random Forest (startup outcome classifier)",
        "algorithm": "RandomForestClassifier(class_weight='balanced_subsample') + CalibratedClassifierCV(sigmoid, 5-fold)",
        "target": "Fate - recorded company status at data collection: Operating, Exited (acquired/IPO), Dead",
        "classes": CLASSES,
        "class_priors": dict(zip(CLASSES, [round(float(p), 4) for p in priors])),
        "decision_rule": "balanced: argmax_k P(k|x) / prior(k)",
        "input_columns": MODEL_COLUMNS,
        "engineered_features": list(rf_inner.named_steps["features"].get_feature_names_out()),
        "excluded_columns": EXCLUDED_COLUMNS,
        "hyperparameters": {key.replace("model__", ""): value for key, value in rf_params.items()}
        | {"n_estimators": 300, "class_weight": "balanced_subsample", "random_state": RANDOM_STATE},
        "grid_search_best_cv_roc_auc": round(float(search.best_score_), 4),
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "random_state": RANDOM_STATE,
        "dataset": {"path": "data/CleanStartups.csv", "sha256": file_sha256(DATA_PATH)},
        "trained_at": trained_at,
        "versions": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    metrics = {
        "data_quality": quality,
        "cross_validation": comparison,
        "holdout_comparison": holdout,
        "holdout": evaluation,
        "year_sensitivity": sensitivity,
        "trained_at": trained_at,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, output_dir / "pipeline.joblib", compress=3)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    importance.to_csv(output_dir / "feature_importance.csv", index=False)
    impurity.to_csv(output_dir / "impurity_importance.csv", index=False)
    reference.to_csv(output_dir / "reference_evaluation.csv", index=False)
    LOGGER.info("Hold-out metrics: %s", json.dumps(evaluation["metrics"], indent=2))
    return {"metadata": metadata, "metrics": metrics}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    train()
