"""REST API routes, all under ``/api``."""

from __future__ import annotations

import re
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

from diligence import analytics
from diligence.data import query
from diligence.data.ingest import (
    CONCEPT_LABELS,
    DatasetError,
    SINGLE_ALIASES,
    MULTI_ALIASES,
    load_dataset,
)
from diligence.data.store import Dataset, DatasetStore
from diligence.errors import ApiError
from diligence.insights import ReferenceStats, analyse, executive_summary
from diligence.ml.model import ModelService
from diligence.ml.schema import FIELD_SPECS, ValidationError, parse_record
from diligence.reports.pdf import build_report

api = Blueprint("api", __name__, url_prefix="/api")
RECOMMENDED = ("name", "total_funding", "city", "markets", "session")


def ok(data: Any, status: int = 200, **meta: Any):
    body: dict[str, Any] = {"data": data}
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def services() -> tuple[ModelService, DatasetStore, ReferenceStats]:
    ext = current_app.extensions["diligence"]
    return ext["model"], ext["store"], ext["stats"]


def get_dataset(dataset_id: str | None = None) -> Dataset:
    _, store, _ = services()
    dataset_id = dataset_id if dataset_id is not None else request.args.get("dataset")
    dataset = store.get(dataset_id)
    if dataset is None:
        raise ApiError(
            404,
            "dataset_not_found",
            "This uploaded dataset is no longer available. Uploads are kept in memory for a limited time; please upload it again.",
        )
    return dataset


def get_record(dataset: Dataset, startup_id: str) -> dict[str, Any]:
    record = dataset.index.get(startup_id)
    if record is None:
        raise ApiError(404, "startup_not_found", "No startup with this id exists in the selected dataset.")
    return record


