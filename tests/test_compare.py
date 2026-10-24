
from src.datapulse.compare import compare_reports


def make_report(completeness, schema_valid=True, fetched=100, total=130):
    return {
        "health_metrics": {
            "completeness_percent": completeness,
            "schema_valid": schema_valid,
            "records_fetched": fetched,
            "records_reported": total,
        }
    }


def test_completeness_drop_triggers_alert():
    previous = make_report(90.0)
    current = make_report(80.0)

    result = compare_reports(previous, current)

    assert any("Completeness dropped" in alert for alert in result["alerts"])


def test_schema_regression_triggers_alert():
    previous = make_report(90.0, schema_valid=True)
    current = make_report(90.0, schema_valid=False)

    result = compare_reports(previous, current)

    assert any("Schema regression" in alert for alert in result["alerts"])


def test_unchanged_metrics_have_no_alerts():
    previous = make_report(90.0)
    current = make_report(90.0)

    result = compare_reports(previous, current)

    assert result["alerts"] == []
