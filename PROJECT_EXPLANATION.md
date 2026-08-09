# AI Startup Due Diligence Platform — Project Documentation

> **Purpose of this document:** a technical and team-handover guide based on the current implementation in this repository. It distinguishes implemented behaviour from planned or unused code paths.

## 1. Project Overview

### Project title

**AI Startup Due Diligence Platform** (branded in the frontend as **VentureSignal**).

### Problem statement

Evaluating many startups is time-consuming and often inconsistent. Investors or analysts need a repeatable way to inspect structured startup information, estimate an outcome class, identify high-level risks, and produce a readable due-diligence report.

### Why this project was built

The project combines a machine-learning classifier with a web dashboard. It lets a user either submit one startup record for a prediction or upload a spreadsheet, choose one company, and generate a PDF due-diligence report.

### Objectives

- Train a supervised classifier on historical startup records.
- Predict one of three historical outcome labels: `Operating`, `Exited`, or `Dead`.
- Return prediction probability, confidence, and a presentation-level risk label.
- Accept CSV, XLSX, and XLS uploads for report generation.
- Adapt common business-column names such as `Company Name`, `Startup Name`, or `Funding`.
- Generate a professional PDF containing company context, financial charts, risk sections, SWOT, and data-quality notes.
- Provide a React interface for model status, metrics, model inputs, and report download.

### Real-world use case

An analyst uploads a startup portfolio spreadsheet. The application lists the companies in it, the analyst selects one company, and the server predicts its historical-outcome class and builds a PDF. The PDF is a **screening aid**, not an investment decision system: it explicitly says that missing information should be independently verified.

## 2. Project Architecture

### Architecture diagram

```text
                         Training workflow
data/CleanStartups.csv ──> preprocess.py ──> train_model.py
                              │                 │
                              │                 └─> model/risk_model.pkl
                              │                     model/features.pkl
                              └─> data/processed_startups.csv
                                                    model/label_encoders.pkl
                                                    model/metrics.json
                                                    model/feature_importance.csv

                         Runtime workflow
Browser
  │
  ▼
React + Vite frontend (frontend/src)
  │ Axios / multipart FormData / JSON
  ▼
Flask API (app.py) ─────> predict.py ─────> saved model artifacts
  │                            │
  │                            └─> prediction + probability + confidence
  │
  ├─> dataset_preprocessing.py ─> column_mapping.py
  │
  └─> pdf_generator.py ─> insight_generator.py + chart_generator.py
                               │                       │
                               └──────────────> PDF + PNG chart assets
                                                    in output/pdf/
```

### Component responsibilities

| Layer | Implemented technology | Responsibility |
|---|---|---|
| Frontend | React 19, Vite, Axios | User interface, routing, uploads, request handling, PDF preview/download. |
| Backend | Flask, Flask-CORS | Defines HTTP routes, validates requests, calls prediction/report functions, returns JSON or a PDF file. |
| ML | scikit-learn RandomForestClassifier | Learns a multiclass outcome classifier from the processed startup dataset. |
| Data | pandas | Reads, cleans, transforms, maps, and exports tabular data. |
| Report engine | ReportLab + Matplotlib | Builds the multi-section PDF and locally generated chart images. |

### Important accuracy note

There is **no OpenAI API, LLM, prompt, token, or generative-AI call** in the repository. “AI” means the trained Random Forest classifier and deterministic, evidence-based report rules in `insight_generator.py`.

## 3. Technology Stack

| Technology | Why it was chosen | Where used |
|---|---|---|
| React | Component-based interactive dashboard. | `frontend/src/` |
| Vite | Fast React development server and production bundler. | `frontend/vite.config.js`, npm scripts |
| Python | Suitable for ML, data processing, Flask, and report generation. | Root `*.py` files |
| Flask | Lightweight REST backend with simple route decorators. | `app.py` |
| Flask-CORS | Lets the Vite frontend on a different local port call Flask. | `app.py` |
| pandas | Reads CSV/Excel files and manipulates DataFrames. | Data, prediction, reports |
| scikit-learn | Label encoding, data split, Random Forest, metrics. | `preprocess.py`, `train_model.py`, `predict.py` |
| joblib | Saves/loads the trained model, feature list, and encoders. | Training and prediction modules |
| ReportLab | Programmatic, paginated PDF layout. | `pdf_generator.py` |
| Matplotlib | Creates static PNG financial charts embedded in the PDF. | `chart_generator.py` |
| openpyxl | Enables pandas to read `.xlsx` Excel uploads. | Indirectly used by `read_startup_file()` |
| Axios | HTTP client with a shared base URL and error translation. | `frontend/src/services/api.js` |
| React Router | Dashboard and About page routes. | `frontend/src/App.jsx` |
| Recharts | Displays model metrics and feature-importance bar charts. | `Charts.jsx`, `FeatureImportance.jsx` |
| Framer Motion | Small entrance/result animations. | `Hero.jsx`, `About.jsx`, `PredictionCard.jsx` |
| Lucide React | UI icons. | Several frontend components |
| Tailwind/Vite plugin | Configured as a dependency/plugin; the visible project styling is chiefly custom CSS in `index.css` and `App.css`. | `package.json`, `vite.config.js` |

