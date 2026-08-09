"""Deterministic, evidence-based investment insights from available data."""
from __future__ import annotations

import pandas as pd

from column_mapping import find_column, map_columns


def number(value) -> float | None:
    result = pd.to_numeric(pd.Series([value]).astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce").iloc[0]
    return None if pd.isna(result) else float(result)


def value(frame: pd.DataFrame, concept: str):
    column = find_column(frame.columns, concept)
    if not column or frame.empty: return None
    series = frame[column].dropna()
    return None if series.empty else series.iloc[0]


REPORT_METRICS = ("revenue", "employees", "burn_rate", "runway", "arr", "mrr", "cac", "ltv", "ebitda", "gross_margin", "churn", "growth", "funding", "valuation")


def report_metric_values(frame: pd.DataFrame) -> dict[str, float]:
    """Return only verified, numeric business metrics from the uploaded dataset."""
    reported = {name: number(value(frame, name)) for name in REPORT_METRICS}
    return {name: metric for name, metric in reported.items() if metric is not None}


def disclosure_observations(frame: pd.DataFrame) -> list[str]:
    """Professional, factual observations about information not supplied."""
    metrics = report_metric_values(frame)
    observations = []
    if not any(key in metrics for key in ("revenue", "arr", "mrr", "ebitda")):
        observations.append("The uploaded dataset does not contain audited revenue or profitability information. Financial performance verification should be completed during financial due diligence.")
    if not any(key in metrics for key in ("burn_rate", "runway")):
        observations.append("Operating cash burn and runway information were not included in the submitted documents and should be validated before investment.")
    if "employees" not in metrics:
        observations.append("Employee and organizational-capacity information was not included; operational due diligence should validate team depth and key-person dependencies.")
    if not any(key in metrics for key in ("growth", "churn", "cac", "ltv")):
        observations.append("Customer traction and unit-economics metrics were not supplied; commercial due diligence should validate retention, acquisition efficiency, and growth evidence.")
    return observations


def report_context(frame: pd.DataFrame, prediction: dict) -> dict:
    mapping = map_columns(frame.columns)
    revenue, funding, burn, runway, growth, employees, valuation, churn = (number(value(frame, key)) for key in ("revenue", "funding", "burn_rate", "runway", "growth", "employees", "valuation", "churn"))
    risk = prediction["risk_level"]
    confidence = float(prediction["confidence"])
    health_score = sum([growth is not None and growth >= 20, runway is not None and runway >= 18, funding is not None and funding > 0, revenue is not None and revenue > 0])
    if risk == "Low" and confidence >= 80 and health_score >= 2: recommendation = "Strong Buy"
    elif risk == "Low" or (risk == "Medium" and confidence >= 75 and health_score >= 3): recommendation = "Buy"
    elif risk == "High" and (confidence < 60 or health_score == 0): recommendation = "Avoid"
    elif risk == "High": recommendation = "Watchlist"
    else: recommendation = "Hold"
    reasons = []
    if growth is not None and growth > 20: reasons.append("Reported growth indicates encouraging market traction.")
    if runway is not None and runway < 12: reasons.append("Cash runway appears limited and requires close capital planning.")
    if burn is not None and revenue is not None and burn > revenue: reasons.append("Monthly burn exceeds reported revenue, creating funding pressure.")
    if funding is not None and funding > 0: reasons.append("Reported funding provides evidence of external capital support.")
    if not reasons: reasons.append("The assessment is based on the available model output; key operating metrics were not supplied.")
    verified = []
    if funding is not None: verified.append("reported funding")
    if valuation is not None: verified.append("reported valuation")
    if revenue is not None: verified.append("reported revenue")
    if growth is not None: verified.append("reported growth")
    evidence = ", ".join(verified) if verified else "the supplied company profile and model output"
    if confidence >= 75:
        summary = f"The assessment reflects {evidence} and a {prediction['confidence']:.1f}% model confidence score. Investment merits remain subject to verification of disclosures not included in the uploaded dataset."
    elif confidence >= 55:
        summary = f"The assessment reflects {evidence}; the model result has moderate confidence. Further financial and operational validation is recommended before investment."
    else:
        summary = f"The assessment is based on {evidence}, but the model confidence is limited. Additional due diligence is recommended before any investment decision."
    metrics = {"Revenue": revenue, "Funding": funding, "Monthly Burn": burn, "Runway (months)": runway, "Growth (%)": growth, "Employees": employees, "Valuation": valuation, "Churn (%)": churn}
    return {"mapping": mapping, "recommendation": recommendation, "reasons": reasons[:5], "summary": summary, "metrics": metrics}


def risk_sections(context: dict) -> list[tuple[str, str, str, str]]:
    limited_runway = context["metrics"]["Runway (months)"] is not None and context["metrics"]["Runway (months)"] < 12
    high_burn = context["metrics"]["Monthly Burn"] is not None and context["metrics"]["Revenue"] is not None and context["metrics"]["Monthly Burn"] > context["metrics"]["Revenue"]
    growth = context["metrics"]["Growth (%)"]
    missing_financials = any(context["metrics"][key] is None for key in ("Revenue", "Monthly Burn", "Runway (months)"))
    missing_employee_data = context["metrics"]["Employees"] is None
    missing_customer_data = growth is None and context["metrics"]["Churn (%)"] is None
    return [
        ("Financial Due Diligence", "High" if limited_runway or high_burn or missing_financials else "Low" if context["metrics"]["Runway (months)"] and context["metrics"]["Runway (months)"] >= 18 else "Medium", "Financial risk is elevated where revenue, liquidity, burn, or runway disclosures are absent or constrained.", "Verify financial statements, cash position, and liquidity assumptions."),
        ("Operational Due Diligence", "High" if missing_employee_data else "Low" if context["metrics"]["Employees"] >= 20 else "Medium", "Operational risk reflects the availability of verified employee and organizational information.", "Validate team structure, key-person dependencies, and operating capacity."),
        ("Commercial Due Diligence", "High" if missing_customer_data else "Low" if growth is not None and growth >= 20 else "Medium", "Commercial risk reflects the availability of verified growth, retention, and customer-economics data.", "Validate customer evidence, retention, and market demand."),
        ("Execution Risk", "High" if context["recommendation"] in {"Avoid", "Watchlist"} else "Low" if context["recommendation"] == "Strong Buy" else "Medium", "Execution risk follows the model assessment and the completeness of supplied evidence.", "Use milestone-based diligence and decision gates."),
    ]
