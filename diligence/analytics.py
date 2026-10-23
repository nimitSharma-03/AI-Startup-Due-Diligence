"""Aggregate statistics for the dashboard and analytics pages."""

from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any

from diligence.data.store import Dataset

FUNDING_BUCKETS = [
    ("$0", 0, 0),
    ("< $100K", 0.01, 1e5),
    ("$100K-1M", 1e5, 1e6),
    ("$1M-10M", 1e6, 1e7),
    ("$10M-100M", 1e7, 1e8),
    ("> $100M", 1e8, float("inf")),
]
COMPLETENESS_FIELDS = [
    ("name", "Company name"),
    ("year", "Batch year"),
    ("session", "Batch session"),
    ("total_funding", "Total funding"),
    ("city", "City"),
    ("markets", "Markets"),
    ("description", "Description"),
    ("founders", "Founders"),
    ("status", "Recorded status"),
]


def _present(record: dict[str, Any], field: str) -> bool:
    value = record.get(field)
    if field == "name":
        return not str(value).startswith("Unnamed startup")
    if isinstance(value, list):
        return bool(value)
    return value not in (None, "")


def _counts(values, top: int | None = None) -> list[dict[str, Any]]:
    counter = Counter(values)
    items = counter.most_common(top)
    return [{"name": name, "count": count} for name, count in items]


def funding_bucket(amount: float) -> str:
    if amount == 0:
        return "$0"
    for label, low, high in FUNDING_BUCKETS[1:]:
        if low <= amount < high:
            return label
    return "> $100M"


DISPLAY_ORDER = ["Operating", "Exited", "Dead"]


def dashboard(dataset: Dataset, classes: list[str]) -> dict[str, Any]:
    classes = [label for label in DISPLAY_ORDER if label in classes]
    records = dataset.records
    scored = dataset.scored
    funding = [r["total_funding"] for r in records if isinstance(r.get("total_funding"), (int, float))]
    statuses = [r["status"] for r in records if r.get("status")]

    predicted = Counter(r["prediction"]["predicted_outcome"] for r in scored)
    signal = Counter(r["prediction"]["failure_signal"]["level"] for r in scored)
    mean_probabilities = (
        {label: round(sum(r["prediction"]["probabilities"][label] for r in scored) / len(scored), 4) for label in classes}
        if scored
        else {}
    )

    by_year: dict[int, Counter] = {}
    for record in records:
        if isinstance(record.get("year"), int):
            by_year.setdefault(record["year"], Counter())[record.get("status") or "Unlabelled"] += 1

    crosstab = None
    labelled = [r for r in scored if r.get("status") in classes]
    if labelled:
        crosstab = {
            "labels": classes,
            "matrix": [
                [sum(1 for r in labelled if r["status"] == actual and r["prediction"]["predicted_outcome"] == guess) for guess in classes]
                for actual in classes
            ],
            "rows": len(labelled),
            "note": "Recorded status vs model-assigned class on this dataset. For the reference dataset most rows were "
            "used in training, so this table is optimistic; see Model Analytics for hold-out results.",
        }

    funding_by_status = []
    for label in sorted(set(statuses)):
        values = [r["total_funding"] for r in records if r.get("status") == label and isinstance(r.get("total_funding"), (int, float))]
        if values:
            funding_by_status.append({"status": label, "count": len(values), "median": median(values), "mean": sum(values) / len(values)})

    return {
        "dataset": dataset.summary(),
        "totals": {
            "startups": len(records),
            "scored": len(scored),
            "with_funding": len(funding),
            "with_status": len(statuses),
            "markets": len({m.lower() for r in records for m in r.get("markets") or []}),
            "cities": len({r["city"].lower() for r in records if r.get("city")}),
        },
        "predicted_distribution": [{"name": label, "count": predicted.get(label, 0)} for label in classes],
        "failure_signal_distribution": [{"name": level, "count": signal.get(level, 0)} for level in ("Lower", "Moderate", "Elevated")],
        "mean_probabilities": mean_probabilities,
        "status_distribution": _counts(statuses),
        "industry_distribution": _counts([m for r in records for m in (r.get("markets") or [])], top=12),
        "primary_industry_distribution": _counts([(r.get("markets") or ["Not reported"])[0] for r in records], top=12),
        "city_distribution": _counts([r["city"] for r in records if r.get("city")], top=10),
        "funding": {
            "reported": len(funding),
            "missing": len(records) - len(funding),
            "zero": sum(1 for value in funding if value == 0),
            "total": sum(funding),
            "median": median(funding) if funding else None,
            "mean": sum(funding) / len(funding) if funding else None,
            "max": max(funding) if funding else None,
            "median_nonzero": median([v for v in funding if v > 0]) if any(v > 0 for v in funding) else None,
            "buckets": [{"name": label, "count": sum(1 for v in funding if funding_bucket(v) == label)} for label, _, _ in FUNDING_BUCKETS],
            "by_status": funding_by_status,
        },
        "year_distribution": [
            {"year": year, **{label: counts.get(label, 0) for label in sorted({*classes, *counts})}, "total": sum(counts.values())}
            for year, counts in sorted(by_year.items())
        ],
        "completeness": [
            {"field": field, "label": label, "share": round(sum(_present(r, field) for r in records) / max(1, len(records)), 4)}
            for field, label in COMPLETENESS_FIELDS
        ],
        "predicted_vs_recorded": crosstab,
    }
