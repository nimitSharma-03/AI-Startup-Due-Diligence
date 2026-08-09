"""Spreadsheet ingestion and model-input adaptation."""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from column_mapping import find_column, normalize_column
from predict import PredictionError


def validate_report_dataframe(frame: pd.DataFrame) -> str:
    """Validate report-specific requirements and return the company column name."""
    if frame.empty:
        raise PredictionError("The uploaded spreadsheet contains no data rows.")
    company_column = find_column(frame.columns, "company")
    if company_column is None:
        raise PredictionError(
            "The spreadsheet is missing a Company Name column. "
            "Add a column such as 'Company Name', 'Company', or 'Startup Name'."
        )
    if frame[company_column].dropna().astype(str).str.strip().eq("").all():
        raise PredictionError("The Company Name column contains no usable company names.")
    return company_column


def get_company_list(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Return display-ready company choices, preserving duplicate row identities."""
    company_column = validate_report_dataframe(frame)
    choices: list[dict[str, object]] = []
    for row_index, company_name in frame[company_column].items():
        if pd.isna(company_name) or not str(company_name).strip():
            continue
        choices.append({"row_index": int(row_index), "name": str(company_name).strip(), "label": f"{str(company_name).strip()} (Row {int(row_index) + 1})"})
    if not choices:
        raise PredictionError("No selectable company names were found in the spreadsheet.")
    return choices


def filter_company_data(frame: pd.DataFrame, row_index: int) -> pd.DataFrame:
    """Return exactly one selected company record without changing the source frame."""
    company_column = validate_report_dataframe(frame)
    if row_index not in frame.index:
        raise PredictionError("The selected company was not found in the uploaded spreadsheet.")
    selected = frame.loc[[row_index]].copy()
    if selected.empty:
        raise PredictionError("The selected company was not found in the uploaded spreadsheet.")
    company_name = selected.iloc[0][company_column]
    if pd.isna(company_name) or not str(company_name).strip():
        raise PredictionError("The selected row does not contain a valid company name.")
    return selected


def read_startup_file(upload: BinaryIO, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            frame = pd.read_csv(upload)
        elif suffix in {".xlsx", ".xls"}:
            frame = pd.read_excel(upload)
        else:
            raise PredictionError("Upload a CSV, XLSX, or XLS spreadsheet.")
    except Exception as error:
        if isinstance(error, PredictionError):
            raise
        raise PredictionError("The uploaded spreadsheet could not be read.") from error
    frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if frame.empty:
        raise PredictionError("The uploaded spreadsheet contains no data rows.")
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame


def adapt_for_model(frame: pd.DataFrame, features: list[str], encoders: dict) -> pd.DataFrame:
    """Map similar headers and fill unavailable fields without rejecting a report."""
    output = pd.DataFrame(index=frame.index)
    source_normalized = {normalize_column(column): column for column in frame.columns}
    for feature in features:
        source = source_normalized.get(normalize_column(feature))
        if source is None:
            source = find_column(frame.columns, _feature_concept(feature))
        if source is not None:
            output[feature] = frame[source]
        elif feature in encoders:
            output[feature] = "Not Available"
        else:
            output[feature] = 0
        if feature in encoders:
            output[feature] = output[feature].fillna("Not Available").astype(str)
        else:
            output[feature] = pd.to_numeric(output[feature], errors="coerce").fillna(0)
    return output


def _feature_concept(feature: str) -> str:
    values = {"TotalFunds": "funding", "Company": "company", "City": "city", "Description": "description", "YCYear": "year"}
    return values.get(feature, feature)
