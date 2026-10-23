"""Deterministic, evidence-based observations about one startup.

Every statement is computed from the record itself, the reference dataset
or the model output, and is tagged with its source so the UI and PDF can
keep factual attributes separate from model-derived conclusions. Nothing
here invents financial data; absent information is disclosed as absent.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from typing import Any

from diligence.data.store import Dataset
from diligence.ml.model import format_usd

MIN_GROUP = 15
NOT_IN_DATASET = [
    "revenue", "burn rate", "cash runway", "valuation", "headcount", "customer metrics", "cap table",
]


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class ReferenceStats:
    """Historical outcome statistics from the labelled reference dataset."""

    def __init__(self, reference: Dataset, classes: list[str]):
        labelled = [record for record in reference.records if record.get("status") in classes]
        self.classes = classes
        self.total = len(labelled)
        self.rates = {label: sum(r["status"] == label for r in labelled) / self.total for label in classes}
        self.funding = sorted(r["total_funding"] for r in labelled if r.get("total_funding") is not None)
        self.funding_by_status = {
            label: sorted(r["total_funding"] for r in labelled if r["status"] == label and r.get("total_funding") is not None)
            for label in classes
        }
        self.zero_funding_share = {
            label: (
                sum(1 for r in labelled if r["status"] == label and r.get("total_funding") == 0)
                / max(1, sum(1 for r in labelled if r["status"] == label and r.get("total_funding") is not None))
            )
            for label in classes
        }
        self.markets = self._group(labelled, lambda r: [m.lower() for m in r.get("markets") or []])
        self.cities = self._group(labelled, lambda r: [r["city"].lower()] if r.get("city") else [])
        self.years = self._group(labelled, lambda r: [str(r["year"])] if r.get("year") else [])
        self.market_names = {m.lower(): m for r in labelled for m in r.get("markets") or []}

    def _group(self, records, keys) -> dict[str, dict[str, Any]]:
        counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for record in records:
            for key in keys(record):
                counts[key][record["status"]] += 1
        groups = {}
        for key, values in counts.items():
            n = sum(values.values())
            groups[key] = {"n": n, "counts": dict(values), "rates": {c: values.get(c, 0) / n for c in self.classes}}
        return groups

    def funding_percentile(self, amount: float) -> int:
        if not self.funding:
            return 0
        return round(100 * bisect.bisect_right(self.funding, amount) / len(self.funding))

    @property
    def funding_median(self) -> float:
        return self.funding[len(self.funding) // 2] if self.funding else 0.0


def indicator(kind: str, title: str, detail: str, source: str) -> dict[str, str]:
    return {"kind": kind, "title": title, "detail": detail, "source": source}


def analyse(record: dict[str, Any], stats: ReferenceStats, dataset_kind: str) -> dict[str, Any]:
    """Return strengths, risk indicators, limitations and diligence questions."""
    strengths: list[dict[str, str]] = []
    risks: list[dict[str, str]] = []
    limitations: list[str] = []
    prediction = record.get("prediction")
    funding = record.get("total_funding") if record.get("model_input") else None
    base_dead = stats.rates["Dead"]
    base_exit = stats.rates["Exited"]

    funding_context = None
    if isinstance(funding, (int, float)):
        percentile = stats.funding_percentile(funding)
        funding_context = {
            "amount": funding,
            "formatted": format_usd(funding),
            "percentile": percentile,
            "reference_median": stats.funding_median,
            "reference_median_formatted": format_usd(stats.funding_median),
            "reference_count": len(stats.funding),
        }
        if funding == 0:
            risks.append(indicator(
                "risk", "No funding recorded",
                f"Reported total funding is $0. In the reference data, {pct(stats.zero_funding_share['Dead'])} of failed "
                f"companies with a funding figure reported $0, against {pct(stats.zero_funding_share['Operating'])} of operating ones.",
                "dataset",
            ))
        elif percentile >= 75:
            strengths.append(indicator(
                "strength", "Funding in the top quartile",
                f"{format_usd(funding)} is at the {ordinal(percentile)} percentile of {len(stats.funding)} reference companies "
                f"(median {format_usd(stats.funding_median)}).",
                "dataset",
            ))
        elif percentile <= 50:
            risks.append(indicator(
                "risk", "Funding at or below the reference median",
                f"{format_usd(funding)} is at the {ordinal(percentile)} percentile of {len(stats.funding)} reference companies "
                f"(median {format_usd(stats.funding_median)}).",
                "dataset",
            ))
        else:
            strengths.append(indicator(
                "strength", "Funding above the reference median",
                f"{format_usd(funding)} is at the {ordinal(percentile)} percentile (median {format_usd(stats.funding_median)}).",
                "dataset",
            ))
    else:
        limitations.append("Total funding is not reported, so the model imputes a typical value and flags it as missing.")

    if prediction:
        p_dead = prediction["probabilities"]["Dead"]
        p_exit = prediction["probabilities"]["Exited"]
        signal = prediction["failure_signal"]
        detail = (
            f"Estimated failure-class probability {pct(p_dead)} vs a {pct(base_dead)} base rate "
            f"({signal['ratio_to_base_rate']:.2f}x)."
        )
        if signal["level"] == "Lower":
            strengths.append(indicator("strength", "Failure-pattern signal below base rate", detail, "model"))
        else:
            risks.append(indicator("risk", f"{signal['level']} failure-pattern signal", detail, "model"))
        if p_exit / base_exit >= 1.5:
            strengths.append(indicator(
                "strength", "Exit-pattern signal above base rate",
                f"Estimated exit-class probability {pct(p_exit)} vs a {pct(base_exit)} base rate ({p_exit / base_exit:.2f}x).",
                "model",
            ))

    for market in record.get("markets") or []:
        group = stats.markets.get(market.lower())
        if not group or group["n"] < MIN_GROUP:
            continue
        dead_rate, exit_rate = group["rates"]["Dead"], group["rates"]["Exited"]
        counts = group["counts"]
        if dead_rate >= 1.5 * base_dead:
            risks.append(indicator(
                "risk", f"Higher historical failure share in {market}",
                f"{counts.get('Dead', 0)} of {group['n']} reference companies tagged {market} are recorded as Dead "
                f"({pct(dead_rate)} vs {pct(base_dead)} overall). Historical association, not causation.",
                "dataset",
            ))
        if exit_rate >= 1.5 * base_exit:
            strengths.append(indicator(
                "strength", f"Higher historical exit share in {market}",
                f"{counts.get('Exited', 0)} of {group['n']} reference companies tagged {market} exited "
                f"({pct(exit_rate)} vs {pct(base_exit)} overall). Historical association, not causation.",
                "dataset",
            ))

    if record.get("city"):
        group = stats.cities.get(record["city"].lower())
        if group and group["n"] >= MIN_GROUP:
            dead_rate = group["rates"]["Dead"]
            if dead_rate <= 0.67 * base_dead:
                strengths.append(indicator(
                    "strength", f"Lower historical failure share in {record['city']}",
                    f"{group['counts'].get('Dead', 0)} of {group['n']} reference companies in {record['city']} are recorded as Dead "
                    f"({pct(dead_rate)} vs {pct(base_dead)} overall).",
                    "dataset",
                ))
            elif dead_rate >= 1.5 * base_dead:
                risks.append(indicator(
                    "risk", f"Higher historical failure share in {record['city']}",
                    f"{group['counts'].get('Dead', 0)} of {group['n']} reference companies in {record['city']} are recorded as Dead.",
                    "dataset",
                ))
    else:
        limitations.append(
            "City is not reported. In the reference data, records without a city are disproportionately Dead, which "
            "reflects how well companies were documented rather than anything about location."
        )

    year = record.get("year")
    if isinstance(year, int):
        if year < 2005 or year > 2014:
            limitations.append(
                f"Batch year {year} is outside the 2005-2014 training range; the model is extrapolating."
            )
        elif year >= 2012:
            group = stats.years.get(str(year))
            share = pct(group["rates"]["Operating"]) if group else "most"
            limitations.append(
                f"Companies from the {year} batch had little time to exit or fail before the data was collected; "
                f"{share} of that batch is recorded as Operating, so the model leans toward Operating for recent batches."
            )
    if not record.get("markets"):
        limitations.append("No market or industry tags are reported.")
    if record.get("warnings"):
        limitations.extend(record["warnings"])
    limitations.append(
        "The dataset contains no " + ", ".join(NOT_IN_DATASET[:-1]) + f" or {NOT_IN_DATASET[-1]} information; "
        "none of it is used or inferred."
    )
    if dataset_kind == "reference":
        limitations.append(
            "Total funding and status reflect the date the source listings were collected (batches up to 2014), "
            "not the company's present situation."
        )
        if record.get("evaluation_split") == "train":
            limitations.append(
                "This company was in the model's training split, so the deployed model's estimate is in-sample. "
                "The cross-validated estimate shown alongside it was produced without this record."
            )

    considerations = [
        "Confirm current operating status, ownership and any acquisition directly from primary sources.",
        "Request audited or management financial statements: revenue, gross margin, burn rate and runway.",
        "Validate the funding history and cap table against filings or investor confirmations.",
    ]
    if not record.get("markets"):
        considerations.append("Establish the company's market and competitive position; none is recorded.")
    if any(item["source"] == "model" and item["kind"] == "risk" for item in risks):
        considerations.append(
            "Investigate why the profile resembles historically failed companies (stage, capital, market timing)."
        )
    if record.get("founders"):
        considerations.append("Run background and reference checks on the listed founders.")
    elif dataset_kind != "input":
        considerations.append("Identify the founding and management team; no founders are recorded.")
    else:
        considerations.append("Assess the founding and management team, which this model does not consider.")

    return {
        "strengths": strengths,
        "risks": risks,
        "limitations": limitations,
        "considerations": considerations,
        "funding_context": funding_context,
    }


def executive_summary(record: dict[str, Any], insight: dict[str, Any], stats: ReferenceStats, dataset_kind: str) -> list[str]:
    """Deterministic narrative paragraphs built only from structured values."""
    name = record["name"]
    paragraphs = []
    facts = []
    if record.get("year"):
        session = f"{record['session']} " if record.get("session") else ""
        facts.append(
            f"was part of the {session}{record['year']} Y Combinator batch" if dataset_kind == "reference"
            else f"has a batch/founding year of {record['year']}"
        )
    if record.get("city"):
        facts.append(f"is based in {record['city']}")
    if record.get("markets"):
        facts.append("is tagged " + ", ".join(record["markets"][:5]))
    if facts:
        paragraphs.append(f"{name} " + "; ".join(facts) + ".")
    funding = insight.get("funding_context")
    status = record.get("status")
    dataset_facts = []
    if funding:
        dataset_facts.append(
            f"total funding of {funding['formatted']} ({ordinal(funding['percentile'])} percentile of the reference set)"
        )
    if status:
        dataset_facts.append(f"a recorded status of {status}")
    if dataset_facts:
        source = "The submitted data reports " if dataset_kind == "input" else "The dataset reports "
        paragraphs.append(source + " and ".join(dataset_facts) + ".")

    prediction = record.get("prediction")
    if prediction:
        probs = prediction["probabilities"]
        signal = prediction["failure_signal"]
        paragraphs.append(
            "Model estimate: "
            + ", ".join(f"{label} {pct(probs[label])}" for label in ("Operating", "Exited", "Dead"))
            + f". The balanced decision rule assigns the {prediction['predicted_outcome']} class, and the failure-pattern "
            f"signal is {signal['level']} ({signal['ratio_to_base_rate']:.2f}x the {pct(stats.rates['Dead'])} base rate)."
        )
    else:
        paragraphs.append("The record could not be scored because required model inputs are missing or invalid.")
    paragraphs.append(
        f"These figures are statistical associations learned from {stats.total} historical companies. "
        "They are not an investment recommendation or a calibrated measure of investment risk."
    )
    return paragraphs
