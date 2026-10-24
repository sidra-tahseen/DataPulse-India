
import requests
import pytest

import src.datapulse.ingestion as ingestion
import src.datapulse.reliability as reliability


def test_retry_records_failure_then_success(monkeypatch, tmp_path):
    recorded = []
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1

        if calls["count"] == 1:
            raise requests.exceptions.Timeout("simulated timeout")

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"records": [{"cityname": "Surat"}]}

        return FakeResponse()

    monkeypatch.setattr(ingestion, "API_KEY", "test-key")
    monkeypatch.setattr(ingestion.requests, "get", fake_get)
    monkeypatch.setattr(ingestion.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        ingestion,
        "record_api_request",
        lambda **kwargs: recorded.append(kwargs),
    )

    result = ingestion.fetch_data(dataset_id="rainfall_surat")

    assert result["records"][0]["cityname"] == "Surat"
    assert calls["count"] == 2
    assert len(recorded) == 2
    assert recorded[0]["success"] is False
    assert recorded[0]["error_type"] == "Timeout"
    assert recorded[1]["success"] is True
    assert recorded[1]["status_code"] == 200
    assert recorded[1]["attempt_count"] == 2


def test_exhausted_retries_record_each_failure(monkeypatch):
    recorded = []

    def fake_get(*args, **kwargs):
        raise requests.exceptions.Timeout("simulated timeout")

    monkeypatch.setattr(ingestion, "API_KEY", "test-key")
    monkeypatch.setattr(ingestion.requests, "get", fake_get)
    monkeypatch.setattr(ingestion.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        ingestion,
        "record_api_request",
        lambda **kwargs: recorded.append(kwargs),
    )

    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        ingestion.fetch_data(dataset_id="rainfall_surat")

    assert len(recorded) == 3
    assert all(item["success"] is False for item in recorded)
def test_api_key_is_not_exposed_in_errors_or_logs(monkeypatch, caplog):
    dummy_key = "DUMMY_SECRET_KEY_12345"
    recorded = []

    def fake_get(*args, **kwargs):
        # Simulate a request exception containing the API key in its URL.
        raise requests.exceptions.Timeout(
            f"Request timed out for https://example.com/?api-key={dummy_key}"
        )

    monkeypatch.setattr(ingestion, "API_KEY", dummy_key)
    monkeypatch.setattr(ingestion.requests, "get", fake_get)
    monkeypatch.setattr(ingestion.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        ingestion,
        "record_api_request",
        lambda **kwargs: recorded.append(kwargs),
    )

    with pytest.raises(RuntimeError) as exc_info:
        ingestion.fetch_data(dataset_id="rainfall_surat")

    assert dummy_key not in str(exc_info.value)
    assert dummy_key not in caplog.text
    assert len(recorded) == 3
    assert all(item["success"] is False for item in recorded)