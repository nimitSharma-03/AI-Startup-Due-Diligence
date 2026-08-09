"""Flask REST API for the AI Startup Due Diligence Platform."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

from dataset_preprocessing import (
    adapt_for_model,
    filter_company_data,
    get_company_list,
    read_startup_file,
)
from pdf_generator import generate_report
from predict import PredictionError, load_prediction_artifacts, predict_dataframe


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
METRICS_PATH = PROJECT_ROOT / "model" / "metrics.json"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "model" / "feature_importance.csv"
DATASET_PATH = PROJECT_ROOT / "data" / "CleanStartups.csv"
TARGET_COLUMN = "Fate"
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    @app.get("/")
    def index() -> Response:
        """Return a lightweight API discovery response."""
        return jsonify(
            {
                "service": "AI Startup Due Diligence API",
                "status": "running",
                "endpoints": [
                    "/health",
                    "/predict",
                    "/reports/companies",
                    "/reports/generate",
                    "/model-info",
                    "/metrics",
                ],
            }
        )

    @app.get("/health")
    def health() -> tuple[Response, int]:
        """Report whether the API and saved prediction artifacts are available."""
        try:
            load_prediction_artifacts()
        except PredictionError as error:
            LOGGER.warning("Health check failed: %s", error)
            return jsonify(
                {
                    "status": "unhealthy",
                    "model_loaded": False,
                    "backend_running": True,
                    "message": str(error),
                }
            ), 503

        return jsonify(
            {
                "status": "healthy",
                "model_loaded": True,
                "backend_running": True,
            }
        ), 200

    @app.post("/predict")
    def predict_single() -> Response:
        """Predict one startup from a JSON object."""
        payload = request.get_json(silent=False)
        if not isinstance(payload, dict) or not payload:
            raise BadRequest("Request body must be a non-empty JSON object.")

        record = payload.get("data", payload)
        if not isinstance(record, dict) or not record:
            raise BadRequest("The 'data' value must be a non-empty JSON object.")

        result = predict_dataframe(pd.DataFrame([record]))
        prediction = result.iloc[0]
        return jsonify(
            {
                "prediction": prediction["Prediction"],
                "probability": float(prediction["Probability"]),
                "confidence": float(prediction["Confidence"]),
                "risk_level": get_risk_level(str(prediction["Prediction"])),
            }
        )

    @app.post("/predict/csv")
    def predict_csv() -> Response:
        """Predict all rows in an uploaded CSV and return JSON or a CSV download."""
        uploaded_file = request.files.get("file")
        if uploaded_file is None or not uploaded_file.filename:
            raise BadRequest("Upload a spreadsheet in the 'file' form field.")
        if not allowed_file(uploaded_file.filename):
            raise BadRequest("Only CSV, XLSX, and XLS files are supported.")
        dataframe = read_startup_file(uploaded_file, uploaded_file.filename)
        _, features, encoders = load_prediction_artifacts()
        result = predict_dataframe(adapt_for_model(dataframe, features, encoders))
        result["Risk Level"] = result["Prediction"].map(get_risk_level)

        records = json.loads(result.to_json(orient="records"))
        return jsonify({"rows_predicted": len(records), "results": records})

    @app.post("/reports/generate")
    def generate_pdf_report() -> Response:
        """Generate a PDF for the explicitly selected company in an upload."""
        uploaded_file = request.files.get("file")
        if uploaded_file is None or not uploaded_file.filename:
            raise BadRequest("Upload a startup spreadsheet in the 'file' form field.")
        if not allowed_file(uploaded_file.filename):
            raise BadRequest("Only CSV, XLSX, and XLS files are supported.")
        dataframe = read_startup_file(uploaded_file, uploaded_file.filename)
        row_index = parse_selected_row(request.form.get("row_index"))
        company_dataframe = filter_company_data(dataframe, row_index)
        _, features, encoders = load_prediction_artifacts()
        predictions = predict_dataframe(adapt_for_model(company_dataframe, features, encoders))
        first = predictions.iloc[0]
        prediction = {"prediction": str(first["Prediction"]), "probability": float(first["Probability"]), "confidence": float(first["Confidence"]), "risk_level": get_risk_level(str(first["Prediction"]))}
        company_name = str(get_company_list(company_dataframe)[0]["name"])
        safe_name = "".join(character if character.isalnum() else "_" for character in company_name).strip("_")[:60]
        filename = f"Due_Diligence_Report_{safe_name or 'Startup'}.pdf"
        report_path = PROJECT_ROOT / "output" / "pdf" / filename
        generate_report(company_dataframe, prediction, load_metrics(), report_path, dataset_name=uploaded_file.filename)
        return send_file(report_path, mimetype="application/pdf", as_attachment=True, download_name=filename)

    @app.post("/reports/companies")
    def list_report_companies() -> Response:
        """Read an upload and return selectable records before report generation."""
        uploaded_file = request.files.get("file")
        if uploaded_file is None or not uploaded_file.filename:
            raise BadRequest("Upload a startup spreadsheet in the 'file' form field.")
        if not allowed_file(uploaded_file.filename):
            raise BadRequest("Only CSV, XLSX, and XLS files are supported.")
        dataframe = read_startup_file(uploaded_file, uploaded_file.filename)
        return jsonify({"companies": get_company_list(dataframe), "rows_available": len(dataframe)})

    @app.get("/model-info")
    def model_info() -> Response:
        """Return model metadata and feature names needed by the frontend."""
        model, features, _ = load_prediction_artifacts()
        return jsonify(
            {
                "model_name": type(model).__name__,
                "algorithm": "Random Forest Classifier",
                "number_of_features": len(features),
                "training_samples": get_training_sample_count(),
                "target_variable": TARGET_COLUMN,
                "features": features,
                "sample_input": get_sample_input(features),
                "feature_importance": get_feature_importance(),
            }
        )

    @app.get("/metrics")
    def metrics() -> Response:
        """Return the primary metrics saved by the training pipeline."""
        metrics_data = load_metrics()
        return jsonify(
            {
                "accuracy": metrics_data.get("accuracy"),
                "precision": metrics_data.get("precision_weighted"),
                "recall": metrics_data.get("recall_weighted"),
                "f1": metrics_data.get("f1_weighted"),
                "roc_auc": metrics_data.get("roc_auc_ovr_weighted"),
            }
        )

    @app.errorhandler(PredictionError)
    def handle_prediction_error(error: PredictionError) -> tuple[Response, int]:
        """Format model and input errors as client-safe API responses."""
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(BadRequest)
    def handle_bad_request(error: BadRequest) -> tuple[Response, int]:
        """Return JSON for malformed client requests."""
        return jsonify({"error": error.description}), 400

    @app.errorhandler(413)
    def handle_file_too_large(_: Any) -> tuple[Response, int]:
        """Return a useful message for uploads above the configured limit."""
        return jsonify({"error": "Uploaded file exceeds the 10 MB limit."}), 413

    return app


def allowed_file(filename: str) -> bool:
    """Return whether a filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_selected_row(value: str | None) -> int:
    """Require an explicit selected row; reports must never silently use row one."""
    if value is None:
        raise BadRequest("Select a company before generating a report.")
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise BadRequest("The selected company row is invalid.") from error


