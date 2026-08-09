from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, NextPageTemplate,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "pdf" / "AI_Due_Diligence_Project_Training_Manual.pdf"

NAVY = colors.HexColor("#0B132B")
SLATE = colors.HexColor("#334155")
TEAL = colors.HexColor("#0F766E")
MINT = colors.HexColor("#CCFBF1")
SKY = colors.HexColor("#E0F2FE")
PINK = colors.HexColor("#FCE7F3")
AMBER = colors.HexColor("#FEF3C7")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#526075")
LINE = colors.HexColor("#D9E2EC")
WHITE = colors.white


class ManualDoc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, "toc_level", None) is not None:
            text = flowable.getPlainText()
            level = flowable.toc_level
            self.notify("TOCEntry", (level, text, self.page))
            key = f"h{level}-{self.page}-{text[:20]}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=False)


class ArchitectureDiagram(Flowable):
    def __init__(self, labels, width=470, height=245):
        Flowable.__init__(self)
        self.labels, self.width, self.height = labels, width, height

    def draw(self):
        c = self.canv
        box_w, box_h = 205, 31
        x = (self.width - box_w) / 2
        y = self.height - box_h - 8
        for i, (title, subtitle, color) in enumerate(self.labels):
            c.setFillColor(color)
            c.roundRect(x, y, box_w, box_h, 7, fill=1, stroke=0)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(x + box_w / 2, y + 18, title)
            c.setFillColor(SLATE)
            c.setFont("Helvetica", 7.3)
            c.drawCentredString(x + box_w / 2, y + 7.5, subtitle)
            if i < len(self.labels) - 1:
                c.setStrokeColor(TEAL); c.setLineWidth(1.2)
                c.line(x + box_w / 2, y - 1, x + box_w / 2, y - 10)
                c.setFillColor(TEAL)
                c.setLineWidth(0.5)
                c.line(x + box_w / 2 - 3, y - 7, x + box_w / 2, y - 10)
                c.line(x + box_w / 2 + 3, y - 7, x + box_w / 2, y - 10)
            y -= 40


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=31, leading=37, textColor=WHITE, alignment=TA_CENTER, spaceAfter=12),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["BodyText"], fontSize=13, leading=19, textColor=colors.HexColor("#CDE5F0"), alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=NAVY, spaceBefore=5, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=TEAL, spaceBefore=10, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=NAVY, spaceBefore=7, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.1, leading=13.2, textColor=INK, spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.6, leading=10, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9.4, textColor=INK),
        "cell_bold": ParagraphStyle("cell_bold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.4, textColor=INK),
        "header": ParagraphStyle("header", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.4, textColor=WHITE),
        "code": ParagraphStyle("code", parent=base["Code"], fontName="Courier", fontSize=7.4, leading=10, textColor=INK, backColor=colors.HexColor("#F1F5F9"), borderColor=LINE, borderWidth=.4, borderPadding=7, spaceBefore=4, spaceAfter=8),
        "quote": ParagraphStyle("quote", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=9, leading=13, textColor=SLATE, leftIndent=9, rightIndent=9),
    }


S = styles()


def p(text, style="body"):
    return Paragraph(str(text).replace("\n", "<br/>"), S[style])


def h(text, level=1):
    style = f"h{level}"
    item = p(text, style)
    item.toc_level = level - 1
    return item


def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet>{text}", S["body"])


def callout(title, text, color=SKY):
    content = [[p(title, "cell_bold")], [p(text, "cell")]]
    return Table(content, colWidths=[470], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), .5, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))


def table(headers, rows, widths):
    converted = [[p(x, "header") for x in headers]] + [[p(x, "cell") for x in row] for row in rows]
    return Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT", style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), .35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))


def header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(LINE); canvas.line(42, 807, 553, 807)
        canvas.setFillColor(TEAL); canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawString(42, 816, "VENTURESIGNAL | AI STARTUP DUE DILIGENCE")
        canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(553, 816, "Project Training Manual")
        canvas.line(42, 35, 553, 35)
        canvas.drawString(42, 24, "Internal team training guide - based on current repository implementation")
        canvas.drawRightString(553, 24, f"Page {doc.page}")
    canvas.restoreState()