## 4. Folder Structure

```text
AI-Startup-Due-Diligence/
├── app.py
├── predict.py
├── preprocess.py
├── train_model.py
├── dataset_preprocessing.py
├── column_mapping.py
├── insight_generator.py
├── chart_generator.py
├── pdf_generator.py
├── check_data.py
├── requirements.txt
├── README.md
├── PROJECT_EXPLANATION.md
├── data/
│   ├── CleanStartups.csv
│   └── processed_startups.csv
├── model/
│   ├── risk_model.pkl
│   ├── features.pkl
│   ├── label_encoders.pkl
│   ├── metrics.json
│   └── feature_importance.csv
├── output/
│   └── pdf/                         # runtime-generated reports/charts
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── eslint.config.js
│   ├── index.html
│   ├── .gitignore
│   ├── README.md
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── App.css
│   │   ├── assets/                   # hero.png and starter SVG assets
│   │   ├── services/api.js
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   └── About.jsx
│   │   └── components/
│   │       ├── UploadCard.jsx
│   │       ├── PredictionCard.jsx
│   │       ├── RiskGauge.jsx
│   │       ├── Statistics.jsx
│   │       ├── FeatureImportance.jsx
│   │       ├── Charts.jsx
│   │       ├── Hero.jsx
│   │       ├── Navbar.jsx
│   │       ├── Footer.jsx
│   │       ├── Loading.jsx
│   │       └── Sidebar.jsx
│   └── dist/                         # generated production frontend build
└── .git/, .agents/, __pycache__/, tmp/ # repository/tool/cache folders
```

`data/` holds input and processed datasets. `model/` holds persisted outputs of training. `output/` is written at runtime. `frontend/dist/` is generated by `npm run build`; its hashed CSS/JS should not be hand-edited. Tool/cache directories are not application source.

## 5. File-by-File Explanation

### Backend, ML, and report files

| File | Purpose and major functions | Inputs → outputs | Called by / calls |
|---|---|---|---|
| `app.py` | Flask entry point. `create_app()` registers routes; helpers validate extensions/rows, calculate risk labels, and load metadata. | JSON or uploaded files → JSON responses or downloaded PDF. | Run directly with `python app.py`; calls dataset, prediction, and PDF modules. |
| `predict.py` | Inference pipeline. `load_prediction_artifacts()`, `validate_uploaded_dataframe()`, `preprocess_input()`, `predict_dataframe()`. | DataFrame → original rows plus `Prediction`, `Probability`, `Confidence`. | Called by `app.py`; loads `model/*.pkl`. |
| `preprocess.py` | Training-data cleanup. Validates CSV, removes duplicates, fills missing values, label-encodes categories, saves processed data/encoders. | Raw CSV → processed DataFrame/CSV + encoder pickle. | Called by `train_model.py`; can run directly. |
| `train_model.py` | Supervised training. Validates data, splits stratified train/test sets, builds/evaluates/saves a Random Forest. | Processed dataset → trained model and evaluation artifacts. | Run with `python train_model.py`; calls `preprocess.py`. |
| `dataset_preprocessing.py` | Report-upload support. Reads CSV/XLS/XLSX, checks company names, returns selectable companies, maps upload columns to model features. | Upload stream/DataFrame → cleaned, selected, or adapted DataFrame. | Called by `app.py`; calls `column_mapping.py`. |
| `column_mapping.py` | Semantic header matching through `ALIASES`, `normalize_column()`, `find_column()`, `map_columns()`. | Column names → canonical-to-real-column mapping. | Called by dataset, insight, chart, and PDF modules. |
| `insight_generator.py` | Deterministic report interpretation. Extracts numeric metrics, identifies missing disclosures, creates recommendation, reasons, and risk sections. | Single-company DataFrame + prediction → context dictionary/tables. | Called by `pdf_generator.py`. |
| `chart_generator.py` | Creates one horizontal bar PNG per available business metric. | One-row DataFrame → `Path` list for PNGs. | Called by `pdf_generator.py`. |
| `pdf_generator.py` | PDF presentation layer. Creates styles, tables, profile, SWOT, data quality appendix, and embeds charts. | One company + prediction + metrics → saved PDF path. | Called by `app.py`; calls chart, insight, and mapping modules. |
| `check_data.py` | Small developer utility printing outcome counts and column data types from processed data. | `processed_startups.csv` → terminal output. | Only run manually. |

