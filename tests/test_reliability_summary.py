import src.datapulse.reliability as reliability


def test_reliability_summary_calculates_metrics(monkeypatch):
    metrics = [
        {
            "dataset_id": "rainfall_surat",
            "success": True,
            "duration_ms": 100,
            "attempt_count": 1,
        },
        {
            "dataset_id": "rainfall_surat",
            "success": False,
            "duration_ms": 300,
            "attempt_count": 1,
        },
        {
            "dataset_id": "rainfall_surat",
            "success": True,
            "duration_ms": 200,
            "attempt_count": 2,
        },
    ]

    monkeypatch.setattr(
        reliability, "load_api_metrics", lambda limit=100: metrics
    )

    summary = reliability.get_reliability_summary(
        dataset_id="rainfall_surat"
    )

    assert summary["total_requests"] == 3
    assert summary["successful_requests"] == 2
    assert summary["failed_requests"] == 1
    assert summary["success_rate"] == 66.67
    assert summary["average_response_time_ms"] == 200.0
    assert summary["retry_frequency"] == 33.33


def test_reliability_summary_handles_no_requests(monkeypatch):
    monkeypatch.setattr(
        reliability, "load_api_metrics", lambda limit=100: []
    )

    summary = reliability.get_reliability_summary(
        dataset_id="rainfall_surat"
    )

    assert summary == {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "success_rate": 0.0,
        "average_response_time_ms": 0.0,
        "retry_frequency": 0.0,
    }