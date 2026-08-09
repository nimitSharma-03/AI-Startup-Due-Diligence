"""Train and evaluate the startup due-diligence Random Forest model."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from preprocess import PreprocessingError, preprocess_data


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_DIRECTORY = PROJECT_ROOT / "model"
TARGET_COLUMN = "Fate"
RANDOM_STATE = 42
TEST_SIZE = 0.20
MODEL_PATH = MODEL_DIRECTORY / "risk_model.pkl"
FEATURES_PATH = MODEL_DIRECTORY / "features.pkl"
METRICS_PATH = MODEL_DIRECTORY / "metrics.json"
FEATURE_IMPORTANCE_PATH = MODEL_DIRECTORY / "feature_importance.csv"


class TrainingError(ValueError):
    """Raised when the model training pipeline cannot be completed."""


def validate_training_data(dataframe: pd.DataFrame, target_column: str) -> None:
    """Validate that a processed dataset is suitable for supervised training.

    Args:
        dataframe: Processed startup dataset.
        target_column: Column containing the startup outcome label.

    Raises:
        TrainingError: If the dataset or target cannot be used for training.
    """
    if dataframe.empty:
        raise TrainingError("The processed dataset is empty.")
    if target_column not in dataframe.columns:
        raise TrainingError(
            f"Target column '{target_column}' was not found in the processed dataset."
        )

    feature_columns = dataframe.drop(columns=[target_column]).columns
    if feature_columns.empty:
        raise TrainingError("At least one feature column is required for training.")
    if dataframe[target_column].isna().any():
        raise TrainingError("The target column contains missing values.")

    class_counts = dataframe[target_column].value_counts()
    if len(class_counts) < 2:
        raise TrainingError("The target column must contain at least two classes.")
    if class_counts.min() < 2:
        raise TrainingError(
            "Each target class must contain at least two records for a stratified split."
        )


def split_dataset(
    dataframe: pd.DataFrame,
    target_column: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split a processed dataset into stratified training and test sets."""
    features = dataframe.drop(columns=[target_column])
    target = dataframe[target_column]

    try:
        return train_test_split(
            features,
            target,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=target,
        )
    except ValueError as error:
        raise TrainingError(f"Could not split the dataset for training: {error}") from error


def build_model() -> RandomForestClassifier:
    """Create the project's primary Random Forest classifier."""
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=15,
        random_state=RANDOM_STATE,
    )


def evaluate_model(
    model: RandomForestClassifier,
    features: pd.DataFrame,
    target: pd.Series,
) -> dict[str, Any]:
    """Calculate classification metrics for a fitted model.

    Weighted precision, recall, and F1 scores ensure every startup outcome is
    represented. ROC-AUC uses one-vs-rest scoring for the multiclass target.
    """
    predictions = model.predict(features)
    probabilities = model.predict_proba(features)
    class_labels = model.classes_

    try:
        if len(class_labels) == 2:
            roc_auc = roc_auc_score(target, probabilities[:, 1])
        else:
            roc_auc = roc_auc_score(
                target,
                probabilities,
                multi_class="ovr",
                average="weighted",
                labels=class_labels,
            )
    except ValueError as error:
        raise TrainingError(f"Could not calculate ROC-AUC: {error}") from error

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(target, predictions)),
        "precision_weighted": float(
            precision_score(target, predictions, average="weighted", zero_division=0)
        ),
        "recall_weighted": float(
            recall_score(target, predictions, average="weighted", zero_division=0)
        ),
        "f1_weighted": float(
            f1_score(target, predictions, average="weighted", zero_division=0)
        ),
        "roc_auc_ovr_weighted": float(roc_auc),
        "confusion_matrix": confusion_matrix(target, predictions, labels=class_labels).tolist(),
        "class_labels": [str(label) for label in class_labels],
        "classification_report": classification_report(
            target,
            predictions,
            labels=class_labels,
            output_dict=True,
            zero_division=0,
        ),
    }
    return metrics


def create_feature_importance(
    model: RandomForestClassifier,
    feature_names: list[str],
) -> pd.DataFrame:
    """Create a descending feature-importance dataframe for a fitted model."""
    importance = pd.DataFrame(
        {"feature": feature_names, "importance": model.feature_importances_}
    )
    return importance.sort_values("importance", ascending=False, ignore_index=True)


def save_training_artifacts(
    model: RandomForestClassifier,
    feature_names: list[str],
    metrics: dict[str, Any],
    feature_importance: pd.DataFrame,
) -> None:
    """Save the model, feature list, evaluation metrics, and importances."""
    try:
        MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        joblib.dump(feature_names, FEATURES_PATH)
        METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        feature_importance.to_csv(FEATURE_IMPORTANCE_PATH, index=False)
    except (OSError, TypeError) as error:
        raise TrainingError(f"Could not save training artifacts: {error}") from error

    LOGGER.info("Saved model to %s", MODEL_PATH)
    LOGGER.info("Saved feature list to %s", FEATURES_PATH)
    LOGGER.info("Saved metrics to %s", METRICS_PATH)
    LOGGER.info("Saved feature importance to %s", FEATURE_IMPORTANCE_PATH)


def log_evaluation_metrics(metrics: dict[str, Any]) -> None:
    """Log a concise, readable summary of model evaluation results."""
    LOGGER.info("Accuracy: %.4f", metrics["accuracy"])
    LOGGER.info("Weighted precision: %.4f", metrics["precision_weighted"])
    LOGGER.info("Weighted recall: %.4f", metrics["recall_weighted"])
    LOGGER.info("Weighted F1 score: %.4f", metrics["f1_weighted"])
    LOGGER.info("Weighted one-vs-rest ROC-AUC: %.4f", metrics["roc_auc_ovr_weighted"])
    LOGGER.info("Confusion matrix: %s", metrics["confusion_matrix"])
    LOGGER.info("Classification report: %s", metrics["classification_report"])


def train_model() -> tuple[RandomForestClassifier, dict[str, Any]]:
    """Preprocess data, train the Random Forest model, and save all artifacts.

    Returns:
        The fitted model and its evaluation metrics.

    Raises:
        TrainingError: If data validation, training, evaluation, or saving fails.
    """
    try:
        dataframe, _ = preprocess_data(required_columns=[TARGET_COLUMN])
    except PreprocessingError as error:
        raise TrainingError(f"Dataset preprocessing failed: {error}") from error

    validate_training_data(dataframe, TARGET_COLUMN)
    x_train, x_test, y_train, y_test = split_dataset(dataframe, TARGET_COLUMN)
    feature_names = x_train.columns.tolist()

    model = build_model()
    try:
        model.fit(x_train, y_train)
    except ValueError as error:
        raise TrainingError(f"Random Forest training failed: {error}") from error

    metrics = evaluate_model(model, x_test, y_test)
    feature_importance = create_feature_importance(model, feature_names)
    save_training_artifacts(model, feature_names, metrics, feature_importance)
    log_evaluation_metrics(metrics)
    return model, metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        train_model()
    except TrainingError as error:
        LOGGER.error("Training failed: %s", error)
        raise SystemExit(1) from error
