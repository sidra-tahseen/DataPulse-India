import json

import src.datapulse.ingestion as ingestion


def test_unchanged_data_reuses_existing_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(ingestion, "RAW_DATA_DIR", tmp_path)

    data = {
        "title": "Test Dataset",
        "total": 2,
        "records": [
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
        ],
    }

    first_path = ingestion.save_snapshot(
        data,
        dataset_id="rainfall_surat",
    )

    second_data = {
        **data,
        "checked_at": "later",
        "fetched_at": "later",
    }

    second_path = ingestion.save_snapshot(
        second_data,
        dataset_id="rainfall_surat",
    )

    assert first_path == second_path
    assert len(list(tmp_path.glob("rainfall_surat_*.json"))) == 1


def test_changed_data_creates_new_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(ingestion, "RAW_DATA_DIR", tmp_path)

    original = {
        "title": "Test Dataset",
        "total": 1,
        "records": [{"id": 1, "value": 10}],
    }

    changed = {
        "title": "Test Dataset",
        "total": 1,
        "records": [{"id": 1, "value": 15}],
    }

    first_path = ingestion.save_snapshot(
        original,
        dataset_id="rainfall_surat",
    )

    second_path = ingestion.save_snapshot(
        changed,
        dataset_id="rainfall_surat",
    )

    assert first_path != second_path
    assert len(list(tmp_path.glob("rainfall_surat_*.json"))) == 2

    with second_path.open("r", encoding="utf-8") as file:
        saved = json.load(file)

    assert saved["records"][0]["value"] == 15