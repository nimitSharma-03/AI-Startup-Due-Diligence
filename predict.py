"""Prediction utilities for the startup due-diligence model."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_DIRECTORY = PROJECT_ROOT / "model"
MODEL_PATH = MODEL_DIRECTORY / "risk_model.pkl"
FEATURES_PATH = MODEL_DIRECTORY / "features.pkl"
ENCODERS_PATH = MODEL_DIRECTORY / "label_encoders.pkl"


class PredictionError(ValueError):
    """Raised when prediction data or model artifacts are invalid."""


def _validate_artifact_path(path: Path, artifact_name: str) -> None:
    """Ensure a required model artifact exists and is a file."""
    if not path.exists():
        raise PredictionError(
            f"Required {artifact_name} file was not found: {path}. "
            "Run train_model.py before making predictions."
        )
    if not path.is_file():
        raise PredictionError(f"The {artifact_name} path must point to a file: {path}")


def load_prediction_artifacts() -> tuple[Any, list[str], dict[str, LabelEncoder]]:
    """Load and validate the trained model, feature list, and label encoders."""
    _validate_artifact_path(MODEL_PATH, "model")
    _validate_artifact_path(FEATURES_PATH, "features")
    _validate_artifact_path(ENCODERS_PATH, "label encoders")

    try:
        loaded_model = joblib.load(MODEL_PATH)
        LOGGER.info("Model loaded from %s", MODEL_PATH)

        loaded_features = joblib.load(FEATURES_PATH)
        LOGGER.info("Features loaded from %s", FEATURES_PATH)

        loaded_encoders = joblib.load(ENCODERS_PATH)
        LOGGER.info("Encoders loaded from %s", ENCODERS_PATH)
    except (OSError, TypeError, ValueError) as error:
        raise PredictionError(
            f"Could not load prediction artifacts: {error}"
        ) from error

    if not isinstance(loaded_features, list) or not all(
        isinstance(feature, str) for feature in loaded_features
    ):
        raise PredictionError(
            "The saved features artifact is not a valid list of columns."
        )
    if not isinstance(loaded_encoders, dict):
        raise PredictionError(
            "The saved encoders artifact is not a valid dictionary."
        )
    supports_predictions = hasattr(loaded_model, "predict")
    supports_probabilities = hasattr(loaded_model, "predict_proba")
    if not supports_predictions or not supports_probabilities:
        raise PredictionError(
            "The saved model does not support class probability prediction."
        )

    return loaded_model, loaded_features, loaded_encoders


def validate_uploaded_dataframe(
    dataframe: pd.DataFrame,
    required_features: list[str],
) -> pd.DataFrame:
    """Validate uploaded data and keep only columns required by the model.

    Extra columns are ignored. The original dataframe is never modified, allowing
    callers to return uploaded data alongside prediction results.
    """
    if dataframe.empty:
        raise PredictionError("The uploaded CSV contains no data rows.")

    extra_columns = sorted(set(dataframe.columns) - set(required_features))
    if extra_columns:
        LOGGER.info("Ignoring %d extra columns in uploaded data.", len(extra_columns))

    LOGGER.info("CSV validated with %d rows.", len(dataframe))
    # Spreadsheet uploads are adapted by dataset_preprocessing before reaching
    # this function. Retain the predictable feature order for the classifier.
    return dataframe.reindex(columns=required_features).copy()


def preprocess_input(
    dataframe: pd.DataFrame,
    encoders: dict[str, LabelEncoder],
) -> pd.DataFrame:
    """Encode categorical columns using the saved training-time encoders.

    Values not seen during training use the existing fallback encoding of zero and
    produce a warning instead of stopping the prediction request.
    """
    processed_dataframe = dataframe.copy()

    for column, encoder in encoders.items():
        if column not in processed_dataframe.columns:
            continue

        known_categories = set(encoder.classes_)
        encoded_values: list[int] = []
        for value in processed_dataframe[column].astype(str):
            if value in known_categories:
                encoded_values.append(int(encoder.transform([value])[0]))
            else:
                LOGGER.warning(
                    "Unseen category '%s' found in column '%s'; "
                    "using fallback encoding.",
                    value,
                    column,
                )
                encoded_values.append(0)

        processed_dataframe[column] = encoded_values

    return processed_dataframe


def predict_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Predict startup outcomes for every row in a supplied dataframe.

    Returns the original input columns with ``Prediction`` and ``Probability``
    appended. ``Confidence`` remains available as a percentage for backward
    compatibility with the existing Streamlit application.
    """
    model, features, label_encoders = load_prediction_artifacts()
    model_input = validate_uploaded_dataframe(dataframe, features)
    model_input = preprocess_input(model_input, label_encoders)

    LOGGER.info("Prediction started for %d rows.", len(model_input))
    try:
        predicted_classes = model.predict(model_input)
        predicted_probabilities = model.predict_proba(model_input).max(axis=1)
    except ValueError as error:
        raise PredictionError(
            f"Prediction failed because of invalid input values: {error}"
        ) from error

    fate_encoder = label_encoders.get("Fate")
    if fate_encoder is None:
        raise PredictionError(
            "The saved encoders do not contain the required 'Fate' encoder."
        )

    try:
        predictions = fate_encoder.inverse_transform(predicted_classes)
    except ValueError as error:
        raise PredictionError(f"Could not decode predicted classes: {error}") from error

    result = dataframe.copy()
    result["Prediction"] = predictions
    result["Probability"] = predicted_probabilities.round(4)
    result["Confidence"] = (predicted_probabilities * 100).round(2)

    LOGGER.info("Prediction completed. Number of rows predicted: %d", len(result))
    return result
