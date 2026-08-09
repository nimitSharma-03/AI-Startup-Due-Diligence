# AI Startup Due Diligence Platform

A full-stack machine-learning application for evaluating startup outcomes. The platform pairs a Flask REST API with a React/Vite dashboard to score individual startups or entire CSV portfolios using a trained Random Forest classifier.

## Highlights

- Single-startup prediction with outcome, probability, confidence, and risk level
- Batch CSV scoring with downloadable prediction results
- Feature-importance and evaluation-metric visualizations
- REST API with input validation, clear error responses, CORS, and health checks
- Responsive dark, glassmorphism-inspired dashboard built with React, Tailwind CSS, Framer Motion, and Recharts

## Architecture

```text
React + Vite dashboard
        |
      Axios
        |
 Flask REST API (Flask-CORS)
        |
     predict.py
        |
Random Forest model artifacts
```

## Project structure

```text
AI-Startup-Due-Diligence/
├── app.py                 # Flask API entry point
├── preprocess.py          # Dataset cleaning and label encoding
├── train_model.py         # Random Forest training and evaluation
├── predict.py             # Validated prediction pipeline
├── model/                 # Saved model, metrics, encoders, feature importance
├── data/                  # Source and processed startup datasets
├── requirements.txt
└── frontend/              # React + Vite dashboard
    └── src/
        ├── components/
        ├── pages/
        └── services/api.js
```

## Requirements

- Python 3.11+
- Node.js 20+ and npm

## Backend setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python train_model.py
python app.py
```

The API starts at `http://127.0.0.1:5000`.

## Frontend setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dashboard is typically available at `http://localhost:5173`. To point it at another API URL, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:5000
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API discovery response |
| GET | `/health` | API and model-artifact health |
| POST | `/predict` | Predict one JSON startup record |
| POST | `/predict/csv` | Score an uploaded CSV |
| POST | `/predict/csv?download=true` | Download scored CSV results |
| GET | `/model-info` | Model metadata, features, and feature importance |
| GET | `/metrics` | Accuracy, precision, recall, F1, and ROC-AUC |

### Single prediction example

```json
POST /predict
{
  "data": {
    "Company": "Example AI",
    "YCYear": 2024
  }
}
```

Supply every feature returned from `/model-info`; the dashboard pre-populates a valid example automatically.

## Model artifacts

Run `python train_model.py` after changing data. It writes:

- `model/risk_model.pkl`
- `model/features.pkl`
- `model/label_encoders.pkl`
- `model/metrics.json`
- `model/feature_importance.csv`

## Screenshots

_Add screenshots of the dashboard, batch upload workflow, and prediction cards here._

## Future improvements

- Authentication and portfolio workspaces
- SHAP-based per-prediction explanations
- Database-backed prediction history
- Model versioning and automated retraining
- Containerized deployment with CI/CD

## License

This project is provided for educational and portfolio use. Add a license file before production distribution.
