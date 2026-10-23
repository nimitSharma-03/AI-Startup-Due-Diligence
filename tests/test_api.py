import io

import pytest
from pypdf import PdfReader

from .conftest import GENERIC_CSV


def upload(client, content: str | bytes, name: str = "startups.csv", path: str = "/api/datasets"):
    data = content.encode() if isinstance(content, str) else content
    return client.post(path, data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data")


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["status"] == "ok" and body["model_loaded"] and body["reference_rows"] == 617
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_model_info_and_metrics(client):
    info = client.get("/api/model").get_json()["data"]
    assert info["classes"] == ["Dead", "Exited", "Operating"]
    assert [field["name"] for field in info["schema"]] == info["input_columns"]
    metrics = client.get("/api/model/metrics").get_json()["data"]
    assert {"cross_validation", "holdout", "holdout_comparison", "data_quality"} <= set(metrics)
    importance = client.get("/api/model/feature-importance").get_json()["data"]
    assert importance["permutation"][0]["feature"] == "year"


def test_list_search_filter_sort_paginate(client):
    body = client.get("/api/startups?page_size=10").get_json()
    assert len(body["data"]) == 10 and body["meta"]["total"] == 617

    search = client.get("/api/startups?q=zencoder").get_json()["data"]
    assert [row["name"] for row in search] == ["Zencoder"]

    filtered = client.get("/api/startups?status=Dead&city=San Francisco&page_size=100").get_json()
    assert filtered["meta"]["total"] > 0
    assert all(row["status"] == "Dead" and row["city"] == "San Francisco" for row in filtered["data"])

    by_funding = client.get("/api/startups?sort=total_funding&order=desc&page_size=5").get_json()["data"]
    amounts = [row["total_funding"] for row in by_funding]
    assert amounts == sorted(amounts, reverse=True)

    years = client.get("/api/startups?year_min=2013&year_max=2013&page_size=100").get_json()
    assert years["meta"]["total"] == 85


def test_list_rejects_bad_parameters(client):
    assert client.get("/api/startups?sort=bogus").status_code == 400
    assert client.get("/api/startups?funding_min=abc").status_code == 400
    assert client.get("/api/startups?page=x").status_code == 400


def test_facets(client):
    facets = client.get("/api/startups/facets").get_json()["data"]
    assert facets["years"][0] == 2005 and facets["years"][-1] == 2014
    assert set(facets["statuses"]) == {"Operating", "Exited", "Dead"}


def test_startup_detail(client):
    detail = client.get("/api/startups/3").get_json()["data"]
    assert detail["name"] == "Zencoder" and detail["status"] == "Exited"
    assert detail["prediction"]["predicted_outcome"] in {"Dead", "Exited", "Operating"}
    assert detail["explanation"] and detail["summary"]
    assert {"strengths", "risks", "limitations", "considerations"} <= set(detail["insights"])
    assert client.get("/api/startups/99999").status_code == 404


def test_predict_success_and_validation(client):
    good = client.post("/api/predict", json={"data": {"year": 2012, "total_funding": "1.5M", "markets": "SaaS"}})
    assert good.status_code == 200
    body = good.get_json()["data"]
    assert abs(sum(body["prediction"]["probabilities"].values()) - 1) < 1e-3
    assert "city" in body["missing_fields"] and body["explanation"]

    bad = client.post("/api/predict", json={"year": "nineteen", "total_funding": -1})
    assert bad.status_code == 422
    error = bad.get_json()["error"]
    assert error["code"] == "validation_failed" and set(error["details"]) == {"year", "total_funding"}

    assert client.post("/api/predict", data="not json", content_type="application/json").status_code == 400


def test_batch_prediction_json_and_csv(client):
    response = client.post("/api/predict/batch", json={"records": [{"year": 2010}, {"year": "bad"}]})
    body = response.get_json()
    assert response.status_code == 200 and body["meta"] == {"rows": 2, "scored": 1}
    assert body["data"][1]["issues"]

    csv_response = client.post("/api/predict/batch?format=csv", json={"records": [{"year": 2010, "name": "=cmd"}]})
    assert csv_response.mimetype == "text/csv"
    assert "'=cmd" in csv_response.get_data(as_text=True)


def test_upload_workflow(client):
    validation = upload(client, GENERIC_CSV, path="/api/datasets/validate")
    assert validation.status_code == 200
    report = validation.get_json()["data"]
    assert report["rows"] == 5 and report["scorable_rows"] == 3 and report["rows_with_issues"] == 2

    created = upload(client, GENERIC_CSV)
    assert created.status_code == 201
    dataset = created.get_json()["data"]
    dataset_id = dataset["id"]
    assert dataset["kind"] == "upload" and len(dataset_id) >= 20

    rows = client.get(f"/api/startups?dataset={dataset_id}").get_json()
    assert rows["meta"]["total"] == 5
    acme = next(row for row in rows["data"] if row["name"] == "Acme Robotics")
    detail = client.get(f"/api/startups/{acme['id']}?dataset={dataset_id}").get_json()["data"]
    assert detail["dataset"]["kind"] == "upload"

    pdf = client.get(f"/api/startups/{acme['id']}/report.pdf?dataset={dataset_id}")
    assert pdf.status_code == 200
    assert "Acme Robotics" in PdfReader(io.BytesIO(pdf.data)).pages[0].extract_text()

    analytics = client.get(f"/api/analytics?dataset={dataset_id}").get_json()["data"]
    assert analytics["totals"]["startups"] == 5

    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 200
    assert client.get(f"/api/startups?dataset={dataset_id}").status_code == 404


@pytest.mark.parametrize(
    "content, name, status",
    [
        ("Company,Funding\nA,1\n", "x.csv", 422),
        ("year\n2010\n", "x.xlsx", 415),
        ("", "x.csv", 400),
    ],
)
def test_upload_rejections(client, content, name, status):
    assert upload(client, content, name).status_code == status


def test_upload_size_limit(app, client):
    big = b"Company,YCYear\n" + b"A,2010\n" * (app.config["MAX_CONTENT_LENGTH"] // 7 + 10)
    assert upload(client, big).status_code == 413


def test_unknown_dataset_and_reference_protection(client):
    assert client.get("/api/startups?dataset=does-not-exist").status_code == 404
    assert client.delete("/api/datasets/reference").status_code == 400


@pytest.mark.parametrize("startup_id", ["3", "50", "200", "451"])
def test_reports_are_company_specific(client, startup_id):
    detail = client.get(f"/api/startups/{startup_id}").get_json()["data"]
    response = client.get(f"/api/startups/{startup_id}/report.pdf")
    assert response.status_code == 200 and response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in detail["name"]).strip("_")
    assert safe_name.split("_")[0] in response.headers["Content-Disposition"]
    reader = PdfReader(io.BytesIO(response.data))
    assert len(reader.pages) >= 6
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert detail["name"] in text
    for section in (
        "Executive summary", "Company profile", "Available financial information", "Funding analysis",
        "Model prediction", "Model confidence and limitations", "Risk indicators", "Strength indicators",
        "Feature contribution analysis", "Investment-related considerations",
        "Data quality and missing-information disclosures", "Methodology", "Disclaimer",
    ):
        assert section in text, section
    assert "Strong Buy" not in text


def test_reports_differ_between_companies(client):
    first = client.get("/api/startups/3/report.pdf").data
    second = client.get("/api/startups/50/report.pdf").data
    text_a = PdfReader(io.BytesIO(first)).pages[0].extract_text()
    text_b = PdfReader(io.BytesIO(second)).pages[0].extract_text()
    assert text_a != text_b


def test_export_csv(client):
    response = client.get("/api/startups/export.csv?status=Exited")
    lines = response.get_data(as_text=True).strip().splitlines()
    assert lines[0].startswith("row_number,name") and len(lines) == 81


def test_analytics(client):
    data = client.get("/api/analytics").get_json()["data"]
    assert data["totals"]["startups"] == 617
    assert sum(item["count"] for item in data["predicted_distribution"]) == 617
    assert {item["name"]: item["count"] for item in data["status_distribution"]} == {"Operating": 452, "Dead": 85, "Exited": 80}
    assert data["funding"]["reported"] == 570


def test_unknown_api_route_returns_json(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404 and response.get_json()["error"]["code"] == "not_found"
