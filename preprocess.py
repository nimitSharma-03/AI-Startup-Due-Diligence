"""Dataset preprocessing utilities for the startup due-diligence model."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import joblib
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.preprocessing import LabelEncoder


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "CleanStartups.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed_startups.csv"
DEFAULT_ENCODERS_PATH = PROJECT_ROOT / "model" / "label_encoders.pkl"


class PreprocessingError(ValueError):
    """Raised when a dataset cannot be safely preprocessed."""


def _validate_csv_path(file_path: str | Path) -> Path:
    """Validate and return an existing CSV file path.

    Args:
        file_path: Path to the source dataset.

    Raises:
        PreprocessingError: If the path is missing, is not a file, or is not CSV.
    """
    path = Path(file_path).expanduser().resolve()

    if path.suffix.lower() != ".csv":
        raise PreprocessingError(f"Only CSV files are supported: {path}")
    if not path.exists():
        raise PreprocessingError(f"Dataset file was not found: {path}")
    if not path.is_file():
        raise PreprocessingError(f"Dataset path must point to a file: {path}")

    return path


def load_data(
    file_path: str | Path = DEFAULT_INPUT_PATH,
    required_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Load a CSV dataset and validate its structure.

    Args:
        file_path: Location of the CSV dataset.
        required_columns: Optional column names that must be present.

    Returns:
        The loaded dataset.

    Raises:
        PreprocessingError: If the CSV is invalid, empty, or lacks required columns.
    """
    path = _validate_csv_path(file_path)

    try:
        dataframe = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise PreprocessingError(f"Could not read a valid CSV dataset: {path}") from error
    except OSError as error:
        raise PreprocessingError(f"Could not access dataset file: {path}") from error

    unnamed_columns = [
        column for column in dataframe.columns if str(column).startswith("Unnamed:")
    ]
    if unnamed_columns:
        dataframe = dataframe.drop(columns=unnamed_columns)
    LOGGER.info("Removed %d unnamed index columns.", len(unnamed_columns))

    if dataframe.empty:
        raise PreprocessingError("The dataset contains no data rows.")
    if dataframe.columns.empty:
        raise PreprocessingError("The dataset does not contain any columns.")

    missing_columns = set(required_columns or ()) - set(dataframe.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise PreprocessingError(f"Dataset is missing required columns: {missing_list}")

    LOGGER.info("Loaded dataset from %s with shape %s", path, dataframe.shape)
    return dataframe


def remove_duplicates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate records and entirely empty rows.

    Args:
        dataframe: Dataset to clean.

    Returns:
        A dataframe without duplicate or completely empty records.
    """
    original_rows = len(dataframe)
    cleaned_dataframe = dataframe.drop_duplicates().dropna(how="all").copy()
    LOGGER.info("Removed %d duplicate or empty rows.", original_rows - len(cleaned_dataframe))

    if cleaned_dataframe.empty:
        raise PreprocessingError("No usable rows remain after removing duplicates and empty rows.")

    return cleaned_dataframe


def handle_missing_values(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Fill missing categorical values with a mode and numeric values with a median.

    Numeric columns containing only missing values are filled with zero. Categorical
    columns without a mode are filled with ``"Unknown"``.
    """
    cleaned_dataframe = dataframe.copy()

    for column in cleaned_dataframe.columns:
        if not cleaned_dataframe[column].isna().any():
            continue

        if is_numeric_dtype(cleaned_dataframe[column]):
            median = cleaned_dataframe[column].median()
            fill_value = 0 if pd.isna(median) else median
        else:
            mode = cleaned_dataframe[column].mode(dropna=True)
            fill_value = mode.iloc[0] if not mode.empty else "Unknown"

        cleaned_dataframe[column] = cleaned_dataframe[column].fillna(fill_value)

    LOGGER.info("Handled missing values for %d columns.", len(cleaned_dataframe.columns))
    return cleaned_dataframe


def encode_categorical_columns(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    """Encode object and categorical columns using one encoder per column."""
    encoded_dataframe = dataframe.copy()
    label_encoders: dict[str, LabelEncoder] = {}

    categorical_columns = encoded_dataframe.select_dtypes(
        include=["object", "category"]
    ).columns
    for column in categorical_columns:
        encoder = LabelEncoder()
        encoded_dataframe[column] = encoder.fit_transform(
            encoded_dataframe[column].astype(str)
        )
        label_encoders[column] = encoder

    LOGGER.info("Encoded %d categorical columns.", len(label_encoders))
    return encoded_dataframe, label_encoders


def save_processed_dataset(
    dataframe: pd.DataFrame,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Save a processed dataframe to CSV and return its resolved path."""
    path = Path(output_path).expanduser().resolve()
    if path.suffix.lower() != ".csv":
        raise PreprocessingError("Processed dataset output must use a .csv extension.")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(path, index=False)
    except OSError as error:
        raise PreprocessingError(f"Could not save processed dataset to: {path}") from error

    LOGGER.info("Saved processed dataset to %s", path)
    return path


def _save_label_encoders(
    label_encoders: dict[str, LabelEncoder],
    encoders_path: str | Path,
) -> Path:
    """Persist fitted label encoders with joblib."""
    path = Path(encoders_path).expanduser().resolve()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(label_encoders, path)
    except OSError as error:
        raise PreprocessingError(f"Could not save label encoders to: {path}") from error

    LOGGER.info("Saved label encoders to %s", path)
    return path


def preprocess_data(
    file_path: str | Path = DEFAULT_INPUT_PATH,
    training: bool = True,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    encoders_path: str | Path = DEFAULT_ENCODERS_PATH,
    required_columns: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    """Load, clean, optionally encode, and save a startup dataset.

    This preserves the original project's return contract: a clean dataframe and a
    dictionary of fitted encoders. When ``training`` is false, categorical values
    remain unchanged and the encoder dictionary is empty.
    """
    dataframe = load_data(file_path, required_columns)
    dataframe = remove_duplicates(dataframe)
    dataframe = handle_missing_values(dataframe)

    label_encoders: dict[str, LabelEncoder] = {}
    if training:
        dataframe, label_encoders = encode_categorical_columns(dataframe)
        _save_label_encoders(label_encoders, encoders_path)

    save_processed_dataset(dataframe, output_path)
    LOGGER.info("Preprocessing completed successfully with shape %s", dataframe.shape)
    return dataframe, label_encoders


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    preprocess_data()
