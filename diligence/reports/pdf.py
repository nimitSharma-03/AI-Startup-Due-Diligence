"""Company-specific PDF due-diligence reports built with ReportLab.

The report is generated in memory for exactly one selected record. Factual
dataset attributes, model-derived estimates and limitations are kept in
separate, labelled sections.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from diligence.insights import ReferenceStats, executive_summary, pct
from diligence.ml.model import FIELD_LABELS, ModelService, format_usd
from diligence.reports import charts

NAVY = colors.HexColor("#0B1F3A")
TEAL = colors.HexColor("#0F766E")
INK = colors.HexColor("#1E293B")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
PALE = colors.HexColor("#F8FAFC")
RED = colors.HexColor("#B91C1C")
GREEN = colors.HexColor("#15803D")
AMBER = colors.HexColor("#B45309")
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
WIDTH = PAGE_W - 2 * MARGIN
PLATFORM = "AI Startup Due Diligence Platform"


def _register_fonts() -> tuple[str, str]:
    """Use DejaVu Sans (bundled with matplotlib) for full Unicode coverage."""
    font_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    try:
        if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DejaVu", str(font_dir / "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(font_dir / "DejaVuSans-Bold.ttf")))
        return "DejaVu", "DejaVu-Bold"
    except Exception:  # pragma: no cover - fall back to built-in fonts
        return "Helvetica", "Helvetica-Bold"


FONT, BOLD = _register_fonts()


def _styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName=FONT, textColor=INK, alignment=TA_LEFT)
    return {
        "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=15, leading=19, textColor=NAVY, spaceBefore=4, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=10.5, leading=14, textColor=TEAL, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", fontSize=9, leading=13.5, spaceAfter=5, **base),
        "small": ParagraphStyle("small", fontSize=7.6, leading=10.5, textColor=MUTED, fontName=FONT),
        "cell": ParagraphStyle("cell", fontSize=8.2, leading=11, **base),
        "cell_bold": ParagraphStyle("cell_bold", fontSize=8.2, leading=11, fontName=BOLD, textColor=INK),
        "head": ParagraphStyle("head", fontSize=8, leading=10.5, fontName=BOLD, textColor=colors.white),
        "bullet": ParagraphStyle("bullet", fontSize=9, leading=13, leftIndent=10, bulletIndent=0, spaceAfter=3, **base),
        "cover_kicker": ParagraphStyle("ck", fontName=BOLD, fontSize=9, leading=12, textColor=colors.HexColor("#5EEAD4")),
        "cover_title": ParagraphStyle("ct", fontName=BOLD, fontSize=26, leading=31, textColor=colors.white),
        "cover_name": ParagraphStyle("cn", fontName=BOLD, fontSize=20, leading=25, textColor=colors.white),
        "cover_text": ParagraphStyle("cx", fontName=FONT, fontSize=9.5, leading=14, textColor=colors.HexColor("#CBD5E1")),
    }


S = _styles()


def text(value: Any, style: str = "body") -> Paragraph:
    if value is None or value == "" or value == []:
        value = "Not provided"
    return Paragraph(escape(str(value)), S[style])


def table(rows: list[list[Any]], widths: list[float], header: bool = True, zebra: bool = True) -> Table:
    data = []
    for index, row in enumerate(rows):
        style = "head" if header and index == 0 else "cell"
        data.append([cell if isinstance(cell, Paragraph) else text(cell, style) for cell in row])
    result = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        commands.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PALE]))
    result.setStyle(TableStyle(commands))
    return result


def key_values(rows: list[tuple[str, Any]]) -> Table:
    return table([[text(label, "cell_bold"), value] for label, value in rows], [WIDTH * 0.3, WIDTH * 0.7], header=False)


def chart(png: bytes, width: float = WIDTH) -> Image:
    image = Image(io.BytesIO(png))
    ratio = image.imageHeight / image.imageWidth
    image.drawWidth, image.drawHeight = width, width * ratio
    return image


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(escape(item), S["bullet"], bulletText="•") for item in items]


def source_note(label: str) -> Paragraph:
    return Paragraph(escape(label), S["small"])


def _cover(canvas, doc, meta: dict[str, Any]) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canvas.setFillColor(TEAL)
    canvas.rect(0, PAGE_H - 9 * mm, PAGE_W, 9 * mm, stroke=0, fill=1)
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.drawString(MARGIN, 14 * mm, "For educational and analytical use. Not investment, legal or financial advice.")
    canvas.drawRightString(PAGE_W - MARGIN, 14 * mm, f"Report ID {meta['report_id']}")
    canvas.restoreState()


def _later(canvas, doc, meta: dict[str, Any]) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, PAGE_H - 12 * mm, PAGE_W - MARGIN, PAGE_H - 12 * mm)
    canvas.setFont(BOLD, 7.5)
    canvas.setFillColor(NAVY)
    canvas.drawString(MARGIN, PAGE_H - 10 * mm, PLATFORM.upper())
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 10 * mm, meta["company"][:70])
    canvas.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    canvas.drawString(MARGIN, 9 * mm, f"Generated {meta['generated']}  ·  Not investment advice")
    canvas.drawRightString(PAGE_W - MARGIN, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report(
    record: dict[str, Any],
    dataset_name: str,
    dataset_kind: str,
    model: ModelService,
    stats: ReferenceStats,
    insight: dict[str, Any],
    explanation: list[dict[str, Any]] | None,
) -> bytes:
    """Render the PDF for one record and return its bytes."""
    now = datetime.now(timezone.utc)
    meta = {
        "company": record["name"],
        "generated": now.strftime("%d %b %Y %H:%M UTC"),
        "report_id": f"{now.strftime('%Y%m%d%H%M%S')}-{dataset_kind[:3].upper()}-{record['id']}",
    }
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Due Diligence Report - {record['name']}",
        author=PLATFORM,
        subject="Startup due diligence screening report",
    )
    prediction = record.get("prediction")
    priors = model.metadata["class_priors"]
    holdout = model.metrics["holdout"]["metrics"]
    cv = model.metrics["cross_validation"]["models"]["random_forest_calibrated"]
    story: list[Any] = []

    # 1-3. Cover --------------------------------------------------------------
    story += [
        Spacer(1, 55 * mm),
        Paragraph(PLATFORM.upper(), S["cover_kicker"]),
        Spacer(1, 4 * mm),
        Paragraph("Startup Due Diligence Report", S["cover_title"]),
        Spacer(1, 10 * mm),
        Paragraph(escape(record["name"]), S["cover_name"]),
        Spacer(1, 4 * mm),
    ]
    cover_facts = [
        part
        for part in (
            f"Batch {record.get('session') or ''} {record['year']}".replace("  ", " ") if record.get("year") else None,
            record.get("city"),
            ", ".join((record.get("markets") or [])[:3]) or None,
        )
        if part
    ]
    if cover_facts:
        story.append(Paragraph(escape("  ·  ".join(cover_facts)), S["cover_text"]))
    story += [
        Spacer(1, 18 * mm),
        Paragraph(f"Report generated: {escape(meta['generated'])}", S["cover_text"]),
        Paragraph(f"Dataset: {escape(dataset_name)} (row {record['row_number']})", S["cover_text"]),
        Paragraph(f"Model: {escape(model.metadata['model_name'])}, trained {escape(model.metadata['trained_at'][:10])}", S["cover_text"]),
        PageBreak(),
    ]

    # 4. Executive summary ------------------------------------------------------
    story.append(Paragraph("Executive summary", S["h1"]))
    for paragraph in executive_summary(record, insight, stats, dataset_kind):
        story.append(text(paragraph))
    summary_rows = [["Recorded status (dataset)", "Model-assigned class", "Failure-pattern signal", "Inputs provided"]]
    provided = 5 - len(record.get("missing_fields") or []) if record.get("model_input") else 0
    summary_rows.append(
        [
            record.get("status") or "Not recorded",
            prediction["predicted_outcome"] if prediction else "Not scored",
            f"{prediction['failure_signal']['level']} ({prediction['failure_signal']['ratio_to_base_rate']:.2f}x base rate)"
            if prediction
            else "Not scored",
            f"{provided} of 5 model inputs",
        ]
    )
    story += [Spacer(1, 3 * mm), table(summary_rows, [WIDTH / 4] * 4)]
    story.append(Spacer(1, 2 * mm))
    story.append(source_note(
        "Recorded status and attributes come from the dataset. The class, probabilities and signal are model estimates."
    ))

    # 5. Company profile -----------------------------------------------------
    story.append(Paragraph("Company profile", S["h1"]))
    story.append(source_note("Source: dataset attributes as supplied. Nothing in this section is model-derived."))
    story.append(Spacer(1, 2 * mm))
    profile = [
        ("Company", record["name"]),
        ("Description", record.get("description")),
        ("Batch year", record.get("year")),
        ("Batch session", record.get("session")),
        ("City", record.get("city")),
        ("Markets", ", ".join(record.get("markets") or []) or None),
        ("Founders listed", ", ".join(record.get("founders") or []) or None),
        ("Investors listed", ", ".join(record.get("investors") or []) or None),
        ("Website", record.get("website")),
        ("Recorded status", record.get("status")),
        ("Dataset row", record["row_number"]),
    ]
    story.append(key_values(profile))

    # 6-7. Financial information and funding analysis --------------------------
    story.append(CondPageBreak(90 * mm))
    story.append(Paragraph("Available financial information", S["h1"]))
    funding = insight.get("funding_context")
    story.append(key_values([
        ("Total funding raised", funding["formatted"] if funding else "Not provided"),
        ("Revenue, burn, runway, valuation", "Not present in the dataset; not estimated"),
        ("Headcount, customers, unit economics", "Not present in the dataset; not estimated"),
    ]))
    story.append(Paragraph("Funding analysis", S["h2"]))
    if funding:
        story.append(text(
            f"Reported total funding of {funding['formatted']} sits at the {funding['percentile']}th percentile of "
            f"{funding['reference_count']} reference companies with a funding figure (median {funding['reference_median_formatted']})."
        ))
        story.append(chart(charts.funding_chart(stats.funding, funding["amount"])))
    else:
        story.append(text("No funding figure is available for this company, so no funding comparison is possible."))
    by_status = []
    for label in ("Operating", "Exited", "Dead"):
        values = stats.funding_by_status.get(label, [])
        if values:
            by_status.append([label, str(len(values)), format_usd(values[len(values) // 2]), pct(stats.zero_funding_share[label])])
    if by_status:
        story.append(Spacer(1, 2 * mm))
        story.append(table([["Reference status", "Companies", "Median funding", "Share reporting $0"]] + by_status, [WIDTH / 4] * 4))
        story.append(source_note("Reference figures are descriptive statistics from the labelled training dataset."))

    # 8-9. Model prediction and confidence -------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("Model prediction", S["h1"]))
    if prediction:
        probs = prediction["probabilities"]
        story.append(text(
            "The calibrated Random Forest estimates the probability that a company with these attributes ended up in each "
            "recorded status class. The model-assigned class is the one whose probability most exceeds its historical base rate "
            "(a balanced decision rule), which is why it can differ from the single most likely class."
        ))
        story.append(chart(charts.probability_chart(probs, priors)))
        rows = [["Outcome class", "Estimated probability", "Historical base rate", "Ratio to base rate"]]
        for label in ("Operating", "Exited", "Dead"):
            rows.append([label, pct(probs[label]), pct(priors[label]), f"{prediction['lift_vs_base_rate'][label]:.2f}x"])
        story.append(table(rows, [WIDTH / 4] * 4))
        story.append(Spacer(1, 2 * mm))
        story.append(key_values([
            ("Model-assigned class", prediction["predicted_outcome"]),
            ("Most likely class", f"{prediction['most_likely_outcome']} ({pct(max(probs.values()))})"),
            ("Failure-pattern signal", f"{prediction['failure_signal']['level']}: {prediction['failure_signal']['description']}"),
        ]))
        oof = record.get("out_of_fold_probabilities")
        if oof:
            story.append(Spacer(1, 2 * mm))
            story.append(text(
                "Cross-validated estimate (model fitted without this company): "
                + ", ".join(f"{label} {pct(oof[label])}" for label in ("Operating", "Exited", "Dead"))
                + f". This record was in the {record.get('evaluation_split', 'unknown')} split of the deployed model."
            ))
    else:
        story.append(text("This record could not be scored: " + "; ".join(f"{k} {v}" for k, v in record["issues"].items())))

    story.append(Paragraph("Model confidence and limitations", S["h2"]))
    story.append(text(
        f"On {model.metadata['test_rows']} held-out companies the model reached balanced accuracy "
        f"{holdout['balanced_accuracy']:.2f}, macro F1 {holdout['f1_macro']:.2f} and macro ROC-AUC "
        f"{holdout['roc_auc_ovr_macro']:.2f} (log-loss {holdout['log_loss']:.2f}). Repeated 5-fold cross-validation on the training "
        f"split gave balanced accuracy {cv['balanced_accuracy']['mean']:.2f} ± {cv['balanced_accuracy']['std']:.2f} and ROC-AUC "
        f"{cv['roc_auc_ovr_macro']['mean']:.2f} ± {cv['roc_auc_ovr_macro']['std']:.2f}. {1 - holdout['accuracy']:.0%} of held-out "
        "companies were assigned the wrong class, so an individual estimate should be read as a weak prior, not a verdict."
    ))
    story += bullets([
        "Probabilities are sigmoid-calibrated on the training split; with 617 companies, calibration is approximate.",
        "Batch year is the strongest input because recent batches had less time to exit or fail" + _year_note(model) + ".",
        "The outcome label is the status at data collection, not a forecast horizon or an investment return.",
    ])

    # 10-11. Risk and strength indicators -------------------------------------
    story.append(CondPageBreak(70 * mm))
    story.append(Paragraph("Risk indicators", S["h1"]))
    story.append(_indicator_table(insight["risks"], "No risk indicators were triggered by the available data."))
    story.append(Paragraph("Strength indicators", S["h1"]))
    story.append(_indicator_table(insight["strengths"], "No strength indicators were triggered by the available data."))
    story.append(source_note(
        "Source 'dataset' = descriptive statistics of the reference data; 'model' = calibrated model estimate. "
        "Historical associations do not imply causation."
    ))

    # 12. Feature contributions ----------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("Feature contribution analysis", S["h1"]))
    if explanation and prediction:
        outcome = prediction["predicted_outcome"]
        story.append(text(
            "Each input is replaced in turn by values from 50 typical training companies while the others are held fixed. "
            "The bar shows how far this company's actual value moves the estimate compared with those typical values. "
            "This describes the model's behaviour; it does not show that an attribute causes an outcome."
        ))
        story.append(Paragraph(f"Contribution to P({outcome})", S["h2"]))
        story.append(chart(charts.contribution_chart(explanation, outcome)))
        if outcome != "Dead":
            story.append(Paragraph("Contribution to P(Dead)", S["h2"]))
            story.append(chart(charts.contribution_chart(explanation, "Dead")))
        rows = [["Input", "Value", "Operating", "Exited", "Dead"]]
        for item in explanation:
            c = item["contributions"]
            rows.append([item["label"], item["value"], *(f"{c[label] * 100:+.1f}" for label in ("Operating", "Exited", "Dead"))])
        story.append(Spacer(1, 2 * mm))
        story.append(KeepTogether([
            table(rows, [WIDTH * 0.2, WIDTH * 0.38, WIDTH * 0.14, WIDTH * 0.14, WIDTH * 0.14]),
            source_note("Values in percentage points of estimated probability."),
        ]))
    else:
        story.append(text("No contribution analysis is available because the record was not scored."))

    # 13. Investment-related considerations ------------------------------------
    story.append(CondPageBreak(60 * mm))
    story.append(Paragraph("Investment-related considerations", S["h1"]))
    story.append(text(
        "The platform does not make investment recommendations. The following diligence questions follow from the "
        "information that is present or missing for this company:"
    ))
    story += bullets(insight["considerations"])

    # 14. Data quality ---------------------------------------------------------
    story.append(Paragraph("Data quality and missing-information disclosures", S["h1"]))
    missing = [FIELD_LABELS[field] for field in record.get("missing_fields") or []]
    story.append(key_values([
        ("Model inputs not provided", ", ".join(missing) if missing else "None - all five inputs provided"),
        ("Validation issues", "; ".join(f"{k}: {v}" for k, v in record["issues"].items()) if record["issues"] else "None"),
        ("Dataset", f"{dataset_name} ({'reference data' if dataset_kind == 'reference' else 'user upload, held in memory only'})"),
    ]))
    story.append(Spacer(1, 2 * mm))
    story += bullets(insight["limitations"])

    # 15. Methodology ----------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("Methodology", S["h1"]))
    story += bullets([
        f"Data: {stats.total} Y Combinator companies from batches 2005-2014 with public SeedDB/CrunchBase listing fields and a "
        "recorded status (Operating, Exited, Dead).",
        "Inputs: batch year, batch session, total funding (log-scaled with a missing flag), city (cities with at least 10 "
        "companies, otherwise 'other'/'unknown') and market tags (tags with at least 10 companies).",
        "Excluded: company names, descriptions, URLs, logos, row indices and founder/investor listings, because they "
        "identify companies or leak the outcome through how well a company is documented.",
        f"Model: Random Forest (300 trees, depth {model.metadata['hyperparameters'].get('max_depth')}, min leaf "
        f"{model.metadata['hyperparameters'].get('min_samples_leaf')}, class-balanced) tuned by 5-fold CV and wrapped in "
        "sigmoid calibration. Stratified 80/20 split, random_state 42.",
        "Evaluation: hold-out test set plus 5x3 repeated stratified cross-validation, compared with majority-class, random and "
        "logistic-regression baselines.",
        "Explanations: interventional single-feature attribution against a fixed sample of training companies; global "
        "importance by permutation of raw inputs on the hold-out set.",
        "Narrative text in this report is generated deterministically from the structured values above. No language model is used.",
    ])

    # 16. Disclaimer -----------------------------------------------------------
    story.append(Paragraph("Disclaimer", S["h1"]))
    story.append(text(
        "This report was produced automatically for educational and analytical purposes. It is not investment, legal, tax or "
        "financial advice, is not produced by a regulated adviser, and must not be relied on for any investment decision. "
        "Model estimates are statistical associations learned from historical data with known gaps and biases. Verify all "
        "information independently with primary sources."
    ))

    doc.build(
        story,
        onFirstPage=lambda canvas, d: _cover(canvas, d, meta),
        onLaterPages=lambda canvas, d: _later(canvas, d, meta),
    )
    return buffer.getvalue()


def _indicator_table(items: list[dict[str, str]], empty: str) -> Any:
    if not items:
        return text(empty)
    rows = [["Indicator", "Evidence", "Source"]]
    rows += [[text(item["title"], "cell_bold"), item["detail"], item["source"]] for item in items]
    return table(rows, [WIDTH * 0.28, WIDTH * 0.6, WIDTH * 0.12])


def _year_note(model: ModelService) -> str:
    sensitivity = model.metrics.get("year_sensitivity")
    if not sensitivity:
        return ""
    with_year = sensitivity["with_year"]["roc_auc_ovr_macro"]["mean"]
    without = sensitivity["without_year"]["roc_auc_ovr_macro"]["mean"]
    return f"; neutralising it lowers cross-validated ROC-AUC from {with_year:.2f} to {without:.2f}"
