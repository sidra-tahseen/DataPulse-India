
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

from src.datapulse.datasets import get_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_DIR = PROJECT_ROOT / "data" / "history"
HISTORY_FILE = HISTORY_DIR / "mandi_prices.jsonl"
CHANGES_FILE = HISTORY_DIR / "mandi_price_changes.jsonl"

logger = logging.getLogger(__name__)

IDENTITY_FIELDS = (
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
)


def _parse_price(record):
    try:
        price = float(record.get("modal_price"))
    except (TypeError, ValueError):
        return None

    if not math.isfinite(price) or price < 0:
        return None

    return price


def _parse_arrival_date(value):
    if not value:
        return None

    for date_format in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(
                str(value).strip(), date_format
            ).date()
        except ValueError:
            continue

    return None


def _load_latest_observations():
    """Load the latest valid observation for each market identity."""
    latest = {}

    if not HISTORY_FILE.exists():
        return latest

    with HISTORY_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                observation = json.loads(line)
                identity = tuple(
                    str(observation.get(field) or "").strip()
                    for field in IDENTITY_FIELDS
                )
                price = _parse_price(observation)

                if (
                    not all(identity)
                    or price is None
                    or not observation.get("arrival_date")
                    or not observation.get("observed_at")
                ):
                    continue

                observation["modal_price"] = price
                latest[identity] = observation

            except (json.JSONDecodeError, TypeError, ValueError):
                logger.warning("Skipping invalid price-history entry.")

    return latest


def _append_jsonl(path, records):
    if not records:
        return

    with path.open("a", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_price_history(records, dataset_id="mandi_prices"):
    """Store changed observations and persist detected price revisions."""

    if dataset_id != "mandi_prices":
        return []

    if not isinstance(records, list):
        raise ValueError("Price history records must be a list.")

    get_dataset(dataset_id)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    previous_by_identity = _load_latest_observations()
    observed_at = datetime.now(timezone.utc).isoformat()

    new_observations = []
    price_changes = []
    seen = set()

    for record in records:
        if not isinstance(record, dict):
            continue

        identity = tuple(
            str(record.get(field) or "").strip()
            for field in IDENTITY_FIELDS
        )

        if not all(identity) or identity in seen:
            continue

        seen.add(identity)

        price = _parse_price(record)
        arrival_date = _parse_arrival_date(record.get("arrival_date"))

        if price is None or arrival_date is None:
            continue

        arrival_date_text = arrival_date.isoformat()
        previous = previous_by_identity.get(identity)

        observation = {
            "dataset_id": dataset_id,
            "observed_at": observed_at,
            "arrival_date": arrival_date_text,
            **dict(zip(IDENTITY_FIELDS, identity)),
            "modal_price": price,
        }

        if previous is not None:
            previous_price = previous["modal_price"]
            same_arrival_date = (
                previous.get("arrival_date") == arrival_date_text
            )
            difference = round(price - previous_price, 2)

            if same_arrival_date and difference != 0:
                price_changes.append({
                    "dataset_id": dataset_id,
                    **dict(zip(IDENTITY_FIELDS, identity)),
                    "arrival_date": arrival_date_text,
                    "previous_modal_price": previous_price,
                    "current_modal_price": price,
                    "change_amount": difference,
                    "change_percent": (
                        round(difference / previous_price * 100, 2)
                        if previous_price != 0
                        else None
                    ),
                    "direction": (
                        "INCREASE" if difference > 0 else "DECREASE"
                    ),
                    "previous_observed_at": previous.get("observed_at"),
                    "current_observed_at": observed_at,
                })

        # Keep a new observation only when its price or arrival date changes.
        if previous is None or (
            previous["modal_price"] != price
            or previous.get("arrival_date") != arrival_date_text
        ):
            new_observations.append(observation)

        # Update in-memory state even if no line needs appending.
        previous_by_identity[identity] = observation

    _append_jsonl(HISTORY_FILE, new_observations)
    _append_jsonl(CHANGES_FILE, price_changes)

    logger.info(
        "Price history: %s new observations, %s price movements",
        len(new_observations),
        len(price_changes),
    )

    return price_changes


def get_price_history(limit=100):
    """Return the most recent saved price observations."""
    if limit < 1:
        raise ValueError("limit must be at least 1.")

    if not HISTORY_FILE.exists():
        return []

    observations = []

    with HISTORY_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                observations.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return observations[-limit:][::-1]


def get_price_changes(limit=100):
    """Return the most recent persisted price movements."""
    if limit < 1:
        raise ValueError("limit must be at least 1.")

    if not CHANGES_FILE.exists():
        return []

    changes = []

    with CHANGES_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                changes.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return changes[-limit:][::-1]