def explanation_for(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    if not record.get("model_input"):
        return None
    if "_explanation" not in record:
        model, _, _ = services()
        record["_explanation"] = model.explain(record["model_input"])
    return record["_explanation"]


def detail(dataset: Dataset, record: dict[str, Any]) -> dict[str, Any]:
    _, _, stats = services()
    insight = analyse(record, stats, dataset.kind)
    return {
        **query.summary(record),
        "description": record.get("description"),
        "website": record.get("website"),
        "founders": record.get("founders") or [],
        "investors": record.get("investors") or [],
        "prediction": record.get("prediction"),
        "out_of_fold_probabilities": record.get("out_of_fold_probabilities"),
        "explanation": explanation_for(record),
        "insights": insight,
        "summary": executive_summary(record, insight, stats, dataset.kind),
        "missing_fields": record.get("missing_fields") or [],
        "warnings": record.get("warnings") or [],
        "dataset": {"id": dataset.id, "name": dataset.name, "kind": dataset.kind},
    }


def column_report(dataset_mapping) -> list[dict[str, Any]]:
    mapping = dataset_mapping.as_dict()
    concepts = list(SINGLE_ALIASES) + list(MULTI_ALIASES)
    report = []
    for concept in concepts:
        level = "required" if concept == "year" else "recommended" if concept in RECOMMENDED else "optional"
        report.append({
            "concept": concept,
            "label": CONCEPT_LABELS[concept],
            "level": level,
            "columns": mapping.get(concept, []),
            "found": concept in mapping,
        })
    return report


def upload_report(records: list[dict[str, Any]], mapping, source_columns: list[str]) -> dict[str, Any]:
    issues = [
        {"row_number": record["row_number"], "name": record["name"], "issues": record["issues"]}
        for record in records
        if record["issues"]
    ]
    columns = column_report(mapping)
    warnings = [
        f"No {item['label'].lower()} column was found; that input will be treated as missing for every row."
        for item in columns
        if item["level"] == "recommended" and not item["found"]
    ]
    return {
        "rows": len(records),
        "scorable_rows": sum(1 for record in records if record["model_input"] is not None),
        "rows_with_issues": len(issues),
        "issues": issues[:200],
        "columns": columns,
        "source_columns": source_columns,
        "unused_columns": mapping.unused,
        "warnings": warnings,
        "preview": [query.summary(record) for record in records[:25]],
    }


def read_upload() -> tuple[bytes, str]:
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ApiError(400, "file_required", "Attach a CSV file in the 'file' form field.")
    if not re.search(r"\.csv$", upload.filename, re.IGNORECASE):
        raise ApiError(415, "unsupported_file_type", "Only .csv files are supported.")
    content = upload.read()
    if not content:
        raise ApiError(400, "empty_file", "The uploaded file is empty.")
    return content, upload.filename


# --------------------------------------------------------------------------- health and model
@api.get("/health")
def health():
    model, store, _ = services()
    return ok({
        "status": "ok",
        "model_loaded": True,
        "model": model.metadata["model_name"],
        "trained_at": model.metadata["trained_at"],
        "reference_rows": len(store.reference.records),
    })


@api.get("/model")
def model_info():
    model, _, _ = services()
    metadata = model.metadata
    return ok({
        **model.summary,
        "target": metadata["target"],
        "decision_rule": metadata["decision_rule"],
        "input_columns": metadata["input_columns"],
        "engineered_features": metadata["engineered_features"],
        "excluded_columns": metadata["excluded_columns"],
        "hyperparameters": metadata["hyperparameters"],
        "versions": metadata["versions"],
        "dataset": metadata["dataset"],
        "schema": FIELD_SPECS,
    })


@api.get("/model/schema")
def model_schema():
    return ok(FIELD_SPECS)


@api.get("/model/metrics")
def model_metrics():
    model, _, _ = services()
    return ok(model.metrics)


@api.get("/model/feature-importance")
def feature_importance():
    model, _, _ = services()
    return ok(model.importance())


# --------------------------------------------------------------------------- prediction
@api.post("/predict")
def predict():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "invalid_json", "Send a JSON object with the startup attributes.")
    raw = payload.get("data", payload)
    try:
        parsed = parse_record(raw)
    except ValidationError as error:
        raise ApiError(422, "validation_failed", "Some fields are invalid.", error.errors) from error
    model, _, stats = services()
    prediction = model.predict([parsed.values])[0]
    record = {
        "id": "input",
        "row_number": 1,
        "name": str(raw.get("name") or "Submitted startup")[:100],
        **{key: parsed.values[key] for key in ("year", "session", "total_funding", "city", "markets")},
        "model_input": parsed.values,
        "prediction": prediction,
        "issues": {},
        "warnings": parsed.warnings,
        "missing_fields": parsed.missing,
    }
    insight = analyse(record, stats, "input")
    return ok({
        "input": parsed.values,
        "prediction": prediction,
        "explanation": model.explain(parsed.values),
        "insights": insight,
        "summary": executive_summary(record, insight, stats, "input"),
        "warnings": parsed.warnings,
        "missing_fields": parsed.missing,
    })


@api.post("/predict/batch")
def predict_batch():
    model, _, _ = services()
    config = current_app.config["DILIGENCE"]
    if request.files:
        content, _ = read_upload()
        try:
            records, _, _ = load_dataset(content)
        except DatasetError as error:
            raise ApiError(422, "invalid_dataset", str(error)) from error
    else:
        payload = request.get_json(silent=True)
        items = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items:
            raise ApiError(400, "invalid_json", "Send {\"records\": [...]} or a CSV file.")
        if len(items) > config.max_batch_records:
            raise ApiError(413, "too_many_records", f"At most {config.max_batch_records} records per request.")
        records = []
        for position, item in enumerate(items):
            record = {
                "id": str(position),
                "row_number": position + 1,
                "name": str(item.get("name") or f"Record {position + 1}")[:100] if isinstance(item, dict) else f"Record {position + 1}",
                "issues": {},
                "model_input": None,
            }
            try:
                parsed = parse_record(item)
                record.update(model_input=parsed.values, **parsed.values)
            except ValidationError as error:
                record["issues"] = error.errors
            records.append(record)
    scorable = [record for record in records if record["model_input"] is not None]
    for record, prediction in zip(scorable, model.predict([r["model_input"] for r in scorable])):
        record["prediction"] = prediction
    if request.args.get("format") == "csv":
        return Response(
            query.to_csv(records),
            mimetype="text/csv",
            headers={"Content-Disposition": 'attachment; filename="batch_predictions.csv"'},
        )
    return ok(
        [query.summary(record) for record in records],
        rows=len(records),
        scored=len(scorable),
    )