### Frontend files

| File | Purpose and interaction |
|---|---|
| `frontend/src/main.jsx` | Browser entry point. Mounts `<App />` into `#root` inside React `StrictMode`. |
| `frontend/src/App.jsx` | Creates router/layout. `/` renders `Dashboard`; `/about` renders `About`; Navbar and Footer wrap both. |
| `frontend/src/pages/Dashboard.jsx` | Main stateful screen. Fetches health/model/metrics, sends single prediction, uploads a file, selects a company, generates/previews/downloads PDF. |
| `frontend/src/pages/About.jsx` | Static project description with motion effects. |
| `frontend/src/services/api.js` | Shared Axios client and all frontend API functions. Uses `VITE_API_BASE_URL` or local Flask default. |
| `components/UploadCard.jsx` | Drag/drop or file-picker UI, company search/select, generate/download controls. |
| `components/PredictionCard.jsx` | Shows one prediction, probability, confidence, and risk badge. |
| `components/RiskGauge.jsx` | Converts confidence into a circular CSS conic-gradient gauge. |
| `components/Statistics.jsx` | Shows training samples, accuracy, feature count, and ROC-AUC. |
| `components/FeatureImportance.jsx` | Recharts horizontal bar chart of server-provided importance records. |
| `components/Charts.jsx` | Shows metric chart. It also contains a batch distribution chart, but `Dashboard.jsx` does not currently pass `batchResult`; therefore that chart is empty in the present UI. |
| `components/Hero.jsx`, `Navbar.jsx`, `Footer.jsx`, `Loading.jsx` | Presentation/status/navigation components. |
| `components/Sidebar.jsx` | Present but intentionally hidden using `display: 'none'`; it has no active UI role. |
| `index.css`, `App.css` | Global/theme/layout styling. |

### Configuration, assets, and persisted artifacts

| Path | Role |
|---|---|
| `requirements.txt` | Python dependency/version ranges. |
| `frontend/package.json` | JavaScript scripts and runtime/development dependencies. |
| `frontend/package-lock.json` | Locked npm dependency tree for reproducible installs. |
| `frontend/vite.config.js` | Enables React and Tailwind Vite plugins. |
| `frontend/eslint.config.js` | Lint rules for React/JavaScript. |
| `frontend/index.html` | Minimal Vite HTML shell containing the React root. |
| `frontend/public/*.svg` | Static favicon/icon assets copied into the frontend build. |
| `frontend/src/assets/*` | Image/starter assets; `hero.png` exists but is not imported by the present components. |
| `data/CleanStartups.csv` | Raw historical dataset: 617 rows and 25 columns, including target `Fate`. |
| `data/processed_startups.csv` | Cleaned/encoded training output: 617 rows and 24 columns. `Fate` is numeric. |
| `model/risk_model.pkl` | Joblib-serialized trained Random Forest. |
| `model/features.pkl` | Ordered list of the 24 input feature names. The order must match training. |
| `model/label_encoders.pkl` | Training-time LabelEncoders, including the target mapping `Dead=0`, `Exited=1`, `Operating=2`. |
| `model/metrics.json` | Persisted held-out metrics and detailed classification report. |
| `model/feature_importance.csv` | Random Forest feature importances, sorted descending. |

## 6. Complete Data Flow

### A. Training flow

1. `python train_model.py` starts `train_model()`.
2. It calls `preprocess_data()` in `preprocess.py` with the required target column `Fate`.
3. `load_data()` reads `data/CleanStartups.csv`, removes CSV index columns named like `Unnamed: ...`, and checks validity.
4. `remove_duplicates()` removes duplicated/all-empty rows.
5. `handle_missing_values()` fills numerical nulls with a median (or zero) and text nulls with mode (or `Unknown`).
6. `encode_categorical_columns()` fits one `LabelEncoder` per text/category column, including `Fate`.
7. Preprocessing saves `data/processed_startups.csv` and `model/label_encoders.pkl`.
8. Training validates that `Fate` exists, contains at least two classes, and every class has at least two examples.
9. `train_test_split()` uses an 80/20 stratified split with `random_state=42`.
10. A Random Forest with 300 trees and max depth 15 is trained.
11. The test subset is evaluated, then the model, ordered features, metrics, and feature importances are saved under `model/`.