def add_file(story, name, purpose, run, calls, imports, logic, inp, out, errors, viva):
    story += [h(name, 2), p(f"<b>Purpose.</b> {purpose}"), p(f"<b>When it runs / caller.</b> {run}"),
              p(f"<b>Calls / dependencies.</b> {calls}"), p(f"<b>Imports.</b> {imports}"),
              p(f"<b>Important logic.</b> {logic}"), p(f"<b>Input -> output.</b> {inp} -> {out}"),
              p(f"<b>Error handling.</b> {errors}"), callout("30-second viva explanation", viva, MINT), Spacer(1, 5)]


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = ManualDoc(str(OUT), pagesize=A4, leftMargin=42, rightMargin=42, topMargin=52, bottomMargin=48,
                    title="AI Due Diligence Project Training Manual", author="AI Startup Due Diligence Platform")
    frame = Frame(42, 48, 511, 745, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=header_footer)])
    story = []

    # Cover
    story += [Spacer(1, 1.2*inch)]
    cover = Table([[p("VENTURESIGNAL", "cover_sub")], [p("AI STARTUP\nDUE DILIGENCE", "title")],
                   [p("Project Training Manual", "cover_sub")], [Spacer(1, 12)],
                   [p("A codebase-guided handbook for new developers, teammates, and project-review preparation.", "cover_sub")],
                   [Spacer(1, 36)], [p("Version 1.0 | 07 August 2026", "cover_sub")],
                   [p("Team: Not specified in the repository", "cover_sub")]], colWidths=[430], rowHeights=[30, 85, 28, 14, 50, 20, 24, 20], style=TableStyle([
                       ("BACKGROUND", (0, 0), (-1, -1), NAVY), ("BOX", (0, 0), (-1, -1), 1, TEAL),
                       ("LEFTPADDING", (0, 0), (-1, -1), 22), ("RIGHTPADDING", (0, 0), (-1, -1), 22),
                       ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                   ]))
    story += [cover, Spacer(1, 28), callout("What this manual is", "This PDF was produced from the current repository. It explains what is actually implemented, including limitations and unused paths; it does not describe planned functionality as complete.", SKY), PageBreak()]

    # TOC
    story += [h("Table of Contents", 1), p("Section page numbers are generated automatically when this PDF is built."), Spacer(1, 8)]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("toc0", fontName="Helvetica", fontSize=9.5, leading=15, leftIndent=0, firstLineIndent=0, textColor=NAVY),
                       ParagraphStyle("toc1", fontName="Helvetica", fontSize=8.4, leading=12, leftIndent=16, firstLineIndent=0, textColor=SLATE)]
    story += [toc, PageBreak()]

    # Overview
    story += [h("1. Project Overview", 1), p("<b>Project title:</b> AI Startup Due Diligence Platform, presented in the web interface as VentureSignal."),
              p("<b>Problem:</b> startup screening can be inconsistent and slow. This project turns structured startup data into a historical outcome prediction and a selected-company due-diligence PDF."),
              p("<b>Why it exists:</b> to demonstrate an end-to-end ML product: data cleaning, supervised training, API inference, browser UI, spreadsheet handling, visual reporting, and downloadable output."),
              h("Objectives", 2)]
    for t in ["Train a multiclass startup-outcome classifier from historical records.", "Score an individual startup and show prediction, probability, confidence, and risk label.", "Read CSV/XLSX/XLS uploads, let the user select one record, and generate a report.", "Show model metadata, held-out metrics, and feature importance in the browser."]:
        story.append(bullet(t))
    story += [h("Real-world use case", 2), p("An analyst uploads a portfolio spreadsheet, selects one company, and receives a PDF with the model result, available financial context, information gaps, risk areas, and a rule-based recommendation. The output is decision support only, not legal, financial, or investment advice."),
              callout("Critical implementation fact", "The codebase does not use OpenAI, an LLM, prompts, embeddings, or external AI APIs. Its AI module is a scikit-learn Random Forest and its report text is generated by deterministic Python rules.", AMBER), PageBreak()]

    # technology
    story += [h("2. Technology Stack", 1), table(["Technology", "Why used", "Where used / benefit"], [
        ["React 19 + React DOM", "Builds a reusable, interactive browser UI.", "frontend/src; component state and declarative rendering."],
        ["Vite", "Fast development server and production bundling.", "frontend package scripts and vite.config.js."],
        ["Python", "Strong ecosystem for data, ML, APIs, and documents.", "All root backend/ML/report modules."],
        ["Flask + Flask-CORS", "Lightweight REST routes and browser cross-origin access.", "app.py; exposes JSON/PDF endpoints."],
        ["pandas + openpyxl", "Reads/manipulates CSV and Excel tabular data.", "Training, upload ingestion, model input, and reports."],
        ["scikit-learn", "Label encoders, split, Random Forest, and metrics.", "preprocess.py, train_model.py, predict.py."],
        ["joblib", "Persists Python ML artifacts.", "Saves/loads model, feature order, and encoders."],
        ["ReportLab + Matplotlib", "Builds a styled PDF and local chart images.", "pdf_generator.py and chart_generator.py."],
        ["Axios, Recharts, Framer Motion, Lucide", "HTTP, charts, animation, icons.", "frontend service/components."],
    ], [105, 160, 205]), h("AI/OpenAI clarification", 2), p("The requested category 'AI/OpenAI' is documented accurately: AI is used through the local Random Forest model. OpenAI is not present in requirements, imports, or runtime code."), PageBreak()]

    # Architecture
    story += [h("3. Complete Architecture", 1), p("The platform has two separate flows: offline model training and online browser/API/report execution."), h("Runtime architecture", 2),
              ArchitectureDiagram([
                  ("React + Vite frontend", "dashboard, upload, form, preview", SKY),
                  ("Flask REST API", "validation and orchestration", MINT),
                  ("Spreadsheet processing", "CSV/XLS/XLSX, header matching", colors.HexColor("#EDE9FE")),
                  ("Random Forest analysis", "saved model + encoders + feature order", AMBER),
                  ("Risk and report rules", "deterministic insights and charts", PINK),
                  ("PDF output", "ReportLab document returned to browser", MINT),
              ]),
              h("Architecture block explanation", 2)]
    for t in ["Frontend: Dashboard.jsx gathers inputs, calls api.js, shows state and Blob PDF preview.", "Backend: app.py owns HTTP routes and converts request data to functions/HTTP responses.", "Excel processing: dataset_preprocessing.py reads uploads; column_mapping.py recognizes common business header names.", "AI analysis: predict.py loads joblib artifacts, aligns columns, encodes categoricals, and calls predict/predict_proba.", "Risk detection: get_risk_level() gives a simple UI label; insight_generator.py evaluates available business metrics.", "PDF generation: ReportLab assembles text/tables and embeds Matplotlib charts under output/pdf/."]:
        story.append(bullet(t))
    story += [h("Training architecture", 2), p("data/CleanStartups.csv -> preprocess.py -> data/processed_startups.csv + model/label_encoders.pkl -> train_model.py -> risk_model.pkl, features.pkl, metrics.json, feature_importance.csv."), PageBreak()]

    # tree
    tree = """AI-Startup-Due-Diligence/
  app.py | predict.py | preprocess.py | train_model.py
  dataset_preprocessing.py | column_mapping.py | insight_generator.py
  chart_generator.py | pdf_generator.py | check_data.py
  requirements.txt | README.md
  data/    CleanStartups.csv, processed_startups.csv
  model/   risk_model.pkl, features.pkl, label_encoders.pkl, metrics.json, feature_importance.csv
  output/pdf/  runtime-generated reports and chart PNGs
  frontend/
    package.json, package-lock.json, vite.config.js, eslint.config.js, index.html
    public/  favicon.svg, icons.svg
    src/
      main.jsx, App.jsx, index.css, App.css, assets/
      services/api.js
      pages/Dashboard.jsx, About.jsx
      components/ UploadCard.jsx, PredictionCard.jsx, RiskGauge.jsx, Statistics.jsx,
                  FeatureImportance.jsx, Charts.jsx, Hero.jsx, Navbar.jsx, Footer.jsx,
                  Loading.jsx, Sidebar.jsx
    dist/  generated production frontend files"""
    story += [h("4. Folder Structure", 1), p("The following is the application-relevant tree. Git/tool caches, Python bytecode, and temporary files are intentionally not source modules."), p(tree, "code"),
              table(["Location", "What it contains", "How it connects"], [
                  ["data/", "Raw and processed startup CSVs.", "Feeds model training; CleanStartups supplies sample form data."],
                  ["model/", "Persisted ML artifacts.", "Loaded by predict.py and exposed as metadata by app.py."],
                  ["output/pdf/", "Generated reports and temporary chart assets.", "Written by pdf_generator.py and sent by Flask."],
                  ["frontend/src/", "React UI code, styles, API layer.", "Calls Flask and renders results."],
                  ["frontend/dist/", "Built static files.", "Generated by npm run build; never hand-edit."],
              ], [115, 180, 175]), PageBreak()]

    # File by file
    story += [h("5. File-by-File Explanation", 1), p("This is the core teaching section. Each card identifies why the file exists, its trigger/caller, dependencies, key logic, data contract, failure behaviour, and a short viva script."), h("5.1 Backend and machine-learning files", 2)]
    add_file(story, "app.py", "The Flask REST API entry point and application orchestrator.", "Run by python app.py; create_app() registers routes. The frontend calls its endpoints through api.js.", "Calls read_startup_file/adapt_for_model/filter_company_data/get_company_list, predict_dataframe/load_prediction_artifacts, and generate_report.", "Built-in: json, logging, pathlib, typing. Third-party: pandas, Flask, Flask-CORS, Werkzeug. Local: dataset_preprocessing, pdf_generator, predict.", "Routes: /, /health, /predict, /predict/csv, /reports/companies, /reports/generate, /model-info, /metrics. Helpers set file rules, row parsing, risk labels, and metadata loading.", "JSON or multipart upload", "JSON response or PDF download", "PredictionError and BadRequest become JSON 400; 413 explains 10 MB upload limit; health returns 503 when artifacts cannot load.", "app.py is the backend gateway. It validates browser requests, calls the ML/report modules, and returns safe JSON or a downloadable PDF.")
    add_file(story, "predict.py", "The reusable model inference pipeline.", "Called by app.py health, prediction, batch, and report routes.", "Loads joblib artifacts from model/. Uses pandas and LabelEncoder.", "Built-in: logging, pathlib, typing. Third-party: joblib, pandas, sklearn LabelEncoder.", "Validates artifact paths; loads model/features/encoders; reorders required columns; encodes categoricals; calls model.predict and predict_proba; decodes Fate classes.", "Input DataFrame", "Copy of original DataFrame plus Prediction, Probability, Confidence", "Raises PredictionError for missing/corrupt artifacts, bad values, or absent Fate encoder. Unseen categories warn and fall back to 0.", "predict.py guarantees that inference uses the same model schema and label encoders as training before it makes a prediction.")
    add_file(story, "preprocess.py", "Cleans the raw training CSV and creates training-time label encoders.", "Called by train_model.py; can also run directly.", "Calls pandas CSV operations and joblib dump; exposes preprocess_data().", "Built-in: logging, pathlib, typing. Third-party: joblib, pandas, sklearn LabelEncoder.", "Validates CSV path, drops accidental Unnamed index columns, removes duplicates, fills missing numerical values with median/zero and categorical values with mode/Unknown, encodes text columns, saves results.", "Raw CleanStartups.csv", "Processed DataFrame, processed_startups.csv, label_encoders.pkl", "Uses PreprocessingError for bad path/CSV/empty data/output failures.", "preprocess.py makes historical raw data safe and numeric for model training while preserving encoders needed later at prediction time.")
    add_file(story, "train_model.py", "Trains, evaluates, and persists the Random Forest classifier.", "Run manually with python train_model.py after changing raw data.", "Calls preprocess_data() then scikit-learn split, fit, metric functions, and joblib/file saves.", "Built-in: json, logging, pathlib, typing. Third-party: joblib, pandas, sklearn ensemble/metrics/model_selection. Local: preprocess.", "Uses stratified 80/20 split and random_state 42. build_model() returns 300-tree, max-depth-15 forest. evaluate_model() calculates accuracy, weighted precision/recall/F1, ROC-AUC, confusion matrix, report; saves artifacts.", "Raw dataset via preprocessing", "Fitted model and model artifacts", "TrainingError wraps validation, split, training, metric, and persistence failures.", "train_model.py is the offline ML pipeline: it preprocesses data, trains a reproducible Random Forest, evaluates it on held-out data, and saves everything the API needs.")
    add_file(story, "dataset_preprocessing.py", "Reads report uploads and adapts flexible spreadsheets to the fixed model schema.", "Called by app.py upload/report routes.", "Calls column_mapping helpers and uses PredictionError from predict.py.", "Built-in: pathlib, BinaryIO. Third-party: pandas. Local: column_mapping, predict.", "read_startup_file() supports CSV/XLSX/XLS. validate_report_dataframe() requires a usable company header. get_company_list() preserves original row identities. filter_company_data() returns exactly selected row. adapt_for_model() maps names/fills missing fields.", "Upload stream or DataFrame", "Cleaned, selected, or model-aligned DataFrame", "Rejects unreadable/empty files, missing company field, invalid selection. Missing model fields are filled deliberately for prediction.", "This file separates user-friendly spreadsheet handling from strict ML feature requirements.")
    add_file(story, "column_mapping.py", "Recognizes semantically similar spreadsheet headers.", "Called by dataset_preprocessing, insight_generator, chart_generator, and pdf_generator.", "Only uses re and Iterable.", "Built-in: re, typing. No third-party imports.", "ALIASES defines canonical business concepts. normalize_column() lowercases/removes punctuation. find_column() tries exact then partial alias matches. map_columns() builds all found mappings.", "Column-name iterable + concept", "Actual column name or mapping dictionary", "Returns None when no match; callers handle absence.", "column_mapping.py lets reports understand headings like Company Name, Startup Name, Funding, or Total Funds without forcing one upload template.")
    add_file(story, "insight_generator.py", "Creates evidence-based report text and risk rows without an LLM.", "Called by pdf_generator.py for each selected company.", "Calls column-mapping functions and pandas numeric conversion.", "Third-party: pandas. Local: column_mapping.", "number()/value() extract data; report_metric_values() keeps verified numeric business fields; report_context() creates recommendation/reasons/summary; risk_sections() returns Financial, Operational, Commercial, Execution rows.", "One-row DataFrame + prediction dictionary", "Context dictionary, observations, and risk tuples", "Missing data leads to explicit disclosure-gap statements rather than invented values.", "insight_generator.py turns available uploaded metrics and model output into transparent, deterministic diligence language.")
    add_file(story, "chart_generator.py", "Produces PNG financial charts for the PDF.", "Called by generate_report().", "Calls find_column() and matplotlib/pandas.", "Built-in: pathlib. Third-party: matplotlib, pandas. Local: column_mapping.", "For revenue, funding, employees, growth, burn, runway, valuation it finds a column, parses a numeric value, draws one horizontal bar, saves image, closes figure.", "One-company DataFrame + output directory", "List of PNG paths", "Silently skips unavailable/non-numeric metrics; it does not fabricate a chart.", "chart_generator.py creates simple local visual evidence from metrics actually supplied in the selected row.")
    add_file(story, "pdf_generator.py", "Creates the polished selected-company PDF report.", "Called only by POST /reports/generate in app.py.", "Calls chart_generator, column_mapping, insight_generator; uses ReportLab and pandas.", "Built-in: datetime, pathlib, html, re, time. Third-party: pandas, ReportLab. Local: chart_generator, column_mapping, insight_generator.", "Defines visual styles/header/footer, safe display/table helpers, profile/industry/SWOT logic, then generate_report() builds cover, summary, context, tables, features, charts, KPIs, risks, and appendix.", "One selected row, prediction dict, saved metrics, output path", "Saved PDF path", "Requires exactly one record; optional feature-importance read failure is ignored; missing input metrics are disclosed.", "pdf_generator.py is the presentation layer: it turns the selected row and model result into a structured, locally generated due-diligence PDF.")
    add_file(story, "check_data.py", "Small development inspection utility.", "Only when a developer runs python check_data.py.", "Reads data/processed_startups.csv with pandas.", "Third-party: pandas.", "Prints Fate value counts and DataFrame data types.", "Processed CSV", "Terminal diagnostics", "No custom error handling; use only after preprocessing has produced the file.", "check_data.py is not part of the web app; it is a quick sanity check for processed labels and column types.")
    story += [PageBreak(), h("5.2 Frontend and configuration files", 2)]
    frontend_files = [
        ("frontend/src/main.jsx", "Browser entry point. createRoot mounts App in StrictMode.", "Vite loads it from index.html.", "React createRoot, App, index.css.", "Input: #root element. Output: mounted React tree."),
        ("frontend/src/App.jsx", "Router and app shell.", "Mounted by main.jsx.", "BrowserRouter/Routes, Navbar, Footer, Dashboard, About.", "Routes / to Dashboard and /about to About."),
        ("frontend/src/pages/Dashboard.jsx", "Main stateful screen.", "Rendered for / by App.jsx.", "React hooks; components; functions from services/api.js.", "Loads health/model/metrics; controls form, prediction, upload company list, selected row, PDF Blob URL, toast, and loading states."),
        ("frontend/src/pages/About.jsx", "Static product explanation page.", "Rendered for /about.", "Framer Motion only.", "Shows implementation claims: Random Forest, persisted artifacts, batch API concept."),
        ("frontend/src/services/api.js", "Single Axios API boundary.", "Imported by Dashboard.jsx.", "Axios and VITE_API_BASE_URL.", "Exports getDashboardData, predictStartup, predictCsv, generateDueDiligenceReport, getReportCompanies; maps server errors to readable Error messages."),
        ("frontend/src/components/UploadCard.jsx", "Spreadsheet file picker, drag/drop, selection UI, PDF action controls.", "Rendered by Dashboard.", "React useState and Lucide icons.", "Accepts callbacks/props. Client-side accepts csv/xlsx/xls; server performs authoritative validation."),
        ("frontend/src/components/PredictionCard.jsx", "Displays latest single prediction.", "Rendered by Dashboard.", "Framer Motion, ArrowUpRight icon.", "Uses prediction, probability, confidence, risk_level; has an empty-state card."),
        ("frontend/src/components/RiskGauge.jsx", "Circular confidence visualization.", "Rendered by Dashboard.", "No external data library.", "Uses a conic-gradient and colour chosen from risk_level."),
        ("frontend/src/components/Statistics.jsx", "Four summary cards.", "Rendered by Dashboard.", "Lucide icons.", "Derives training samples, accuracy, features, ROC-AUC from dashboard API state."),
        ("frontend/src/components/FeatureImportance.jsx", "Horizontal Recharts importance chart.", "Rendered by Dashboard.", "Recharts.", "Receives top importance records from /model-info."),
        ("frontend/src/components/Charts.jsx", "Model-metric and optional batch-distribution charts.", "Rendered by Dashboard.", "Recharts.", "Metric chart works. Batch chart needs batchResult, but Dashboard does not pass it in current implementation."),
        ("frontend/src/components/Hero.jsx, Navbar.jsx, Footer.jsx, Loading.jsx", "Reusable visual/status/navigation elements.", "Rendered by App or Dashboard.", "Framer Motion, React Router, Lucide where needed.", "They do not call backend APIs."),
        ("frontend/src/components/Sidebar.jsx", "Placeholder navigation component.", "Rendered by Dashboard.", "Lucide.", "Currently display:none, so it has no visible user role."),
        ("frontend/src/index.css and App.css", "Global, layout, glassmorphism, responsive styles.", "Imported from main.jsx/App.", "CSS only.", "No business logic."),
        ("frontend/package.json, vite.config.js, eslint.config.js, index.html", "Frontend dependency/build/lint/HTML configuration.", "Used by npm/Vite/ESLint rather than Flask.", "Vite React/Tailwind plugins and ESLint config.", "package.json scripts are dev, build, lint, preview."),
    ]
    for name, purpose, run, imports, logic in frontend_files:
        add_file(story, name, purpose, run, "See statement above; UI components generally call upward callbacks, while Dashboard calls api.js.", imports, logic, "Props, browser events, or route", "Rendered UI or API action", "API errors are shown in Dashboard toast; rendering uses optional chaining/empty states.", f"{name.split('/')[-1]} is part of the React presentation layer. It keeps the interface modular while Dashboard and api.js coordinate data and backend communication.")
    story += [PageBreak()]

    # Workflow
    story += [h("6. Project Workflow", 1), h("Selected-company PDF workflow", 2), ArchitectureDiagram([
        ("1. Open dashboard", "React fetches health, info, metrics", SKY),
        ("2. Upload spreadsheet", "UploadCard -> /reports/companies", MINT),
        ("3. Choose company", "explicit original row index", colors.HexColor("#EDE9FE")),
        ("4. Server reads/adapts", "CSV/XLS/XLSX + header aliases", AMBER),
        ("5. Model predicts", "encoded 24-feature Random Forest input", PINK),
        ("6. Generate/download", "rules + charts -> ReportLab PDF", MINT),
    ]),
    h("Step-by-step in plain English", 2)]
    for i, text in enumerate(["The Vite browser app starts and Dashboard calls /health, /model-info, and /metrics in parallel.", "The user uploads a spreadsheet. The browser sends the file as multipart FormData to /reports/companies.", "Flask reads CSV with pandas or Excel with pandas/openpyxl, removes fully empty rows/columns, and finds a company-name column through aliases.", "The browser shows company labels such as Company Name (Row 4). The user must select one; this prevents an accidental report for row one.", "The selected row and original upload are posted to /reports/generate.", "The backend maps input headers to model features, fills unavailable categorical features with Not Available and numeric features with 0, then runs prediction.", "The report module reads original company fields for business context, not the encoded values. It creates only charts/claims supported by uploaded values.", "Flask returns a PDF attachment. React turns it into a Blob URL for iframe preview and download."], 1):
        story.append(p(f"<b>{i}.</b> {text}"))
    story += [h("Single prediction workflow", 2), p("The form is pre-filled from /model-info sample_input. Clicking Analyze startup sends /predict. The response is rendered by PredictionCard and RiskGauge. This path does not make a PDF."), PageBreak()]

    # API
    story += [h("7. API Documentation", 1), table(["Endpoint", "Purpose", "Request", "Response"], [
        ["GET /", "API discovery.", "None", "Service/status/endpoint list."],
        ["GET /health", "Check server and artifacts.", "None", "healthy/unhealthy, model_loaded, backend_running; 503 if unavailable."],
        ["GET /model-info", "Supply UI schema/metadata.", "None", "Algorithm, feature names/count, sample input, feature importance, sample count."],
        ["GET /metrics", "Return held-out metrics.", "None", "accuracy, precision, recall, f1, roc_auc."],
        ["POST /predict", "Score one startup.", "JSON {data: {features}} or direct record.", "prediction, probability, confidence, risk_level."],
        ["POST /predict/csv", "Score all upload rows.", "FormData file (.csv/.xlsx/.xls).", "rows_predicted, results array. API exists but current UI does not wire it."],
        ["POST /reports/companies", "List selectable company rows.", "FormData file.", "companies [{row_index,name,label}], rows_available."],
        ["POST /reports/generate", "Create selected report.", "FormData file and row_index.", "application/pdf attachment."],
    ], [95, 120, 140, 115]), h("Request example", 2), p('{"data": {"Company": "Example AI", "YCYear": 2024, "... all returned features ...": "..."}}', "code"),
    callout("API contract rule", "For direct prediction, send all features returned by /model-info. The browser does this by starting from a server-provided complete sample record.", SKY), PageBreak()]

    # Front/backend
    story += [h("8. Frontend Guide", 1), p("React uses local state in Dashboard.jsx rather than Redux or Context. `data` holds API startup data, `form` stores editable model input, `prediction` holds the latest result, `companies/selectedRow` handle the report selection, and `reportUrl` is an in-memory browser Blob URL."),
              h("User interaction map", 2), table(["User action", "Component", "API / state effect"], [
                  ["Open app", "Dashboard", "getDashboardData() concurrently requests health, model info, metrics."],
                  ["Edit fields and analyze", "Dashboard + PredictionCard", "predictStartup(form) -> /predict -> setPrediction."],
                  ["Upload file", "UploadCard", "getReportCompanies(file) -> companies state."],
                  ["Choose company", "UploadCard", "onCompanyChange sets selectedRow."],
                  ["Generate PDF", "Dashboard", "generateDueDiligenceReport(file,row) -> Blob URL -> iframe."],
                  ["Download PDF", "Dashboard", "Temporary anchor uses Blob URL/file name."],
              ], [125, 135, 210]),
              h("9. Backend Guide", 1), p("Flask route functions remain deliberately thin. `app.py` validates HTTP-level requirements and delegates data/ML/report work. This separation makes prediction reusable outside HTTP and keeps PDF logic out of route functions."),
              table(["Module", "Business logic", "Validation / errors"], [
                  ["app.py", "Orchestration and response format.", "BadRequest/PredictionError/413 JSON responses."],
                  ["predict.py", "Artifact-compatible inference.", "Artifact presence/type/interface and prediction failures."],
                  ["dataset_preprocessing.py", "Upload reading/header adaptation/row selection.", "Empty files, company column, selected row."],
                  ["insight_generator.py", "Deterministic recommendation/risk content.", "Treats missing metrics as disclosure gaps."],
                  ["pdf_generator.py", "Document composition.", "Requires exactly one record; optional data displays safely."],
              ], [115, 205, 150]), PageBreak()]

    # AI / report
    story += [h("10. AI Module", 1), p("The model is `RandomForestClassifier(n_estimators=300, max_depth=15, random_state=42)`. Training uses 24 features and a target called Fate. Categorical columns are LabelEncoded, including the target. The decoder mapping saved in this repository is Dead=0, Exited=1, Operating=2."),
              h("Decision process", 2)]
    for t in ["A prediction request is aligned to features.pkl so column order matches training.", "Saved encoders transform categorical values. Known categories use the learned mapping; unseen values use 0 and log a warning.", "The forest outputs a predicted class and class probabilities. The maximum probability becomes Probability; multiplied by 100 it becomes Confidence.", "app.py maps outcome label to a presentational risk label. The PDF makes a separate rule-based recommendation from risk, confidence, funding, revenue, growth, and runway where supplied."]:
        story.append(bullet(t))
    story += [callout("Prompt flow", "None exists. Any answer claiming the report sends prompts to OpenAI would be inaccurate for this repository. The report is deterministic Python code.", AMBER), h("Limitations", 2)]
    for t in ["Raw class distribution is imbalanced: Operating 452, Dead 85, Exited 80.", "Saved held-out metrics show 77.4% accuracy and 0.887 weighted ROC-AUC, but the saved report has zero recall for Exited; accuracy alone is not enough.", "Text identifiers such as company name, profile URL, and logo encode into arbitrary numbers and may not generalize.", "Fallback encoding and zero-filled missing numeric inputs can reduce trustworthiness. Human diligence is required."]:
        story.append(bullet(t))
    story += [h("11. Report Generation", 1), p("`pdf_generator.generate_report()` receives the unencoded selected row, prediction dictionary, saved metrics dictionary, destination path, and source filename. It uses ReportLab flowables (Paragraph, Table, PageBreak, Image) and a page template for headers/footers."),
              table(["Report area", "Data source", "Meaning"], [
                  ["Executive summary", "report_context()", "Model confidence plus evidence/disclosure wording."],
                  ["Company overview", "Original upload via semantic mapping", "Industry, funding, valuation, team, revenue, city, year where available."],
                  ["Feature importance", "model/feature_importance.csv", "Top business-relevant model inputs; certain profile/identity-like names are filtered here."],
                  ["Financial analysis", "Original numeric upload values", "Matplotlib bars for available revenue/funding/growth/etc."],
                  ["Risk/SWOT/appendix", "Deterministic rules + column mapping", "Risk actions, missing data, completeness, method information."],
              ], [125, 155, 190]), PageBreak()]

    # data flow / errors / libraries
    story += [h("12. Data Flow Between Files", 1), p("Training: CleanStartups.csv -> preprocess.py -> processed_startups.csv and label_encoders.pkl -> train_model.py -> model artifacts. Runtime: Dashboard/api.js -> app.py -> dataset_preprocessing.py/predict.py -> prediction -> pdf_generator.py -> output/pdf -> browser."),
              h("13. Libraries Used", 1), table(["Library", "Purpose", "Primary files"], [
                  ["Flask / Flask-CORS", "REST API and CORS.", "app.py"], ["pandas", "Table IO, transformations, numeric parsing.", "Most Python modules"], ["scikit-learn", "Encoders, Random Forest, metrics/split.", "preprocess.py, train_model.py, predict.py"], ["joblib", "Artifact persistence.", "preprocess.py, train_model.py, predict.py"], ["ReportLab", "PDF layout.", "pdf_generator.py"], ["Matplotlib", "Chart PNGs.", "chart_generator.py"], ["Axios", "HTTP client/error handling.", "api.js"], ["Recharts", "Browser charts.", "Charts.jsx, FeatureImportance.jsx"], ["Framer Motion", "Animations.", "Hero/About/PredictionCard"], ["Lucide React", "Icons.", "Frontend components"]
              ], [115, 190, 165]), h("14. Common Errors and Debugging", 1), table(["Symptom", "Likely cause", "Debug / resolution"], [
                  ["/health is unhealthy", "Artifacts absent/corrupt.", "Run python train_model.py; read Flask log for PredictionError."],
                  ["Connection toast", "Flask down or wrong base URL.", "Start app.py, check port 5000, set VITE_API_BASE_URL."],
                  ["Company column error", "No mapped company header.", "Use Company Name/Company/Startup Name or extend ALIASES."],
                  ["Report lacks metrics", "Upload has no usable numeric fields.", "Include revenue/funding/burn/runway/growth; system intentionally avoids guessing."],
                  ["Excel read failure", "Bad workbook/dependency.", "Confirm file and openpyxl installation."],
                  ["Unexpected prediction", "Data/model limitations or fallback category.", "Inspect logs, input columns, feature order, encoders, class metrics."],
              ], [125, 145, 200]), PageBreak()]

    # future and handover
    story += [h("15. Future Scope", 1)]
    for x in ["Add automated tests for routes, data mapping, prediction schemas, and PDF content.", "Improve minority-class results with additional/cleaner data, class weighting/resampling, tuning, and per-class acceptance criteria.", "Remove or redesign identifier-like features such as URLs/logos/company names; add meaningful financial/market features.", "Add model/dataset versioning, training metadata, experiment tracking, calibrated confidence, and explainability checks.", "Secure production deployment: authenticated users, restricted CORS, debug off, rate limits, virus/file scanning, database/object storage, audit trails.", "Wire the existing batch prediction endpoint to Dashboard and the batch distribution chart.", "Add human-review workflow and explicit policy disclaimers."]:
        story.append(bullet(x))
    story += [h("16. Team Handover Guide", 1), h("First files to read", 2), p("1) app.py for public contract. 2) predict.py for inference. 3) preprocess.py and train_model.py for the model lifecycle. 4) dataset_preprocessing.py/column_mapping.py/insight_generator.py/pdf_generator.py for reports. 5) api.js then Dashboard.jsx for browser coordination."),
              h("Adding a feature", 2), p("First locate its layer. A new uploaded metric may require alias mapping, report extraction, PDF presentation, and tests. A new model feature requires data preparation, retraining, regenerated artifacts, backend schema confirmation, and frontend form confirmation. Avoid manually changing pickled files."),
              h("Debug sequence", 2), p("Check /health -> /model-info -> /metrics before the UI. Reproduce one request outside React if necessary. Then inspect Flask logs, browser network responses, selected input columns, and generated output/pdf files."), PageBreak()]

    # Viva 50
    story += [h("17. Frequently Asked Viva Questions", 1), p("The answers below are based on the implementation, including its limitations. They are intentionally direct enough to rehearse." )]
    qs = [
        ("What type of project is this?", "A full-stack machine-learning application: React frontend, Flask REST backend, scikit-learn classifier, spreadsheet processing, and ReportLab PDF generation."),
        ("What is the model target?", "The Fate column. Its saved label mapping is Dead=0, Exited=1, Operating=2."),
        ("Does it use OpenAI?", "No. The repository has no OpenAI dependency or API call. AI here is a Random Forest model."),
        ("Why use Random Forest?", "It handles nonlinear relationships, multiclass output, mixed encoded inputs, and gives feature importances/probabilities with a practical training workflow."),
        ("How many trees are trained?", "300 trees, with maximum depth 15 and random_state 42."),
        ("Why set random_state?", "It makes split and model behaviour reproducible across runs, as far as the library permits."),
        ("How is the dataset split?", "train_test_split uses 20% test data, 80% training data, and stratify=target."),
        ("Why stratify?", "The outcome classes are imbalanced, so stratification preserves their proportions in train and test sets."),
        ("What is LabelEncoder doing?", "It maps each categorical string to an integer. A separate fitted encoder is saved for each categorical column."),
        ("Why save encoders?", "Prediction must apply the same category-to-number mappings that training used."),
        ("What happens for unseen categories?", "Inference logs a warning and uses fallback encoding 0. It keeps the API available but is a modelling limitation."),
        ("Why is features.pkl needed?", "It preserves the exact expected feature names and order for classifier inference."),
        ("What does confidence mean?", "It is the maximum class probability from predict_proba multiplied by 100, not a guarantee of real-world success."),
        ("How does risk level work?", "app.py maps Operating to Low, Exited or Acquired to Medium, and all other labels to High."),
        ("Is risk a second trained model?", "No. It is a simple presentation rule over the outcome label."),
        ("How is report recommendation decided?", "Deterministic conditions use risk, confidence, growth, runway, funding, and revenue to choose Strong Buy, Buy, Hold, Watchlist, or Avoid."),
        ("Does the report invent missing facts?", "No. It detects missing metrics and writes disclosure-gap/verification statements instead."),
        ("Why keep original upload data for reports?", "Encoded values are only meaningful to the model. A human report needs original company names and actual business values."),
        ("Why require a selected row?", "To prevent silently reporting the first spreadsheet row when the user intended another company."),
        ("Which uploads are allowed?", "CSV, XLSX, and XLS, subject to a 10 MB Flask upload limit."),
        ("How are variable headers handled?", "Aliases and normalized exact/partial matching in column_mapping.py map common terms to canonical concepts."),
        ("What does Flask do?", "It receives HTTP requests, validates them, calls local modules, and returns JSON or a PDF file."),
        ("Why use CORS?", "During development Vite and Flask run on different origins/ports, so the browser needs permission for API calls."),
        ("What is the use of /health?", "It verifies both backend availability and that model artifacts can load, returning 503 if they cannot."),
        ("What is returned by /model-info?", "Model algorithm/name, features, feature count, sample input, importance records, target, and training sample count."),
        ("How does the dashboard avoid missing fields?", "It asks /model-info for a sample input and edits that complete record rather than starting with an unknown schema."),
        ("What does Axios add?", "A central base URL, timeout, request helpers, multipart handling, and consistent error-message extraction."),
        ("How does PDF preview work?", "The response is a blob; Dashboard creates a browser object URL and uses it as an iframe source."),
        ("Why revoke Blob URLs?", "To reduce browser memory leakage when a new report replaces an old report or the component unmounts."),
        ("Which library makes the PDF?", "ReportLab. Matplotlib separately makes chart PNG files embedded in the document."),
        ("What chart data is used?", "Available selected-row values for revenue, funding, employees, growth, burn rate, runway, or valuation."),
        ("How are model metrics computed?", "On held-out test data: accuracy, weighted precision/recall/F1, ROC-AUC, confusion matrix, classification report."),
        ("Why weighted metrics?", "They account for each class while weighting contributions by support, which matters with imbalanced class counts."),
        ("What limitation does the current report show?", "Saved metrics show zero recall for the encoded Exited class, despite 77.4% overall accuracy; minority-class performance needs work."),
        ("Why is accuracy insufficient?", "The Operating class dominates, so a model may look accurate while missing smaller but important outcomes."),
        ("What is check_data.py for?", "A manual utility that prints processed Fate counts and dtypes; it is not used by the web application."),
        ("What is frontend/dist?", "The generated production build from Vite. It should be rebuilt, not edited directly."),
        ("Is Tailwind actively responsible for all styling?", "It is installed/configured, but the visible project styles are primarily custom CSS in index.css and App.css."),
        ("Why is Sidebar not visible?", "Sidebar.jsx renders with inline display:none, so it is currently a placeholder."),
        ("Is batch prediction complete in the UI?", "The API and api.js function exist, but Dashboard does not call predictCsv or pass batchResult to Charts, so the batch distribution is not active."),
        ("What error type represents domain failures?", "PredictionError, a ValueError subclass used for artifacts, uploads, and prediction problems."),
        ("How does Flask return invalid requests?", "BadRequest is handled as JSON 400, not a default HTML error page."),
        ("How are missing numeric values handled in training?", "They are filled with the column median, or zero if the entire numeric column is missing."),
        ("How are missing categorical values handled in training?", "They are filled with the mode, or Unknown if there is no mode."),
        ("How does report adaptation fill absent features?", "Categorical model features receive Not Available; numeric features receive 0, allowing an imperfect but complete inference record."),
        ("What security improvements are needed?", "Restrict CORS, disable debug in production, authenticate users, scan uploads, limit/rate-limit requests, and store reports safely."),
        ("How would you improve model validity?", "Audit leakage/identifier features, collect better balanced data, test models, tune/calibrate, and set per-class performance goals."),
        ("What happens after raw data changes?", "Run train_model.py to regenerate processed data, encoders, model, metrics, features, and importance before serving predictions."),
        ("What must a new developer read first?", "app.py for contract, predict.py for inference, training/preprocessing for lifecycle, then api.js/Dashboard for frontend orchestration."),
        ("What is the most important ethical warning?", "The tool is decision support. It should not replace verification or professional investment, legal, financial, security, or tax due diligence."),
    ]
    for i, (q, a) in enumerate(qs, 1):
        story += [p(f"<b>{i}. {q}</b>", "h3"), p(a)]
    story += [PageBreak()]

    # quick revision
    story += [h("18. Quick Revision", 1), callout("One-minute summary", "VentureSignal is a React + Flask project that trains a 300-tree Random Forest on historical startup records. Flask loads saved model artifacts to predict Dead, Exited, or Operating. Users can submit a single form or upload a spreadsheet and select a company for a deterministic ReportLab PDF.", MINT),
              h("Five-page revision checklist", 2)]
    checklist = [
        ("Page A - Architecture", "React calls Flask via Axios. Flask calls prediction/report modules. Training creates artifacts under model/."),
        ("Page B - ML", "preprocess.py cleans/fills/encodes. train_model.py stratifies 80/20, trains 300-tree RF, calculates metrics, saves artifacts."),
        ("Page C - Prediction", "predict.py loads artifacts, aligns feature order, encodes text, predicts class/probability, decodes Fate. app.py maps risk."),
        ("Page D - Report", "Upload -> company list -> selected row -> header mapping -> prediction -> deterministic insights/charts -> ReportLab PDF -> browser Blob preview."),
        ("Page E - Caution", "No OpenAI/LLM. Imbalanced classes and identifier-like encoded features are limitations. Report is decision support and requires human verification."),
    ]
    for title, text in checklist:
        story += [h(title, 2), p(text)]
    story += [h("Final team checklist", 2)]
    for x in ["Run training before first backend start or after dataset changes.", "Verify /health before debugging the frontend.", "Keep frontend API base URL aligned with Flask port.", "Never hand-edit model pickle files or frontend dist bundles.", "Update README and this training manual when endpoint/data-flow behaviour changes."]:
        story.append(bullet(x))
    story += [Spacer(1, 14), callout("End of manual", "This training manual reflects the repository as inspected on 07 August 2026. Use it alongside the code and test data when making production decisions.", SKY)]
    doc.multiBuild(story)


if __name__ == "__main__":
    build()
    print(OUT)
