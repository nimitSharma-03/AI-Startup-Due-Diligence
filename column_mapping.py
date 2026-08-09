"""Semantic column matching for varied startup spreadsheets."""
from __future__ import annotations

import re
from typing import Iterable


ALIASES = {
    "company": ("company", "startup", "startup name", "company name", "business name", "name"),
    "revenue": ("revenue", "annual revenue", "revenue usd", "revenue $", "sales", "arr", "annual recurring revenue"),
    "funding": ("funding", "total funding", "funding amount", "capital raised", "investment", "total funds", "totalfunds", "raised"),
    "burn_rate": ("burn rate", "monthly burn", "cash burn", "burn"),
    "runway": ("runway", "cash runway", "runway months"),
    "employees": ("employees", "employee count", "headcount", "team size"),
    "industry": ("industry", "sector", "market", "vertical", "market 1"),
    "stage": ("funding stage", "stage", "round", "series"),
    "growth": ("growth", "growth %", "revenue growth", "growth rate", "mom growth", "yoy growth"),
    "arr": ("arr", "annual recurring revenue"), "mrr": ("mrr", "monthly recurring revenue"),
    "cac": ("cac", "customer acquisition cost"), "ltv": ("ltv", "lifetime value"),
    "gross_margin": ("gross margin", "gross margin %"), "ebitda": ("ebitda", "ebitda margin"),
    "valuation": ("valuation", "company valuation", "post money valuation", "enterprise value"),
    "churn": ("churn", "churn rate"), "year": ("year", "date", "month", "period", "founded", "founded year", "founding year"),
    "city": ("city", "headquarters", "hq", "location"), "description": ("description", "summary", "about"),
}


def normalize_column(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def find_column(columns: Iterable[str], concept: str) -> str | None:
    """Find the best matching source column for a canonical business concept."""
    normalized = {column: normalize_column(column) for column in columns}
    terms = ALIASES.get(concept, (concept.replace("_", " "),))
    for term in terms:
        needle = normalize_column(term)
        exact = next((column for column, value in normalized.items() if value == needle), None)
        if exact:
            return exact
    for term in terms:
        needle = normalize_column(term)
        partial = next((column for column, value in normalized.items() if needle in value or value in needle), None)
        if partial:
            return partial
    return None


def map_columns(columns: Iterable[str]) -> dict[str, str]:
    return {concept: column for concept in ALIASES if (column := find_column(columns, concept))}
