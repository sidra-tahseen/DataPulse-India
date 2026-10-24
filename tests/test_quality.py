
from src.datapulse.quality import (
    check_completeness,
    check_schema,
    check_volume,
)


def test_completeness_with_missing_values():
    records = [
        {"cityname": "Surat", "month_year": "Jan-11", "total_rainfall": "10"},
        {"cityname": "Surat", "month_year": "Feb-11", "total_rainfall": "NA"},
    ]

    result = check_completeness(
        records,
        ["cityname", "month_year", "total_rainfall"],
    )

    assert result["missing_values"] == 1
    assert result["completeness_percent"] == 83.33


def test_schema_valid():
    records = [
        {"cityname": "Surat", "month_year": "Jan-11", "total_rainfall": "10"}
    ]

    result = check_schema(
        records,
        ["cityname", "month_year", "total_rainfall"],
    )

    assert result["schema_valid"] is True
    assert result["missing_fields"] == []


def test_schema_missing_field():
    records = [{"cityname": "Surat", "month_year": "Jan-11"}]

    result = check_schema(
        records,
        ["cityname", "month_year", "total_rainfall"],
    )

    assert result["schema_valid"] is False
    assert result["missing_fields"] == ["total_rainfall"]


def test_volume():
    data = {
        "total": 130,
        "records": [{"cityname": "Surat"}, {"cityname": "Surat"}],
    }

    result = check_volume(data)

    assert result["records_fetched"] == 2
    assert result["records_reported"] == 130
