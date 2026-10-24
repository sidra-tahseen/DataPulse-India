
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import time
import hashlib

from src.datapulse.reliability import record_api_request

import requests
from dotenv import load_dotenv

from src.datapulse.datasets import get_dataset

load_dotenv()

API_KEY = os.getenv("DATAGOV_API_KEY")
API_BASE_URL = "https://api.data.gov.in/resource"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def fetch_data(limit=100, offset=0, dataset_id="rainfall_surat"):
    """Fetch one page and record metrics for every HTTP attempt."""

    if not API_KEY:
        raise ValueError("DATAGOV_API_KEY is missing from .env")

    config = get_dataset(dataset_id)
    resource_id = config["resource_id"]
    api_url = f"{API_BASE_URL}/{resource_id}"

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit,
        "offset": offset,
    }

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        start_time = time.perf_counter()
        status_code = None

        try:
            response = requests.get(
                api_url,
                params=params,
                headers={"User-Agent": "DataPulse-India/1.0"},
                timeout=(10, 30),
            )
            status_code = response.status_code

            if status_code in (429, 500, 502, 503, 504):
                raise requests.exceptions.HTTPError(
                    f"Temporary server error: HTTP {status_code}",
                    response=response,
                )

            response.raise_for_status()

            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as error:
                raise ValueError(
                    "Government API returned invalid JSON."
                ) from error

            if not isinstance(data, dict):
                raise ValueError("Unexpected API response format.")

            if "records" in data and not isinstance(data["records"], list):
                raise ValueError(
                    "The API response contains an invalid records field."
                )

            duration_ms = (time.perf_counter() - start_time) * 1000

            record_api_request(
                dataset_id=dataset_id,
                duration_ms=duration_ms,
                success=True,
                status_code=status_code,
                attempt_count=attempt,
            )

            return data

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as error:
            retryable = True
            error_message = (
                "Government API request timed out."
                if isinstance(error, requests.exceptions.Timeout)
                else "Could not connect to the government API."
            )
            error_type = type(error).__name__

        except requests.exceptions.HTTPError as error:
            status = (
                error.response.status_code
                if error.response is not None
                else None
            )
            retryable = status in (429, 500, 502, 503, 504)
            error_message = f"Government API returned HTTP {status}."
            error_type = type(error).__name__

        except ValueError as error:
            duration_ms = (time.perf_counter() - start_time) * 1000

            record_api_request(
                dataset_id=dataset_id,
                duration_ms=duration_ms,
                success=False,
                status_code=status_code,
                attempt_count=attempt,
                error_type=type(error).__name__,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        record_api_request(
            dataset_id=dataset_id,
            duration_ms=duration_ms,
            success=False,
            status_code=status_code,
            attempt_count=attempt,
            error_type=error_type,
        )

        if not retryable:
            raise RuntimeError(error_message)

        if attempt == max_attempts:
            raise RuntimeError(
                f"Government API request failed after "
                f"{max_attempts} attempts: {error_message}"
            )

        wait_seconds = 2 ** attempt
        logger.warning(
            "Temporary API failure for dataset=%s, attempt=%s/%s. "
            "Retrying in %s seconds. Reason: %s",
            dataset_id,
            attempt,
            max_attempts,
            wait_seconds,
            error_message,
        )
        time.sleep(wait_seconds)





def fetch_all_data(limit=100, dataset_id="rainfall_surat"):
    """Fetch a bounded number of records in batches."""

    max_records = 1000
    limit = min(limit, max_records)

    first_page = fetch_data(
        limit=limit,
        offset=0,
        dataset_id=dataset_id,
    )

    records = first_page.get("records", [])
    if not isinstance(records, list):
        raise ValueError("The API response does not contain a valid records list.")

    all_records = list(records[:max_records])

    try:
        total = int(first_page.get("total", len(all_records)))
    except (TypeError, ValueError):
        total = len(all_records)

    offset = len(records)

    while offset < min(total, max_records):
        remaining = max_records - len(all_records)
        page_limit = min(limit, remaining)

        page = fetch_data(
            limit=page_limit,
            offset=offset,
            dataset_id=dataset_id,
        )
        page_records = page.get("records", [])

        if not isinstance(page_records, list):
            raise ValueError("The API returned an invalid records list.")

        if not page_records:
            logger.warning(
                "API returned an empty page before all records were fetched "
                "for dataset=%s",
                dataset_id,
            )
            break

        all_records.extend(page_records)
        offset += len(page_records)

        logger.info(
            "Fetched %s records (source reports %s) for dataset=%s",
            len(all_records),
            total,
            dataset_id,
        )

    result = dict(first_page)
    result["records"] = all_records
    result["total"] = total
    result["fetched_records"] = len(all_records)
    result["dataset_id"] = dataset_id

    return result


def save_snapshot(data, dataset_id=None):
    """Save a snapshot only when its dataset content has changed."""

    dataset_id = dataset_id or data.get("dataset_id", "rainfall_surat")
    config = get_dataset(dataset_id)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = dict(data)
    snapshot["dataset_id"] = dataset_id
    snapshot["dataset_name"] = config["name"]

    # Hash the dataset payload, excluding metadata that changes on every run.
    content = {
        key: value
        for key, value in snapshot.items()
        if key not in {
            "checked_at",
            "timestamp",
            "fetched_at",
            "ingested_at",
        }
    }

    canonical_json = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    content_hash = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()

    # Find the newest snapshot for this dataset.
    existing_files = sorted(
        RAW_DATA_DIR.glob(f"{dataset_id}_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if existing_files:
        latest_path = existing_files[0]

        try:
            with latest_path.open("r", encoding="utf-8") as file:
                latest_snapshot = json.load(file)

            latest_content = {
                key: value
                for key, value in latest_snapshot.items()
                if key not in {
                    "checked_at",
                    "timestamp",
                    "fetched_at",
                    "ingested_at",
                }
            }

            latest_json = json.dumps(
                latest_content,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            latest_hash = hashlib.sha256(
                latest_json.encode("utf-8")
            ).hexdigest()

            if content_hash == latest_hash:
                logger.info(
                    "Dataset unchanged; reusing snapshot for dataset=%s",
                    dataset_id,
                )
                return latest_path

        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Could not read latest snapshot for dataset=%s; "
                "creating a new snapshot.",
                dataset_id,
            )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    file_path = RAW_DATA_DIR / f"{dataset_id}_{timestamp}.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(snapshot, file, indent=2, ensure_ascii=False)

    logger.info(
        "Snapshot saved for dataset=%s at %s",
        dataset_id,
        file_path,
    )

    return file_path

def main():
    dataset_id = "rainfall_surat"
    data = fetch_all_data(limit=100, dataset_id=dataset_id)
    file_path = save_snapshot(data, dataset_id=dataset_id)

    logger.info("Dataset: %s", data.get("title", "Unknown"))
    logger.info("Dataset ID: %s", dataset_id)
    logger.info(
       "Records reported by source: %s",
       data.get("total", "Unknown"),
    )
    logger.info("Records fetched: %s", len(data.get("records", [])))

    if len(data.get("records", [])) < int(data.get("total", 0)):
        logger.warning(
           "Fetched record count is below the reported total for dataset=%s",
           dataset_id,
        )


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.RequestException:
        logger.error("Government API request failed.")
    except (OSError, ValueError, RuntimeError) as error:
        logger.error("Ingestion failed: %s", type(error).__name__)
