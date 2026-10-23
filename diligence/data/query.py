"""Search, filter, sort and serialise startup records."""

from __future__ import annotations

import csv
import io
from typing import Any, Iterable

from diligence.errors import ApiError

SORT_KEYS = {
    "name": lambda r: (r["name"] or "").lower(),
    "year": lambda r: r.get("year") if isinstance(r.get("year"), int) else -1,
    "total_funding": lambda r: r.get("total_funding") if isinstance(r.get("total_funding"), (int, float)) else -1,
    "p_dead": lambda r: r["prediction"]["probabilities"]["Dead"] if r.get("prediction") else -1,
    "p_exited": lambda r: r["prediction"]["probabilities"]["Exited"] if r.get("prediction") else -1,
    "city": lambda r: (r.get("city") or "~").lower(),
    "status": lambda r: r.get("status") or "~",
}
MAX_PAGE_SIZE = 100


def summary(record: dict[str, Any]) -> dict[str, Any]:
    prediction = record.get("prediction")
    return {
        "id": record["id"],
        "row_number": record["row_number"],
        "name": record["name"],
        "year": record.get("year"),
        "session": record.get("session"),
        "city": record.get("city"),
        "total_funding": record.get("total_funding") if isinstance(record.get("total_funding"), (int, float)) else None,
        "markets": record.get("markets") or [],
        "status": record.get("status"),
        "scorable": prediction is not None,
        "issues": record["issues"],
        "prediction": None
        if prediction is None
        else {
            "predicted_outcome": prediction["predicted_outcome"],
            "probabilities": prediction["probabilities"],
            "failure_signal": prediction["failure_signal"]["level"],
        },
        "evaluation_split": record.get("evaluation_split"),
    }


def _number(value: str | None, name: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError as error:
        raise ApiError(400, "invalid_parameter", f"'{name}' must be a number.") from error


def filter_records(records: Iterable[dict[str, Any]], args) -> list[dict[str, Any]]:
    q = (args.get("q") or "").strip().lower()
    industry = (args.get("industry") or "").strip().lower()
    city = (args.get("city") or "").strip().lower()
    status = (args.get("status") or "").strip()
    predicted = (args.get("predicted") or "").strip()
    signal = (args.get("signal") or "").strip()
    year_min, year_max = _number(args.get("year_min"), "year_min"), _number(args.get("year_max"), "year_max")
    funding_min, funding_max = _number(args.get("funding_min"), "funding_min"), _number(args.get("funding_max"), "funding_max")

    result = []
    for record in records:
        if q and not (
            q in record["name"].lower()
            or q in (record.get("description") or "").lower()
            or any(q in market.lower() for market in record.get("markets") or [])
        ):
            continue
        if industry and industry not in {market.lower() for market in record.get("markets") or []}:
            continue
        if city and city != (record.get("city") or "").lower():
            continue
        if status and status != (record.get("status") or ""):
            continue
        prediction = record.get("prediction")
        if predicted and (not prediction or prediction["predicted_outcome"] != predicted):
            continue
        if signal and (not prediction or prediction["failure_signal"]["level"] != signal):
            continue
        year = record.get("year") if isinstance(record.get("year"), int) else None
        if year_min is not None and (year is None or year < year_min):
            continue
        if year_max is not None and (year is None or year > year_max):
            continue
        funding = record.get("total_funding") if isinstance(record.get("total_funding"), (int, float)) else None
        if funding_min is not None and (funding is None or funding < funding_min):
            continue
        if funding_max is not None and (funding is None or funding > funding_max):
            continue
        result.append(record)
    return result


def sort_records(records: list[dict[str, Any]], args) -> list[dict[str, Any]]:
    key = args.get("sort") or "name"
    if key not in SORT_KEYS:
        raise ApiError(400, "invalid_parameter", f"'sort' must be one of: {', '.join(SORT_KEYS)}.")
    order = args.get("order") or "asc"
    if order not in {"asc", "desc"}:
        raise ApiError(400, "invalid_parameter", "'order' must be 'asc' or 'desc'.")
    return sorted(records, key=SORT_KEYS[key], reverse=order == "desc")


def paginate(records: list[dict[str, Any]], args) -> tuple[list[dict[str, Any]], dict[str, int]]:
    try:
        page = max(1, int(args.get("page") or 1))
        size = min(MAX_PAGE_SIZE, max(1, int(args.get("page_size") or 25)))
    except ValueError as error:
        raise ApiError(400, "invalid_parameter", "'page' and 'page_size' must be integers.") from error
    start = (page - 1) * size
    return records[start : start + size], {
        "page": page,
        "page_size": size,
        "total": len(records),
        "pages": max(1, -(-len(records) // size)),
    }


def facets(records: list[dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    markets = Counter(market for record in records for market in record.get("markets") or [])
    cities = Counter(record["city"] for record in records if record.get("city"))
    years = sorted({record["year"] for record in records if isinstance(record.get("year"), int)})
    return {
        "industries": [{"name": name, "count": count} for name, count in markets.most_common(60)],
        "cities": [{"name": name, "count": count} for name, count in cities.most_common(40)],
        "statuses": sorted({record["status"] for record in records if record.get("status")}),
        "years": years,
        "predicted": ["Operating", "Exited", "Dead"],
        "signals": ["Lower", "Moderate", "Elevated"],
    }


def _safe_cell(value: Any) -> Any:
    """Neutralise spreadsheet formula injection in exported text cells."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def to_csv(records: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "row_number", "name", "year", "session", "city", "total_funding_usd", "markets", "recorded_status",
        "model_assigned_class", "p_operating", "p_exited", "p_dead", "failure_signal", "issues",
    ])
    for record in records:
        prediction = record.get("prediction")
        probs = prediction["probabilities"] if prediction else {}
        writer.writerow([_safe_cell(value) for value in (
            record["row_number"],
            record["name"],
            record.get("year"),
            record.get("session"),
            record.get("city"),
            record.get("total_funding") if isinstance(record.get("total_funding"), (int, float)) else "",
            "; ".join(record.get("markets") or []),
            record.get("status") or "",
            prediction["predicted_outcome"] if prediction else "",
            probs.get("Operating", ""),
            probs.get("Exited", ""),
            probs.get("Dead", ""),
            prediction["failure_signal"]["level"] if prediction else "",
            "; ".join(f"{k}: {v}" for k, v in record["issues"].items()),
        )])
    return buffer.getvalue()