def get_risk_level(prediction: str) -> str:
    """Map the model's outcome label to a presentation-friendly risk level."""
    normalized_prediction = prediction.lower()
    if "operating" in normalized_prediction:
        return "Low"
    if "exited" in normalized_prediction or "acquired" in normalized_prediction:
        return "Medium"
    return "High"


def load_metrics() -> dict[str, Any]:
    """Load the evaluation report created by the training pipeline."""
    if not METRICS_PATH.is_file():
        raise PredictionError(
            f"Metrics file was not found: {METRICS_PATH}. Run train_model.py first."
        )
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PredictionError(f"Could not read model metrics: {error}") from error


def get_training_sample_count() -> int | None:
    """Return the source dataset row count when it is available."""
    if not DATASET_PATH.is_file():
        return None
    try:
        return int(len(pd.read_csv(DATASET_PATH)))
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return None


def get_sample_input(features: list[str]) -> dict[str, Any]:
    """Return a safe sample record to prefill the browser prediction form."""
    if not DATASET_PATH.is_file():
        return {feature: "" for feature in features}
    try:
        dataframe = pd.read_csv(DATASET_PATH)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return {feature: "" for feature in features}

    dataframe = dataframe.drop(columns=[TARGET_COLUMN], errors="ignore")
    if dataframe.empty:
        return {feature: "" for feature in features}

    sample = dataframe.iloc[0].reindex(features)
    return {
        feature: None if pd.isna(value) else value
        for feature, value in sample.to_dict().items()
    }


def get_feature_importance() -> list[dict[str, Any]]:
    """Load the top ten saved feature-importance records when available."""
    if not FEATURE_IMPORTANCE_PATH.is_file():
        return []
    try:
        importance = pd.read_csv(FEATURE_IMPORTANCE_PATH).head(10)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return []

    if not {"feature", "importance"}.issubset(importance.columns):
        return []
    return json.loads(importance.to_json(orient="records"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    create_app().run(host="0.0.0.0", port=5000, debug=True)
