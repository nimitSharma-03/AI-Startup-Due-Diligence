"""Executive-grade PDF due-diligence report generator."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import html
import re
import time

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, Image, PageBreak, Paragraph, Spacer, Table, TableStyle

from chart_generator import create_charts
from column_mapping import find_column, map_columns
from insight_generator import disclosure_observations, number, report_context, report_metric_values, risk_sections, value

NAVY = colors.HexColor("#0B2D4D")
TEAL = colors.HexColor("#0F766E")
INK = colors.HexColor("#1E293B")
MUTED = colors.HexColor("#64748B")
PALE = colors.HexColor("#F1F7FA")
GREEN, YELLOW, RED = colors.HexColor("#15803D"), colors.HexColor("#B7791F"), colors.HexColor("#B91C1C")
MISSING = "Data Not Provided"


def _styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=30, leading=36, textColor=colors.white, alignment=TA_CENTER),
        "cover": ParagraphStyle("cover", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=colors.HexColor("#DCECF4"), alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=23, textColor=NAVY, spaceBefore=7, spaceAfter=9),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEAL, spaceBefore=9, spaceAfter=5),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.2, leading=14, textColor=INK, spaceAfter=4),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.5, textColor=INK),
        "cell_bold": ParagraphStyle("cell_bold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.2, leading=10.5, textColor=INK),
    }


def _header_footer(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(NAVY); canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#5EEAD4")); canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(A4[0] / 2, 48, "CONFIDENTIAL | INVESTMENT ASSESSMENT")
    else:
        canvas.setStrokeColor(colors.HexColor("#D7E2E5")); canvas.line(42, 806, 553, 806)
        canvas.setFont("Helvetica-Bold", 7.5); canvas.setFillColor(MUTED); canvas.drawString(42, 815, "AI STARTUP DUE DILIGENCE PLATFORM")
        canvas.setFont("Helvetica", 7.5); canvas.drawRightString(553, 28, f"CONFIDENTIAL  |  PAGE {doc.page}")
    canvas.restoreState()


def _p(text, style):
    """Render plain, safe text; source HTML must never leak into the PDF."""
    if text is None or pd.isna(text) or str(text).strip().lower() in {"", "nan", "none"}:
        text = MISSING
    clean = re.sub(r"<\s*br\s*/?\s*>", " ", html.unescape(str(text)), flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", "", clean)
    clean = re.sub(r"[\r\n]+", " ", clean).strip()
    return Paragraph(html.escape(clean), style)


def _table(rows, widths, styles, risk_column=None):
    converted = [[_p(cell, styles["cell_bold"] if row_no == 0 else styles["cell"]) for cell in row] for row_no, row in enumerate(rows)]
    table = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]), ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#D7E2E5")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
    if risk_column is not None:
        for index, row in enumerate(rows[1:], 1):
            level = str(row[risk_column]).lower(); colour = RED if level == "high" else GREEN if level == "low" else YELLOW
            commands += [("TEXTCOLOR", (risk_column, index), (risk_column, index), colour), ("FONTNAME", (risk_column, index), (risk_column, index), "Helvetica-Bold")]
    table.setStyle(TableStyle(commands)); return table


def _display(raw, percent=False):
    if raw is None or pd.isna(raw) or str(raw).strip() == "": return MISSING
    numeric = number(raw)
    if numeric is None: return str(raw)
    if percent and abs(numeric) <= 1: numeric *= 100
    return f"{numeric:,.1f}%" if percent else f"{numeric:,.0f}"


def _industry(frame) -> str:
    """Prefer named market/category data over generic labels such as Other."""
    generic = {"", "other", "others", "unknown", "n/a", "na", "not available"}
    candidate = value(frame, "industry")
    if candidate is not None and str(candidate).strip().lower() not in generic:
        return str(candidate).strip()
    for column in frame.columns:
        normalized = str(column).lower().replace(" ", "")
        if normalized in {"market1", "market", "category", "sector", "vertical"}:
            item = frame.iloc[0][column]
            if pd.notna(item) and str(item).strip().lower() not in generic:
                return str(item).strip()
    description = str(value(frame, "description") or "").lower()
    known = (("Artificial Intelligence", ("artificial intelligence", "machine learning", "generative ai")), ("FinTech", ("fintech", "payment", "financial")), ("HealthTech", ("health", "medical", "clinical")), ("SaaS", ("saas", "software platform", "subscription")), ("E-Commerce", ("e-commerce", "ecommerce", "marketplace", "retail")), ("CleanTech", ("climate", "energy", "sustainability")))
    return next((label for label, terms in known if any(term in description for term in terms)), MISSING)


def _profile(company, industry, city, year, description):
    if description is not None and str(description).strip().lower() not in {"", "nan", "none"}:
        return str(description).strip()
    facts = []
    if industry != MISSING: facts.append(f"operates in the {industry} sector")
    if year != MISSING: facts.append(f"was founded in {year}")
    if city != MISSING: facts.append(f"is headquartered in {city}")
    if not facts: return f"{company} is a startup currently under review; the supplied dataset does not include a company description."
    return f"{company} {facts[0]}" + (f", {facts[1]}" if len(facts) > 1 else "") + (f", and {facts[2]}." if len(facts) > 2 else ".")


def _business_feature(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(name).lower())
    blocked = ("unnamed", "index", "id", "profile", "url", "website", "logo", "company", "founder", "investor", "session")
    return bool(normalized) and not any(token in normalized for token in blocked)


def _metric_display(metric: float | None, percent=False) -> str:
    if not metric:
        return ""
    return _display(metric, percent)


def _meter(label, amount, colour, styles):
    amount = max(0, min(100, float(amount)))
    return Table([[_p(label, styles["cell_bold"])], [Table([["", ""]], colWidths=[4.35 * inch * amount / 100, 4.35 * inch * (100 - amount) / 100], rowHeights=[8], style=TableStyle([("BACKGROUND", (0, 0), (0, 0), colour), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#E2E8F0")), ("BOX", (0, 0), (-1, -1), 0, colors.white)]))], [_p(f"{amount:.0f}%", styles["small"])]], colWidths=[4.55 * inch], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), .3, colors.HexColor("#D7E2E5")), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))


def _swot(context):
    m = context["metrics"]; strengths=[]; weaknesses=[]; opportunities=[]; threats=[]
    if m["Funding"]: strengths.append("Reported external funding")
    if m["Growth (%)"] is not None and m["Growth (%)"] >= 20: strengths.append("Strong reported growth")
    if m["Employees"] is not None and m["Employees"] >= 20: strengths.append("Established team capacity")
    if m["Valuation"]: strengths.append("Valuation data supplied")
    if m["Monthly Burn"] is not None and m["Revenue"] is not None and m["Monthly Burn"] > m["Revenue"]: weaknesses.append("Burn exceeds reported revenue")
    if m["Runway (months)"] is not None and m["Runway (months)"] < 12: weaknesses.append("Limited cash runway")
    if m["Revenue"] is None: weaknesses.append("Revenue disclosure is incomplete")
    if m["Employees"] is None: weaknesses.append("Team-size disclosure is incomplete")
    if m["Growth (%)"] is not None and m["Growth (%)"] >= 20: opportunities.append("Reported growth supports further commercial validation")
    if m["Funding"] is not None: opportunities.append("Reported funding supports validation of capital deployment")
    if not opportunities: opportunities.append("No verified market-expansion opportunity can be assessed from the submitted data")
    if m["Revenue"] is None or m["Churn (%)"] is None: threats.append("Limited commercial disclosure increases diligence requirements")
    if m["Runway (months)"] is None: threats.append("Liquidity position requires independent verification")
    return [["Strengths", "Weaknesses"], ["; ".join(strengths or ["No material strengths can be confirmed from supplied data"]), "; ".join(weaknesses or ["No material financial weaknesses identified from supplied data"])], ["Opportunities", "Threats"], ["; ".join(opportunities), "; ".join(threats or ["No verified threat can be assessed from the submitted data"])]]


def generate_report(frame, prediction: dict, metrics: dict, output_path: Path, dataset_name: str | None = None) -> Path:
    """Generate a polished report for one pre-filtered company dataframe."""
    if len(frame) != 1: raise ValueError("A due-diligence report must be generated for exactly one company.")
    started = time.perf_counter(); styles = _styles(); output_path.parent.mkdir(parents=True, exist_ok=True)
    context = report_context(frame, prediction); mapping = map_columns(frame.columns)
    metric_values = report_metric_values(frame)
    company = str(value(frame, "company") or "Startup Under Review")
    industry = _industry(frame)
    city, year, description = (value(frame, concept) for concept in ("city", "year", "description"))
    doc = BaseDocTemplate(str(output_path), pagesize=A4, leftMargin=42, rightMargin=42, topMargin=42, bottomMargin=42, title=f"Due Diligence - {company}")
    from reportlab.platypus import PageTemplate
    doc.addPageTemplates([PageTemplate(id="report", frames=[Frame(42, 42, 511, 758, id="body")], onPage=_header_footer)])
    story=[]; now = datetime.now()
    # Cover uses an identity mark because remote logo URLs cannot be reliably embedded in an offline PDF.
    cover_fields = [str(item) for item in (industry if industry != MISSING else None, city, f"Founded {year}" if year is not None else None) if item is not None and str(item).strip()]
    story += [Spacer(1, 1.2*inch), Paragraph("AI STARTUP", styles["cover"]), Spacer(1, 8), Paragraph("DUE DILIGENCE", styles["cover_title"]), Paragraph("REPORT", styles["cover_title"]), Spacer(1, .34*inch), _p(company, ParagraphStyle("company", parent=styles["cover_title"], fontSize=20, leading=25)), Spacer(1, .25*inch)]
    if cover_fields: story.append(_p(" | ".join(cover_fields), styles["cover"]))
    story += [_p(now.strftime("%d %B %Y"), styles["cover"]), _p("Prepared by AI Startup Due Diligence Platform", styles["cover"]), Spacer(1, .3*inch), Paragraph("CONFIDENTIAL", ParagraphStyle("badge", parent=styles["cover"], fontName="Helvetica-Bold", textColor=colors.HexColor("#5EEAD4"))), PageBreak()]
    verified_context = []
    if industry != MISSING: verified_context.append(f"Industry: {industry}")
    if year is not None and str(year).strip(): verified_context.append(f"Founded: {_display(year)}")
    if "funding" in metric_values: verified_context.append(f"Reported funding: {_metric_display(metric_values['funding'])}")
    if "valuation" in metric_values: verified_context.append(f"Reported valuation: {_metric_display(metric_values['valuation'])}")
    story += [Paragraph("Executive Summary", styles["h1"]), _p(context["summary"], styles["body"])]
    if verified_context: story += [_p("Verified company context - " + "; ".join(verified_context) + ".", styles["body"])]
    story += [Spacer(1, 6), _table([["Overall Risk", "Recommendation", "Model Confidence", "Probability"], [prediction["risk_level"], context["recommendation"], f"{prediction['confidence']:.1f}%", f"{prediction['probability']:.1%}"]], [127.5]*4, styles), Spacer(1, 10), _meter("Confidence meter", prediction["confidence"], TEAL, styles), Spacer(1, 7), _meter("Probability meter", prediction["probability"]*100, NAVY, styles), Paragraph("Primary contributing factors", styles["h2"])]
    for reason in context["reasons"]: story.append(_p("- " + reason, styles["body"]))
    story += [Paragraph("Company Profile", styles["h1"])]
    profile = _profile(company, industry, _display(city), _display(year), description)
    story += [_p(profile, styles["body"]), Paragraph("Company Overview", styles["h2"])]
    overview = [("Industry", industry), ("Funding", _metric_display(metric_values.get("funding"))), ("Valuation", _metric_display(metric_values.get("valuation"))), ("Employees", _metric_display(metric_values.get("employees"))), ("Revenue", _metric_display(metric_values.get("revenue"))), ("Burn Rate", _metric_display(metric_values.get("burn_rate"))), ("Runway", _metric_display(metric_values.get("runway"))), ("Growth", _metric_display(metric_values.get("growth"), True)), ("Founding Year", _display(year)), ("Headquarters", _display(city))]
    overview = [(label, item) for label, item in overview if item not in {"", MISSING}]
    story += [_table([["Attribute", "Value"]] + overview, [175,336], styles), Paragraph("AI Assessment", styles["h1"]), _p(f"The model predicts {prediction['prediction']} with {prediction['confidence']:.1f}% confidence. The final recommendation is {context['recommendation']}, calibrated against prediction certainty, financial health and the dynamic risk profile.", styles["body"]), PageBreak()]
    importance_path = output_path.parents[2] / "model" / "feature_importance.csv"
    if importance_path.is_file():
        try:
            importance = pd.read_csv(importance_path)
            importance = importance[importance["feature"].map(_business_feature)].head(5)
            if {"feature", "importance"}.issubset(importance.columns) and not importance.empty:
                story += [Paragraph("Most Influential Model Features", styles["h2"]), _table([["Feature", "Relative Importance"]] + [[str(row.feature), f"{float(row.importance):.1%}"] for row in importance.itertuples()], [280,231], styles)]
        except (OSError, pd.errors.ParserError, ValueError):
            pass
    story += [PageBreak()]
    chart_frame = pd.DataFrame([metric_values])
    charts = create_charts(chart_frame, output_path.parent / "charts")
    if charts:
        story.append(Paragraph("Financial Analysis", styles["h1"]))
        for chart in charts: story += [Image(str(chart), width=6.65*inch, height=2.17*inch), Spacer(1, 6)]
    kpis = [("ARR", "arr", False), ("MRR", "mrr", False), ("CAC", "cac", False), ("LTV", "ltv", False), ("Gross Margin", "gross_margin", True), ("EBITDA", "ebitda", False), ("Churn", "churn", True), ("Revenue Growth", "growth", True), ("Monthly Burn", "burn_rate", False)]
    kpis = [(label, key, percent) for label, key, percent in kpis if key in metric_values]
    if kpis:
        rows=[["KPI", "Reported Value", "KPI", "Reported Value"]]
        for left, right in zip(kpis[::2], kpis[1::2] + [("", "", False)]): rows.append([left[0], _metric_display(metric_values[left[1]], left[2]), right[0], _metric_display(metric_values.get(right[1]), right[2]) if right[0] else "-"])
        story += [Paragraph("KPI Dashboard", styles["h1"]), _table(rows, [110,145,110,145], styles)]
    observations = disclosure_observations(frame)
    if observations:
        story += [Paragraph("Due Diligence Scope & Information Gaps", styles["h1"])]
        for observation in observations: story.append(_p("- " + observation, styles["body"]))
    story += [PageBreak(), Paragraph("Risk Analysis", styles["h1"])]
    story += [_table([["Risk Area", "Level", "Assessment", "Recommended Action"]] + [list(row) for row in risk_sections(context)], [92,53,190,176], styles, risk_column=1), Paragraph("Dynamic SWOT Analysis", styles["h1"]), _table(_swot(context), [255,256], styles), Paragraph("Final Recommendation", styles["h1"]), _p(f"{context['recommendation']} - This report is based only on information supplied in the uploaded dataset. Missing financial and operational disclosures reduce confidence and should be verified before any investment decision.", styles["body"]), PageBreak(), Paragraph("Appendix: Dataset Quality & Methodology", styles["h1"])]
    missing = [concept.replace("_", " ").title() for concept in ("revenue", "funding", "employees", "growth", "burn_rate", "runway", "year", "city", "industry") if concept not in mapping]
    ignored = [str(column) for column in frame.columns if str(column) not in mapping.values()]
    missing_pct = (frame.isna().sum().sum() / max(1, frame.shape[0] * frame.shape[1])) * 100
    required_metrics = ("revenue", "employees", "burn_rate", "runway", "arr", "mrr", "cac", "ltv", "ebitda", "gross_margin", "churn", "growth")
    completeness = len([name for name in required_metrics if name in metric_values]) / len(required_metrics) * 100
    completeness_label = "Strong" if completeness >= 75 else "Moderate" if completeness >= 45 else "Limited" if completeness >= 20 else "Poor"
    processing_time = time.perf_counter() - started
    quality = [["Dataset Quality Check", "Value"], ["Dataset name", dataset_name or "Uploaded spreadsheet"], ["Records processed", str(len(frame))], ["Detected columns", str(len(frame.columns))], ["Mapped columns", ", ".join(f"{k}: {v}" for k,v in mapping.items()) or "None"], ["Missing expected columns", ", ".join(missing) or "None"], ["Ignored columns", ", ".join(ignored) or "None"], ["Data completeness score", f"{completeness:.0f}% - {completeness_label}"], ["Missing cell percentage", f"{missing_pct:.1f}%"], ["Features used", str(len(frame.columns))], ["Model used", "Random Forest Classifier"], ["Model accuracy", f"{float(metrics.get('accuracy') or 0):.1%}"], ["Prediction confidence", f"{prediction['confidence']:.1f}%"], ["Generated timestamp", now.strftime("%Y-%m-%d %H:%M:%S")], ["Processing time", f"{processing_time:.2f} seconds"], ["Report version", "2.2"]]
    story += [_table(quality, [175,336], styles), Spacer(1, 10), _p("This report is based only on information supplied in the uploaded dataset. Missing financial and operational disclosures reduce confidence and should be verified before any investment decision. This document is not a substitute for legal, financial, tax, security, or technical diligence.", styles["small"])]
    doc.build(story); return output_path