### B. Single-startup prediction flow

1. `Dashboard.jsx` loads `/model-info`; the backend returns saved feature names plus a sample record from `CleanStartups.csv`.
2. The user edits the form and clicks **Analyze startup**.
3. `api.js` sends `POST /predict` with `{ "data": { ...features } }`.
4. `app.py` creates a one-row pandas DataFrame and calls `predict_dataframe()`.
5. `predict.py` loads saved artifacts, keeps the required feature order, encodes text using saved encoders, and uses fallback `0` for an unseen category.
6. The Random Forest returns a class and per-class probabilities. The greatest probability becomes `Probability`; multiplied by 100 it becomes `Confidence`.
7. The target encoder converts numeric class back to `Dead`, `Exited`, or `Operating`.
8. `app.py` maps the class to UI risk: `Operating → Low`, `Exited/Acquired → Medium`, everything else → High.
9. React displays `PredictionCard` and `RiskGauge`.

### C. PDF report flow

1. The user chooses CSV/XLS/XLSX in `UploadCard`.
2. The frontend calls `POST /reports/companies` with multipart `FormData`.
3. `read_startup_file()` reads the upload, strips blank rows/columns, and `get_company_list()` validates/matches a company-name header.
4. User selects an explicit row. The frontend sends the **same file** and `row_index` to `POST /reports/generate`.
5. `filter_company_data()` returns exactly that one row; it never silently uses the first record.
6. `adapt_for_model()` maps available upload headers to the model’s expected feature names. Missing categorical model features become `Not Available`; missing numerical ones become `0`.
7. The normal Random Forest prediction flow runs.
8. `generate_report()` combines the original selected row, prediction, saved model metrics, deterministic insights, and generated chart images.
9. Flask returns the resulting PDF as an attachment. React creates a Blob URL, previews it in an `<iframe>`, and enables download.

## 7. API Documentation

All endpoints are defined in `app.py`. The default base URL is `http://127.0.0.1:5000`.

| Method and URL | Request | Success response | Purpose |
|---|---|---|---|
| `GET /` | None | Service name, status, endpoint list. | Simple API discovery. |
| `GET /health` | None | `{status, model_loaded, backend_running}`; `503` if artifacts unavailable. | Checks backend and model artifact readiness. |
| `GET /model-info` | None | Model name/algorithm, feature count/list, sample input, feature importance, training sample count. | Populates frontend form and dashboard. |
| `GET /metrics` | None | `{accuracy, precision, recall, f1, roc_auc}`. | Supplies model performance chart/cards. |
| `POST /predict` | JSON record, either `{data: {...}}` or `{...}`. | `{prediction, probability, confidence, risk_level}`. | Scores one startup. |
| `POST /predict/csv` | `multipart/form-data` field `file`; supports CSV/XLSX/XLS. | `{rows_predicted, results: [...]}`. | Scores every uploaded row; exposed by API but not wired into current dashboard. |
| `POST /reports/companies` | `multipart/form-data` field `file`. | `{companies: [{row_index,name,label}], rows_available}`. | Provides the company chooser for report generation. |
| `POST /reports/generate` | `multipart/form-data`: `file`, `row_index`. | `application/pdf` attachment. | Generates one selected-company report. |

### Example: single prediction

```json
POST /predict
{
  "data": {
    "Company": "Example AI",
    "YCYear": 2024
  }
}
```

In practice, send **all 24 features** returned by `/model-info`. The frontend starts with a complete sample record to avoid missing feature values.

### Errors

- `400`: malformed JSON, invalid input, invalid spreadsheet, missing selected company, model/prediction validation failure.
- `413`: upload larger than 10 MB.
- `503`: health check could not load the saved artifacts.

## 8. AI Module

### How AI is used

The ML component is a supervised multiclass **Random Forest Classifier**, implemented in `train_model.py`. It learns from 617 historical records. The raw target distribution is `Operating: 452`, `Dead: 85`, `Exited: 80`, so it is imbalanced and accuracy must not be viewed alone.

