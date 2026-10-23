"""Input schema shared by training, the prediction API and uploads.

Every record that reaches the model is first converted to the canonical
form defined here, so training and serving use exactly the same parsing.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

MODEL_COLUMNS = ["year", "session", "total_funding", "city", "markets"]
SESSIONS = ("Winter", "Summer")
TRAINING_YEAR_RANGE = (2005, 2014)
MIN_YEAR = 1990
MAX_FUNDING = 1e12
MAX_MARKETS = 10
MAX_TEXT = 100

# Human-readable description of each model input, served to the frontend so
# the prediction form is generated from the schema the model actually uses.
FIELD_SPECS: list[dict[str, Any]] = [
    {
        "name": "year",
        "label": "Y Combinator batch year",
        "type": "integer",
        "required": True,
        "min": MIN_YEAR,
        "max": date.today().year + 1,
        "help": "Year of the accelerator batch. The model was trained on batches 2005-2014.",
    },
    {
        "name": "session",
        "label": "Batch session",
        "type": "enum",
        "required": False,
        "options": list(SESSIONS),
        "help": "Winter or Summer batch. Optional.",
    },
    {
        "name": "total_funding",
        "label": "Total funding raised (USD)",
        "type": "number",
        "required": False,
        "min": 0,
        "help": "Cumulative funding in US dollars, e.g. 1500000 or 1.5M. Leave blank if unknown.",
    },
    {
        "name": "city",
        "label": "Headquarters city",
        "type": "string",
        "required": False,
        "help": "City name as text. Leave blank if unknown.",
    },
    {
        "name": "markets",
        "label": "Markets / industries",
        "type": "list",
        "required": False,
        "max_items": MAX_MARKETS,
        "help": "Up to 10 market tags, comma separated, e.g. SaaS, Analytics.",
    },
]

_MULTIPLIERS = {"k": 1e3, "m": 1e6, "mm": 1e6, "b": 1e9, "bn": 1e9}
_MISSING_TOKENS = {"", "nan", "none", "null", "n/a", "na", "-", "unknown", "not available"}


class ValidationError(ValueError):
    """Raised when a record cannot be converted to a valid model input."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{key}: {value}" for key, value in errors.items()))
        self.errors = errors


@dataclass
class ParsedRecord:
    """A canonical model input plus non-fatal notes about it."""

    values: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def is_missing(value: Any) -> bool:
    """Return whether a raw value should be treated as absent."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, (list, tuple)):
        return len(value) == 0
    return str(value).strip().lower() in _MISSING_TOKENS


def parse_money(value: Any) -> float:
    """Parse amounts such as 1500000, "$1.5M", "2,000,000" or "750k"."""
    if isinstance(value, bool):
        raise ValueError("must be a number")
    if isinstance(value, (int, float)):
        amount = float(value)
    else:
        text = str(value).strip().lower().replace(",", "").replace("$", "").replace("usd", "").strip()
        match = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*([a-z]*)", text)
        if not match or (match.group(2) and match.group(2) not in _MULTIPLIERS):
            raise ValueError("must be a number such as 1500000 or 1.5M")
        amount = float(match.group(1)) * _MULTIPLIERS.get(match.group(2), 1.0)
    if math.isnan(amount) or math.isinf(amount):
        raise ValueError("must be a finite number")
    if amount < 0:
        raise ValueError("cannot be negative")
    if amount > MAX_FUNDING:
        raise ValueError("is implausibly large")
    return amount


def parse_year(value: Any) -> int:
    """Parse a four-digit year, accepting floats such as 2012.0 from CSVs."""
    if isinstance(value, bool):
        raise ValueError("must be a year")
    try:
        number = float(str(value).strip())
    except ValueError as error:
        raise ValueError("must be a four-digit year") from error
    if not number.is_integer():
        raise ValueError("must be a whole year")
    year = int(number)
    if year < MIN_YEAR or year > date.today().year + 1:
        raise ValueError(f"must be between {MIN_YEAR} and {date.today().year + 1}")
    return year


def parse_session(value: Any) -> str:
    """Normalise batch session names (W, S, winter, Summer 2012...)."""
    text = str(value).strip().lower()
    if text.startswith("w"):
        return "Winter"
    if text.startswith("s"):
        return "Summer"
    raise ValueError("must be Winter or Summer")


def clean_text(value: Any) -> str:
    """Collapse whitespace and cap the length of a free-text value."""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) > MAX_TEXT:
        raise ValueError(f"must be at most {MAX_TEXT} characters")
    return text


def parse_markets(value: Any) -> list[str]:
    """Accept a list or a comma/semicolon/pipe separated string of tags."""
    if is_missing(value):
        return []
    items = value if isinstance(value, (list, tuple)) else re.split(r"[,;|]", str(value))
    markets: list[str] = []
    for item in items:
        if is_missing(item):
            continue
        tag = clean_text(item)
        if tag and tag.lower() not in {existing.lower() for existing in markets}:
            markets.append(tag)
    if len(markets) > MAX_MARKETS:
        raise ValueError(f"must contain at most {MAX_MARKETS} tags")
    return markets


def parse_record(raw: dict[str, Any]) -> ParsedRecord:
    """Validate a raw record and convert it to the canonical model input.

    Raises ValidationError listing every invalid field. Optional fields that
    are absent are recorded in ``missing`` so callers can disclose them.
    """
    if not isinstance(raw, dict):
        raise ValidationError({"record": "must be a JSON object"})

    errors: dict[str, str] = {}
    values: dict[str, Any] = {}
    missing: list[str] = []
    warnings: list[str] = []

    parsers = {
        "year": parse_year,
        "session": parse_session,
        "total_funding": parse_money,
        "city": clean_text,
    }
    for name, parser in parsers.items():
        raw_value = raw.get(name)
        if is_missing(raw_value):
            values[name] = None
            missing.append(name)
            continue
        try:
            values[name] = parser(raw_value)
        except ValueError as error:
            errors[name] = str(error)

    try:
        values["markets"] = parse_markets(raw.get("markets"))
        if not values["markets"]:
            missing.append("markets")
    except ValueError as error:
        errors["markets"] = str(error)

    if values.get("year") is None and "year" not in errors:
        errors["year"] = "is required"
    if errors:
        raise ValidationError(errors)

    low, high = TRAINING_YEAR_RANGE
    if not low <= values["year"] <= high:
        warnings.append(
            f"Batch year {values['year']} is outside the training range {low}-{high}; "
            "the model is extrapolating and the result is less reliable."
        )
    if values["city"] == "":
        values["city"] = None
    return ParsedRecord(values=values, warnings=warnings, missing=missing)
