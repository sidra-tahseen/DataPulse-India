
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "data" / "reports"


def save_health_report(
    dataset,
    completeness,
    schema,
    volume,
    freshness=None,
    dataset_id=None,
    anomalies=None,
    score=None,
    success_rate=None,
):
    """Save quality, anomaly, and health-score results for one run."""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "dataset": dataset,
        "dataset_id": dataset_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "health_metrics": {
            "completeness_percent": completeness["completeness_percent"],
            "missing_values": completeness["missing_values"],
            "missing_by_field": completeness["missing_by_field"],
            "schema_valid": schema["schema_valid"],
            "missing_fields": schema["missing_fields"],
            "records_fetched": volume["records_fetched"],
            "records_reported": volume["records_reported"],
            "freshness_status": (
                freshness["freshness_status"] if freshness else "UNKNOWN"
            ),
            "age_days": freshness["age_days"] if freshness else None,
            "health_score": score,
            "anomalies": anomalies or {},
            "api_success_rate": success_rate,
        },
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    file_path = REPORT_DIR / f"health_report_{timestamp}.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    return file_path