### Input and output

- **Input:** 24 model features, including company/profile strings, YC year/session, funding, investor/founder, and market fields.
- **Output:** predicted target label; highest class probability; percentage confidence.
- **Decoded labels:** `Dead`, `Exited`, `Operating`.

### Decision process

1. Train-time label encoders turn text columns into numeric values.
2. The forest trains 300 decision trees; each tree makes a class vote.
3. The winning class is the aggregate prediction.
4. `predict_proba()` gives class probabilities; the largest one becomes displayed confidence.
5. `app.py` applies a simple presentation mapping to Low/Medium/High risk.
6. `insight_generator.py` applies deterministic rules to business metrics for the PDF recommendation, such as runway under 12 months, burn greater than revenue, and growth over 20%.

### Prompt flow

**Not applicable.** No LLM, OpenAI client, prompt template, or generative text request exists in this codebase. Report narrative is created through Python f-strings and conditional logic.

### Existing evaluation results

`model/metrics.json` reports held-out test performance: accuracy `77.4%`, weighted precision `67.3%`, weighted recall `77.4%`, weighted F1 `71.9%`, and weighted one-vs-rest ROC-AUC `0.887`. The report also shows zero recall for the encoded `Exited` class in this saved evaluation, which is an important limitation to mention honestly.

### Limitations

- Historical labels and data quality limit prediction quality.
- The classes are imbalanced; high overall accuracy can favour `Operating`.
- Label encoding arbitrary text (company names, URLs, descriptions) can encode identifiers rather than meaningful generalizable signals.
- Unseen categories are encoded as `0`, a fallback that may not represent their true meaning.
- The PDF recommendation is a rule-based screening output, not expert financial, legal, security, or investment advice.
- The frontend calls model confidence “probability”; it is a model score, not a guaranteed real-world probability.

## 9. Report Generation

### File and process

`pdf_generator.py` implements `generate_report(frame, prediction, metrics, output_path, dataset_name)`. It requires exactly one company row, creates output folders, builds a ReportLab story, and writes the finished PDF.

### Report sections

| Section | Source of content |
|---|---|
| Cover | Company name, industry/city/year where available, current date. |
| Executive Summary | `insight_generator.report_context()` and model confidence. |
| Overall Risk / Recommendation / Meters | `prediction` dictionary and deterministic recommendation. |
| Company Profile and Overview | Semantic column lookups from original uploaded row. |
| AI Assessment | Predicted label and confidence. |
| Influential Model Features | Top relevant entries from `model/feature_importance.csv`; URL/profile/identity-like columns are filtered for this report section. |
| Financial Analysis | PNG charts made by `chart_generator.create_charts()`. |
| KPI Dashboard | Available reported metrics such as ARR, MRR, CAC, LTV, EBITDA, churn. |
| Information Gaps | `disclosure_observations()` identifies absent disclosures. |
| Risk Analysis and SWOT | `risk_sections()` plus `_swot()` deterministic rules. |
| Appendix | Column mapping, missing fields/cells, completeness score, model accuracy, timestamp, processing time. |

The report never invents a financial value. If a metric is absent, the code uses missing-data language and recommends verification.

## 10. Frontend Explanation

### State management and interactions

`Dashboard.jsx` uses React local state, not Redux/Context:

| State | Meaning |
|---|---|
| `data` | Health, model info, and metrics fetched at load. |
| `form` | Editable values for the single-prediction model form. |
| `prediction` | Latest response from `/predict`. |
| `companies`, `selectedRow` | Company choices and selected spreadsheet row for a PDF. |
| `reportUrl`, `reportName` | Browser Blob URL and server filename for report preview/download. |
| `loading`, `predicting` | Initial/dashboard and action progress indicators. |
| `toast` | Temporary success/error message. |

On startup, `useEffect()` calls `load()`, which uses `getDashboardData()` to make `/health`, `/model-info`, and `/metrics` requests in parallel. It also revokes a prior Blob URL during cleanup to avoid memory leakage.

The report UI is intentionally separate from the single-prediction form: report generation uses an uploaded record and must have a selected company row.

## 11. Backend Explanation

### Validation and business logic

- `app.py` sets `MAX_CONTENT_LENGTH` to 10 MB and allows only CSV/XLSX/XLS filenames.
- Flask’s `BadRequest` handler returns JSON instead of HTML errors.
- `PredictionError` is the project-specific exception used for invalid artifacts/input/prediction conditions.
- Model artefacts are checked for existence, type shape, and required model methods before prediction.
- Report requests must name a valid company column and explicitly provide a valid row index.
- Upload headers are matched with aliases, allowing common business spreadsheet variations.

