"""Read startup CSV files and map their columns to canonical records.

The reference dataset and user uploads go through the same code, so a file
with the original Y Combinator columns (``Company``, ``YCYear``,
``TotalFunds``, ``Market1``...) and a file with generic headers
(``Company Name``, ``Founded Year``, ``Funding``, ``Industry``...) both work.
Column matching is exact on normalised header names; there is no fuzzy
substring matching, so a column is never mapped to the wrong concept.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from diligence.ml.schema import (
    ValidationError,
    is_missing,
    parse_record,
)

MAX_ROWS = 5000
MAX_COLUMNS = 200

# Single-valued concepts: first matching column wins.
SINGLE_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("company", "company name", "startup", "startup name", "name", "organization", "organisation"),
    "year": ("ycyear", "yc year", "batch year", "year", "founded", "founded year", "founding year", "year founded"),
    "session": ("ycsession", "yc session", "session", "batch session", "batch"),
    "total_funding": (
        "totalfunds", "total funds", "total funding", "total funding usd", "funding", "funding usd",
        "funding amount", "capital raised", "amount raised", "total raised",
    ),
    "city": ("city", "location", "headquarters", "hq", "hq city"),
    "description": ("description", "summary", "about", "short description"),
    "website": ("website", "url", "homepage", "site"),
    "status": ("fate", "status", "outcome", "current status"),
}
# Multi-valued concepts: every matching column (e.g. Market1..Market5) is used.
MULTI_ALIASES: dict[str, tuple[str, ...]] = {
    "markets": ("market", "markets", "industry", "industries", "sector", "category", "categories", "vertical"),
    "founders": ("founder", "founders"),
    "investors": ("investor", "investors"),
}
CONCEPT_LABELS = {
    "name": "Company name",
    "year": "Batch / founding year",
    "session": "Batch session",
    "total_funding": "Total funding",
    "city": "City",
    "markets": "Markets / industry",
    "description": "Description",
    "website": "Website",
    "status": "Recorded status",
    "founders": "Founders",
    "investors": "Investors",
}
STATUS_SYNONYMS = {
    "operating": "Operating", "active": "Operating", "live": "Operating",
    "exited": "Exited", "acquired": "Exited", "ipo": "Exited", "exit": "Exited",
    "dead": "Dead", "closed": "Dead", "defunct": "Dead", "shut down": "Dead", "failed": "Dead",
}


class DatasetError(ValueError):
    """Raised when a file cannot be used as a startup dataset."""


def normalize_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


@dataclass
class ColumnMapping:
    single: dict[str, str] = field(default_factory=dict)
    multi: dict[str, list[str]] = field(default_factory=dict)
    unused: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        mapping = {concept: [column] for concept, column in self.single.items()}
        mapping.update({concept: columns for concept, columns in self.multi.items()})
        return mapping


def map_columns(columns: list[str]) -> ColumnMapping:
    """Match source headers to canonical concepts."""
    normalized = {column: normalize_header(column) for column in columns}
    mapping = ColumnMapping()
    used: set[str] = set()

    for concept, aliases in SINGLE_ALIASES.items():
        for alias in aliases:
            match = next(
                (column for column, norm in normalized.items() if norm == alias and column not in used),
                None,
            )
            if match is not None:
                mapping.single[concept] = match
                used.add(match)
                break

    for concept, aliases in MULTI_ALIASES.items():
        pattern = re.compile(r"^(" + "|".join(re.escape(alias) for alias in aliases) + r")\s*\d*$")
        matches = [column for column, norm in normalized.items() if column not in used and pattern.match(norm)]
        if matches:
            mapping.multi[concept] = matches
            used.update(matches)

    mapping.unused = [column for column in columns if column not in used]
    return mapping


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    """Parse CSV bytes defensively, keeping every cell as text."""
    if not content or not content.strip():
        raise DatasetError("The file is empty.")
    if b"\x00" in content[:4096]:
        raise DatasetError("The file does not look like a text CSV file.")
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    try:
        frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, na_values=[""])
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise DatasetError("The CSV could not be parsed. Check the delimiter and quoting.") from error
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.loc[:, [column for column in frame.columns if column and not column.startswith("Unnamed:")]]
    frame = frame.dropna(how="all")
    if frame.empty:
        raise DatasetError("The CSV contains no data rows.")
    if len(frame.columns) > MAX_COLUMNS:
        raise DatasetError(f"The CSV has {len(frame.columns)} columns; the limit is {MAX_COLUMNS}.")
    if len(frame) > MAX_ROWS:
        raise DatasetError(f"The CSV has {len(frame)} rows; the limit is {MAX_ROWS}.")
    if len(set(frame.columns)) != len(frame.columns):
        raise DatasetError("The CSV has duplicate column names.")
    return frame.reset_index(drop=True)


def _cell(row: pd.Series, column: str | None) -> Any:
    if column is None:
        return None
    value = row.get(column)
    return None if is_missing(value) else str(value).strip()


def _multi(row: pd.Series, columns: list[str]) -> list[str]:
    values: list[str] = []
    for column in columns:
        raw = row.get(column)
        if is_missing(raw):
            continue
        for part in re.split(r"[;|]", str(raw)) if len(columns) == 1 else [str(raw)]:
            part = part.strip()
            if part and part.lower() not in {value.lower() for value in values}:
                values.append(part)
    return values


def normalize_status(value: Any) -> str | None:
    if is_missing(value):
        return None
    text = str(value).strip()
    return STATUS_SYNONYMS.get(text.lower(), text)


def build_records(frame: pd.DataFrame, mapping: ColumnMapping) -> list[dict[str, Any]]:
    """Convert dataframe rows into display records with parsed model inputs.

    Each record carries ``model_input`` (canonical values or ``None``),
    ``issues`` (validation errors that block scoring), ``warnings`` and
    ``missing_fields`` so the UI can disclose exactly what is unknown.
    """
    records: list[dict[str, Any]] = []
    single = mapping.single
    for position, (_, row) in enumerate(frame.iterrows()):
        markets_columns = mapping.multi.get("markets", [])
        # A single "Industry" column may hold "SaaS, Analytics"; numbered
        # Market1..5 columns hold one tag each.
        if len(markets_columns) == 1:
            raw_markets = _cell(row, markets_columns[0])
            markets = [part.strip() for part in re.split(r"[,;|]", raw_markets)] if raw_markets else []
            markets = [market for market in markets if market]
        else:
            markets = _multi(row, markets_columns)

        raw_input = {
            "year": _cell(row, single.get("year")),
            "session": _cell(row, single.get("session")),
            "total_funding": _cell(row, single.get("total_funding")),
            "city": _cell(row, single.get("city")),
            "markets": markets,
        }
        record: dict[str, Any] = {
            "id": str(position),
            "row_number": position + 1,
            "name": _cell(row, single.get("name")) or f"Unnamed startup (row {position + 1})",
            "description": _cell(row, single.get("description")),
            "website": _cell(row, single.get("website")),
            "status": normalize_status(_cell(row, single.get("status"))),
            "founders": _multi(row, mapping.multi.get("founders", [])),
            "investors": _multi(row, mapping.multi.get("investors", [])),
            "markets": markets,
            "model_input": None,
            "issues": {},
            "warnings": [],
            "missing_fields": [],
        }
        try:
            parsed = parse_record(raw_input)
            record["model_input"] = parsed.values
            record["warnings"] = parsed.warnings
            record["missing_fields"] = parsed.missing
            record.update(
                year=parsed.values["year"],
                session=parsed.values["session"],
                total_funding=parsed.values["total_funding"],
                city=parsed.values["city"],
                markets=parsed.values["markets"],
            )
        except ValidationError as error:
            record["issues"] = error.errors
            record.update(
                year=raw_input["year"],
                session=raw_input["session"],
                total_funding=raw_input["total_funding"],
                city=raw_input["city"],
            )
        records.append(record)
    return records


def load_dataset(content: bytes) -> tuple[list[dict[str, Any]], ColumnMapping, pd.DataFrame]:
    """Parse, map and validate a CSV upload. Raises DatasetError if unusable."""
    frame = read_csv_bytes(content)
    mapping = map_columns(list(frame.columns))
    if "year" not in mapping.single:
        accepted = ", ".join(f"'{alias}'" for alias in SINGLE_ALIASES["year"])
        raise DatasetError(
            "No batch or founding year column was found, and the model cannot score a startup "
            f"without it. Accepted headers: {accepted}."
        )
    return build_records(frame, mapping), mapping, frame
