"""Load the trained pipeline and produce predictions with explanations."""

from __future__ import annotations

import json
import logging
from functools import cached_property
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn

from diligence.ml.schema import MODEL_COLUMNS

LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "model"

FIELD_LABELS = {
    "year": "Batch year",
    "session": "Batch session",
    "total_funding": "Total funding",
    "city": "City",
    "markets": "Markets",
}
SIGNAL_LEVELS = (
    (1.0, "Lower", "Estimated failure-class probability is below the historical base rate."),
    (2.0, "Moderate", "Estimated failure-class probability is between 1x and 2x the historical base rate."),
    (float("inf"), "Elevated", "Estimated failure-class probability is at least 2x the historical base rate."),
)


class ModelUnavailable(RuntimeError):
    """Raised when model artifacts are missing or cannot be loaded."""


def describe_value(field: str, value: Any) -> str:
    if value is None or (isinstance(value, list) and not value):
        return "Not provided"
    if field == "total_funding":
        return format_usd(value)
    if field == "markets":
        return ", ".join(value)
    return str(value)


def format_usd(value: float | None) -> str:
    if value is None:
        return "Not provided"
    value = float(value)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= threshold:
            return f"${value / threshold:,.1f}{suffix}"
    return f"${value:,.0f}"


class ModelService:
    """Wraps the persisted pipeline; all methods accept canonical inputs."""

    def __init__(self, model_dir: Path = DEFAULT_MODEL_DIR):
        self.model_dir = model_dir
        try:
            # The pipeline is a first-party artifact produced by
            # diligence.ml.train and shipped in the repository. User uploads
            # are only ever parsed as CSV text and are never unpickled.
            self.pipeline = joblib.load(model_dir / "pipeline.joblib")
            self.metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
            self.metrics = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
            self.permutation_importance = pd.read_csv(model_dir / "feature_importance.csv")
            self.impurity_importance = pd.read_csv(model_dir / "impurity_importance.csv")
            self.reference_evaluation = pd.read_csv(model_dir / "reference_evaluation.csv", dtype={"id": str})
        except (OSError, ValueError) as error:
            raise ModelUnavailable(f"Model artifacts could not be loaded from {model_dir}") from error

        self.classes: list[str] = list(self.pipeline.classes_)
        if self.classes != self.metadata["classes"]:
            raise ModelUnavailable("Model classes do not match metadata.")
        self.priors = np.array([self.metadata["class_priors"][label] for label in self.classes])
        trained_version = self.metadata["versions"]["scikit_learn"]
        if trained_version != sklearn.__version__:
            LOGGER.warning(
                "Model trained with scikit-learn %s but running %s; retrain with python -m diligence.ml.train",
                trained_version,
                sklearn.__version__,
            )
        self._background: pd.DataFrame | None = None

    # ------------------------------------------------------------------ predictions
    @staticmethod
    def to_frame(inputs: list[dict[str, Any]]) -> pd.DataFrame:
        frame = pd.DataFrame(inputs, columns=MODEL_COLUMNS)
        frame["markets"] = frame["markets"].map(lambda value: value if isinstance(value, list) else [])
        return frame

    def probabilities(self, inputs: list[dict[str, Any]]) -> np.ndarray:
        if not inputs:
            return np.zeros((0, len(self.classes)))
        return self.pipeline.predict_proba(self.to_frame(inputs))

    def predict(self, inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        probabilities = self.probabilities(inputs)
        return [self._format(row) for row in probabilities]

    def _format(self, row: np.ndarray) -> dict[str, Any]:
        lift = row / self.priors
        predicted_index = int(np.argmax(lift))
        dead_lift = float(lift[self.classes.index("Dead")])
        level, description = next((name, text) for limit, name, text in SIGNAL_LEVELS if dead_lift < limit)
        return {
            "predicted_outcome": self.classes[predicted_index],
            "predicted_probability": round(float(row[predicted_index]), 4),
            "most_likely_outcome": self.classes[int(np.argmax(row))],
            "probabilities": {label: round(float(p), 4) for label, p in zip(self.classes, row)},
            "lift_vs_base_rate": {label: round(float(value), 3) for label, value in zip(self.classes, lift)},
            "failure_signal": {"level": level, "ratio_to_base_rate": round(dead_lift, 3), "description": description},
        }

    # ------------------------------------------------------------------ explanations
    def set_background(self, inputs: list[dict[str, Any]], size: int = 100, seed: int = 42) -> None:
        """Use a fixed random sample of training records as the comparison set."""
        frame = self.to_frame(inputs)
        if len(frame) > size:
            frame = frame.sample(n=size, random_state=seed)
        self._background = frame.reset_index(drop=True)

    def explain(self, model_input: dict[str, Any]) -> list[dict[str, Any]]:
        """Interventional single-feature attribution.

        For each input field, the field is replaced by its value in each
        background record (all other fields kept) and the probabilities are
        averaged. The contribution is the probability for the record minus
        that average, i.e. how much this field's actual value moves the
        estimate relative to typical values. It describes model behaviour,
        not causation, and contributions need not add up exactly.
        """
        if self._background is None:
            raise ModelUnavailable("Explanation background has not been initialised.")
        base = self.probabilities([model_input])[0]
        record = self.to_frame([model_input])
        background = self._background
        contributions = []
        for field in MODEL_COLUMNS:
            perturbed = pd.concat([record] * len(background), ignore_index=True)
            perturbed[field] = background[field].to_numpy()
            average = self.pipeline.predict_proba(perturbed).mean(axis=0)
            delta = base - average
            contributions.append(
                {
                    "field": field,
                    "label": FIELD_LABELS[field],
                    "value": describe_value(field, model_input.get(field)),
                    "contributions": {label: round(float(d), 4) for label, d in zip(self.classes, delta)},
                }
            )
        contributions.sort(key=lambda item: -max(abs(v) for v in item["contributions"].values()))
        return contributions

    # ------------------------------------------------------------------ metadata
    @cached_property
    def summary(self) -> dict[str, Any]:
        holdout = self.metrics["holdout"]["metrics"]
        cv = self.metrics["cross_validation"]["models"]["random_forest_calibrated"]
        return {
            "model_name": self.metadata["model_name"],
            "algorithm": self.metadata["algorithm"],
            "classes": self.classes,
            "class_priors": self.metadata["class_priors"],
            "train_rows": self.metadata["train_rows"],
            "test_rows": self.metadata["test_rows"],
            "trained_at": self.metadata["trained_at"],
            "holdout": {key: round(value, 4) for key, value in holdout.items()},
            "cross_validation": {key: value for key, value in cv.items() if isinstance(value, dict)},
        }

    def importance(self) -> dict[str, Any]:
        permutation = [
            {
                "feature": row.feature,
                "label": FIELD_LABELS.get(row.feature, row.feature),
                "importance": round(float(row.importance_mean), 5),
                "std": round(float(row.importance_std), 5),
            }
            for row in self.permutation_importance.itertuples()
        ]
        impurity = [
            {"feature": row.feature, "importance": round(float(row.importance), 5)}
            for row in self.impurity_importance.head(20).itertuples()
        ]
        return {
            "permutation": permutation,
            "permutation_method": "Increase in hold-out log-loss when the raw input column is shuffled (30 repeats).",
            "impurity": impurity,
            "impurity_method": "Mean decrease in impurity of the uncalibrated forest, per engineered feature (biased toward high-cardinality numeric features).",
        }