### Error handling

User-safe messages are returned for invalid JSON, missing files, unsupported extensions, bad spreadsheets, invalid row selections, artifact problems, and file size. The code does not currently define a generic unexpected-`Exception` 500 JSON handler, authentication, rate limiting, or persistent request logging.

### Integration boundaries

The backend does not call external AI services. Its only outputs are JSON responses and files created locally under `output/pdf/`.

## 12. Important Functions

| Function | File | Purpose | Parameters | Return value |
|---|---|---|---|---|
| `create_app` | `app.py` | Builds Flask app/routes/error handlers. | None | `Flask` app |
| `get_risk_level` | `app.py` | Converts outcome label to UI risk. | prediction string | `Low`, `Medium`, or `High` |
| `load_prediction_artifacts` | `predict.py` | Loads/validates model, feature order, encoders. | None | model, feature list, encoder dict |
| `preprocess_input` | `predict.py` | Encodes categorical inference inputs. | DataFrame, encoders | encoded DataFrame |
| `predict_dataframe` | `predict.py` | Runs full inference and appends outputs. | DataFrame | result DataFrame |
| `preprocess_data` | `preprocess.py` | Cleans and optionally encodes training CSV. | paths, training flag, required columns | DataFrame, encoder dict |
| `train_model` | `train_model.py` | Executes preprocessing, fitting, evaluation, persistence. | None | fitted model, metrics |
| `evaluate_model` | `train_model.py` | Calculates held-out classification metrics. | model, X test, y test | metrics dict |
| `read_startup_file` | `dataset_preprocessing.py` | Reads CSV/XLS/XLSX upload. | file stream, name | DataFrame |
| `adapt_for_model` | `dataset_preprocessing.py` | Adapts flexible headers to fixed model schema. | DataFrame, features, encoders | model-input DataFrame |
| `find_column` | `column_mapping.py` | Finds real input column for canonical concept. | columns, concept | matching name or `None` |
| `report_context` | `insight_generator.py` | Produces recommendation, reasons, summary, metrics. | DataFrame, prediction dict | context dict |
| `risk_sections` | `insight_generator.py` | Creates risk-table rows. | context dict | list of tuples |
| `create_charts` | `chart_generator.py` | Makes financial metric chart images. | DataFrame, output directory | list of image paths |
| `generate_report` | `pdf_generator.py` | Builds a selected-company PDF. | frame, prediction, metrics, output path, dataset name | PDF `Path` |
| `getDashboardData` | `frontend/src/services/api.js` | Fetches dashboard startup data concurrently. | None | health/model/metrics object |
| `generateDueDiligenceReport` | `frontend/src/services/api.js` | Uploads file + row and requests PDF blob. | file, row index | Axios response |

## 13. External Libraries

Python libraries are pinned in `requirements.txt`: Flask, Flask-Cors, joblib, pandas, scikit-learn, openpyxl, matplotlib, and reportlab. JavaScript libraries and versions are in `frontend/package.json`; key runtime libraries are React, React DOM, React Router, Axios, Recharts, Framer Motion, Lucide React, Tailwind CSS, and the Tailwind Vite plugin. ESLint/Vite/React-plugin packages are development tooling.

## 14. Project Workflow

```text
Install Python requirements + npm dependencies
        ↓
Run train_model.py when data/model needs rebuilding
        ↓
Start Flask: python app.py
        ↓
Start Vite: npm run dev (inside frontend/)
        ↓
Open browser dashboard
        ↓
Dashboard loads health, model information, and metrics
        ↓
Choose: single prediction OR spreadsheet-to-PDF workflow
        ↓
Flask validates, predicts, optionally generates report
        ↓
React displays prediction / previews and downloads PDF
```

## 15. Error Handling

| Area | Implemented behaviour |
|---|---|
| Raw training CSV | Validates file extension/path, empty data, missing required target; removes duplicate and blank rows. |
| Missing values | Numeric median/zero; categorical mode/`Unknown` at training time. |
| Model artifacts | Checks that all pickle files exist and expected interfaces/types are present. |
| Unseen inference categories | Logs a warning and encodes to `0` instead of failing the whole request. |
| Upload files | Checks presence, extension, readability, and 10 MB Flask limit. |
| Report selection | Requires company column, usable company name, and explicit valid row index. |
| API client | Axios converts server error JSON or network error into an `Error` shown as a toast. |
| PDF generation | Ignores unreadable/malformed optional feature-importance file rather than failing the full report. |