# --------------------------------------------------------------------------- datasets
@api.get("/datasets")
def list_datasets():
    _, store, _ = services()
    return ok([store.reference.summary()])


@api.post("/datasets/validate")
def validate_dataset():
    content, filename = read_upload()
    try:
        records, mapping, frame = load_dataset(content)
    except DatasetError as error:
        raise ApiError(422, "invalid_dataset", str(error)) from error
    model, _, _ = services()
    scorable = [record for record in records if record["model_input"] is not None]
    for record, prediction in zip(scorable, model.predict([r["model_input"] for r in scorable])):
        record["prediction"] = prediction
    return ok({"filename": filename, **upload_report(records, mapping, list(frame.columns))})


@api.post("/datasets")
def upload_dataset():
    content, filename = read_upload()
    _, store, _ = services()
    try:
        dataset = store.add_upload(content, filename)
    except DatasetError as error:
        raise ApiError(422, "invalid_dataset", str(error)) from error
    return ok({**dataset.summary(), **upload_report(dataset.records, dataset.mapping, dataset.source_columns)}, 201)


@api.get("/datasets/<dataset_id>")
def dataset_summary(dataset_id: str):
    return ok(get_dataset(dataset_id).summary())


@api.delete("/datasets/<dataset_id>")
def delete_dataset(dataset_id: str):
    _, store, _ = services()
    if dataset_id == "reference":
        raise ApiError(400, "not_allowed", "The reference dataset cannot be deleted.")
    if not store.delete(dataset_id):
        raise ApiError(404, "dataset_not_found", "Dataset not found.")
    return ok({"deleted": dataset_id})


# --------------------------------------------------------------------------- startups
@api.get("/startups")
def list_startups():
    dataset = get_dataset()
    records = query.sort_records(query.filter_records(dataset.records, request.args), request.args)
    page, meta = query.paginate(records, request.args)
    return ok([query.summary(record) for record in page], **meta, dataset=dataset.id)


@api.get("/startups/facets")
def startup_facets():
    return ok(query.facets(get_dataset().records))


@api.get("/startups/export.csv")
def export_startups():
    dataset = get_dataset()
    records = query.sort_records(query.filter_records(dataset.records, request.args), request.args)
    return Response(
        query.to_csv(records),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="startups_export.csv"'},
    )


@api.get("/startups/<startup_id>")
def startup_detail(startup_id: str):
    dataset = get_dataset()
    return ok(detail(dataset, get_record(dataset, startup_id)))


@api.get("/startups/<startup_id>/report.pdf")
def startup_report(startup_id: str):
    dataset = get_dataset()
    record = get_record(dataset, startup_id)
    model, _, stats = services()
    insight = analyse(record, stats, dataset.kind)
    pdf = build_report(record, dataset.name, dataset.kind, model, stats, insight, explanation_for(record))
    safe = re.sub(r"[^A-Za-z0-9]+", "_", record["name"]).strip("_")[:60] or "startup"
    disposition = "inline" if request.args.get("inline") == "1" else "attachment"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="Due_Diligence_{safe}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@api.get("/analytics")
def dashboard_analytics():
    model, _, _ = services()
    dataset = get_dataset()
    return ok({**analytics.dashboard(dataset, model.classes), "model": model.summary})
