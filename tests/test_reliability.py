
import json

import src.datapulse.reliability as reliability


def test_record_api_request_saves_metrics(tmp_path, monkeypatch):
    metrics_file = tmp_path / "api_requests.jsonl"
    monkeypatch.setattr(reliability, "METRICS_DIR", tmp_path)
    monkeypatch.setattr(reliability, "METRICS_FILE", metrics_file)

    metric = reliability.record_api_request(
        dataset_id="rainfall_surat",
        duration_ms=125.678,
        success=True,
        status_code=200,
        attempt_count=2,
    )

    assert metric["dataset_id"] == "rainfall_surat"
    assert metric["duration_ms"] == 125.68
    assert metric["success"] is True
    assert metric["status_code"] == 200
    assert metric["attempt_count"] == 2

    saved = json.loads(metrics_file.read_text(encoding="utf-8"))
    assert saved == metric


def test_load_api_metrics_returns_latest_entries(tmp_path, monkeypatch):
    metrics_file = tmp_path / "api_requests.jsonl"
    monkeypatch.setattr(reliability, "METRICS_FILE", metrics_file)

    entries = [
        {"dataset_id": "rainfall_surat", "duration_ms": 100},
        {"dataset_id": "rainfall_surat", "duration_ms": 200},
        {"dataset_id": "rainfall_surat", "duration_ms": 300},
    ]

    metrics_file.write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries),
        encoding="utf-8",
    )

    assert reliability.load_api_metrics(limit=2) == entries[-2:]


def test_load_api_metrics_handles_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        reliability,
        "METRICS_FILE",
        tmp_path / "missing.jsonl",
    )

    assert reliability.load_api_metrics() == []