## 16. Future Improvements

- Add unit/integration tests for prediction routes, header matching, and PDF output.
- Fix class imbalance using class weights, resampling, more data, and per-class evaluation targets.
- Remove non-generalizable identity/profile fields (company name, URLs, logos) or replace them with meaningful engineered features.
- Validate numerical business values/ranges and prevent misleading fallback values.
- Add model version, dataset version, training timestamp, and reproducible experiment tracking.
- Add authentication, authorization, audit logs, and secure upload storage before production use.
- Add a database for reports/history rather than storing files locally.
- Wire `predictCsv()` and `Charts` batch distribution into the dashboard, or remove dead UI/API paths.
- Add SHAP or another explainability method with careful validation.
- Deploy with environment-specific CORS, `debug=False`, containerization, CI/CD, and a production WSGI server.
- Add an explicit disclaimer/consent flow and improve report provenance.

## 17. Frequently Asked Viva Questions

1. **What problem does the project solve?**  It provides consistent first-pass startup screening: model outcome prediction plus a structured report generated from uploaded data.
2. **Is this an OpenAI or chatbot project?**  No. The AI component is a scikit-learn Random Forest. There is no OpenAI API or prompt flow in the code.
3. **Why use Random Forest?**  It is an ensemble of decision trees, handles nonlinear relationships, supports multiclass classification, returns feature importances/probabilities, and needs less feature scaling than many alternatives.
4. **What does the target column represent?**  `Fate`, encoded from `Dead`, `Exited`, and `Operating` during training.
5. **How is text data made usable for the model?**  `LabelEncoder` turns each categorical string into an integer and saves the encoder so inference uses the same mappings.
6. **Why save encoders?**  Training and inference must represent the same category identically; otherwise the model receives incompatible numbers.
7. **What happens with an unseen category?**  `predict.py` logs a warning and assigns fallback integer `0`. This is resilient but a known limitation.
8. **Why save `features.pkl`?**  Models depend on exact feature schema/order. It ensures inference columns are aligned with training.
9. **How is data split?**  80% train and 20% test, stratified by outcome class, with random seed 42 for repeatability.
10. **Why stratify?**  It preserves approximate class proportions in both training and test data.
11. **What do accuracy and F1 mean?**  Accuracy is total correct predictions; weighted F1 balances precision/recall across classes while weighting each by support.
12. **Why is accuracy alone insufficient here?**  `Operating` is much more common. A model can get high accuracy while poorly predicting minority outcomes.
13. **What limitation appears in saved metrics?**  The saved classification report gives zero recall for encoded class `1` (`Exited`), so that class needs improvement.
14. **What is prediction probability?**  The maximum `predict_proba()` probability across output classes. It is model confidence, not a guarantee.
15. **How is risk level decided?**  The app maps `Operating` to Low, `Exited`/`Acquired` to Medium, otherwise High. It is a display rule, not a separate trained risk model.
16. **How does the report recommendation work?**  `insight_generator.py` uses explicit thresholds for prediction risk/confidence and available growth, runway, funding, and revenue.
17. **Why are there no hallucinations in the report?**  It does not use an LLM. It derives statements only from uploaded fields and deterministic rules.
18. **How are varying spreadsheet headers supported?**  `column_mapping.py` normalizes names and searches aliases, such as `Company Name`, `Company`, or `Startup Name`.
19. **What happens if the upload lacks a model feature?**  Report adaptation inserts `Not Available` for encoded categoricals and `0` for numerical features.
20. **What formats can users upload?**  CSV, XLSX, and XLS; `openpyxl` supports `.xlsx` reading.
21. **Why use Flask?**  It is a concise Python REST framework and integrates easily with the ML/report code.
22. **Why use CORS?**  Vite and Flask run on separate local origins/ports. CORS permits browser API requests between them.
23. **Why use Axios?**  It centralizes base URL, timeout, multipart requests, and error extraction.
24. **How does React obtain the model form fields?**  It calls `/model-info`; backend returns the persisted feature list and a complete sample record.
25. **How is the PDF generated?**  ReportLab builds text, tables, page breaks, and styles; Matplotlib creates local PNG charts which are embedded in the PDF.
26. **Why does report generation require selecting a row?**  It avoids silently generating a report for an unintended first row; the API requires `row_index`.
27. **Does the frontend currently support batch results visually?**  Not fully. The API and `predictCsv()` exist, and `Charts.jsx` can draw a distribution, but Dashboard does not invoke/pass batch result.
28. **What security limitations exist?**  CORS currently permits all origins, debug is enabled when running directly, there is no authentication, and files are written locally; production hardening is required.
29. **Why create output folders at runtime?**  The report generator ensures its target directory exists so report requests do not fail merely because `output/pdf/` is absent.
30. **How would you improve model quality?**  Audit features/leakage, remove identifiers, collect more balanced data, test alternatives, tune hyperparameters, calibrate probabilities, and evaluate per class.

