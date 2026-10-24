
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = PROJECT_ROOT / "data" / "metrics"
METRICS_FILE = METRICS_DIR / "api_requests.jsonl"


def record_api_request(
    dataset_id,
    duration_ms,
    success,
    status_code=None,
    attempt_count=1,
    error_type=None,
):
    """Append one API request's reliability metrics."""

    metric = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset_id,
        "duration_ms": round(duration_ms, 2),
        "success": bool(success),
        "status_code": status_code,
        "attempt_count": attempt_count,
        "error_type": error_type,
    }

    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    with METRICS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(metric) + "\n")

    return metric


def load_api_metrics(limit=100):
    """Load the most recent API request metrics."""

    if not METRICS_FILE.exists():
        return []

    with METRICS_FILE.open("r", encoding="utf-8") as file:
        lines = file.readlines()

    metrics = []

    for line in lines[-max(0, limit):] if limit > 0 else []:
        try:
            metrics.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return metrics
def get_reliability_summary(dataset_id=None, limit=100):
    """Calculate reliability statistics from recorded API requests."""
    metrics = load_api_metrics(limit=limit)

    if dataset_id:
        metrics = [
            metric
            for metric in metrics
            if metric.get("dataset_id") == dataset_id
        ]

    total_requests = len(metrics)

    if total_requests == 0:
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "success_rate": 0.0,
            "average_response_time_ms": 0.0,
            "retry_frequency": 0.0,
        }

    successful_requests = sum(
        1 for metric in metrics if metric.get("success") is True
    )

    failed_requests = total_requests - successful_requests

    average_response_time = sum(
        float(metric.get("duration_ms", 0))
        for metric in metrics
    ) / total_requests

    retried_requests = sum(
        1 for metric in metrics
        if int(metric.get("attempt_count", 1)) > 1
    )

    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate": round(
            successful_requests / total_requests * 100, 2
        ),
        "average_response_time_ms": round(
            average_response_time, 2
        ),
        "retry_frequency": round(
            retried_requests / total_requests * 100, 2
        ),
    }