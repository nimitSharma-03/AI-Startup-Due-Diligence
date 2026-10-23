import pytest

from diligence.data.ingest import DatasetError, load_dataset, map_columns, read_csv_bytes
from diligence.ml.schema import ValidationError, parse_money, parse_record, parse_session

from .conftest import GENERIC_CSV


@pytest.mark.parametrize(
    "raw, expected",
    [(1500000, 1500000.0), ("1.5M", 1500000.0), ("$2,000,000", 2000000.0), ("750k", 750000.0), ("0", 0.0)],
)
def test_parse_money_accepts_common_formats(raw, expected):
    assert parse_money(raw) == expected


@pytest.mark.parametrize("raw", ["-5", "abc", "1.5Q", True, float("inf")])
def test_parse_money_rejects_invalid(raw):
    with pytest.raises(ValueError):
        parse_money(raw)


def test_parse_session_variants():
    assert parse_session("W") == "Winter"
    assert parse_session("summer") == "Summer"
    with pytest.raises(ValueError):
        parse_session("autumn")


def test_parse_record_requires_year_and_reports_missing():
    with pytest.raises(ValidationError) as error:
        parse_record({"total_funding": 100})
    assert "year" in error.value.errors

    parsed = parse_record({"year": "2012", "markets": "SaaS, Analytics, saas"})
    assert parsed.values["year"] == 2012
    assert parsed.values["markets"] == ["SaaS", "Analytics"]
    assert set(parsed.missing) == {"session", "total_funding", "city"}


def test_parse_record_warns_outside_training_range():
    parsed = parse_record({"year": 2020})
    assert parsed.warnings and "outside the training range" in parsed.warnings[0]


def test_parse_record_collects_all_errors():
    with pytest.raises(ValidationError) as error:
        parse_record({"year": 1800, "session": "x", "total_funding": "-1", "markets": [f"m{i}" for i in range(11)]})
    assert set(error.value.errors) == {"year", "session", "total_funding", "markets"}


def test_map_columns_handles_reference_and_generic_headers():
    reference = map_columns(["Company", "YCYear", "TotalFunds", "Market1", "Market2", "Fate", "Logo"])
    assert reference.single["year"] == "YCYear"
    assert reference.multi["markets"] == ["Market1", "Market2"]
    assert "Logo" in reference.unused

    generic = map_columns(["Company Name", "Founded Year", "Funding", "Industry"])
    assert generic.single == {"name": "Company Name", "year": "Founded Year", "total_funding": "Funding"}
    assert generic.multi["markets"] == ["Industry"]


def test_load_dataset_marks_invalid_rows():
    records, mapping, _ = load_dataset(GENERIC_CSV.encode())
    assert len(records) == 5
    acme, beta, gamma, no_year, formula = records
    assert acme["model_input"]["total_funding"] == 2_500_000
    assert acme["markets"] == ["Hardware", "Robotics"]
    assert beta["status"] == "Dead" and gamma["status"] == "Exited"
    assert no_year["issues"] == {"year": "is required"}
    assert "total_funding" in formula["issues"]


def test_load_dataset_rejects_files_without_year_column():
    with pytest.raises(DatasetError, match="year"):
        load_dataset(b"Company,Funding\nA,100\n")


@pytest.mark.parametrize("content", [b"", b"\x00\x01binary", b"a,b\n"])
def test_read_csv_rejects_unusable_files(content):
    with pytest.raises(DatasetError):
        read_csv_bytes(content)