## 18. How to Run the Project

### Prerequisites

- Python 3.11+ recommended by `README.md`.
- Node.js 20+ and npm recommended by `README.md`.

### Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python train_model.py
python app.py
```

Flask listens on `http://127.0.0.1:5000` (the code binds `0.0.0.0:5000`). Run `train_model.py` after changing `data/CleanStartups.csv`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite normally serves at `http://localhost:5173`.

### Environment variable

Optional `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:5000
```

### Common errors and troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Health shows unhealthy | Model artifacts are missing/corrupt. Run `python train_model.py` and inspect terminal errors. |
| Excel upload fails | Ensure `openpyxl` is installed and the spreadsheet is a readable `.xlsx`/`.xls` file. |
| API connection error | Start Flask, check port 5000, or set `VITE_API_BASE_URL` to the actual API URL. |
| Report says no company column | Rename/add a column such as `Company Name`, `Company`, or `Startup Name`. |
| Report has limited financial content | Upload actual numeric business columns (revenue, funding, burn, runway, growth, etc.); missing fields are intentionally not invented. |
| Port is already in use | Stop the old process or alter the Flask/Vite port and update frontend API configuration. |
| Changes do not appear in production frontend | Rebuild with `npm run build`; do not edit `frontend/dist` by hand. |

## 19. Team Handover Guide

### Recommended reading order

1. `README.md` and this document for architecture.
2. `app.py` for the public API contract.
3. `predict.py` for runtime inference.
4. `preprocess.py` and `train_model.py` for the ML lifecycle.
5. `dataset_preprocessing.py`, `column_mapping.py`, `insight_generator.py`, and `pdf_generator.py` for reporting.
6. `frontend/src/services/api.js`, then `pages/Dashboard.jsx`, then individual components.

### Debugging approach

- Start with `GET /health`, then `/model-info`, then `/metrics` to isolate artifact vs frontend issues.
- Reproduce backend requests with Postman/curl before debugging React rendering.
- Inspect Flask terminal logs for warnings/errors, especially unseen category warnings.
- Test the selected file/row in `/reports/companies` before `/reports/generate`.
- Use `python check_data.py` to inspect processed target counts and types.

### Adding a feature safely

1. Decide whether it belongs to input validation, prediction, report logic, API, or UI.
2. If adding a model feature, update dataset preparation, retrain, regenerate artifacts, and confirm `/model-info` returns it.
3. If adding an API route, add server validation/error responses and an `api.js` function.
4. Add/modify a focused React component and call that service function from `Dashboard.jsx` or a new page.
5. Test error states and verify that generated PDFs render correctly.
6. Update this document and `README.md`; code documentation must match the actual endpoint behaviour.

## 20. Project Summary

- VentureSignal is a Flask + React startup screening and PDF-report platform.
- Its ML engine is a saved scikit-learn Random Forest, not an OpenAI/LLM integration.
- Training starts from `data/CleanStartups.csv`, preprocesses/encodes fields, uses a stratified 80/20 split, and saves artifacts under `model/`.
- Runtime inference in `predict.py` strictly aligns model features, uses saved encoders, and returns label/probability/confidence.
- Flask exposes health, metadata, metrics, single/batch prediction, company-list, and PDF-report routes.
- Flexible spreadsheet headers are matched through aliases in `column_mapping.py`.
- PDF generation is deterministic: ReportLab formats the document, Matplotlib provides charts, and rule-based insight functions create recommendations/risk notes.
- The React dashboard fetches model metadata, supports manual prediction, manages upload/report state, and previews/downloads a returned PDF.
- Existing limitations include class imbalance, encoded identity-like text features, unseen-category fallback, all-origin CORS, debug mode, local file outputs, and unfinished batch UI wiring.
- Treat the output as decision support requiring human verification—not as a replacement for legal, financial, or investment due diligence.
