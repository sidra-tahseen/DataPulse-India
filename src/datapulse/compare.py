
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "data" / "reports"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

COMPLETENESS_DROP_THRESHOLD = 5.0


def _dataset_slug(dataset_id):
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(dataset_id)).strip("_")
    if not slug:
        raise ValueError("dataset_id must contain letters or numbers.")
    return slug.lower()


def _load_latest_two(files, description):
    files = sorted(files)

    if len(files) < 2:
        raise ValueError(
            f"At least two {description} are required. "
            "Run the monitor twice to create them."
        )

    with files[-2].open("r", encoding="utf-8") as file:
        previous = json.load(file)

    with files[-1].open("r", encoding="utf-8") as file:
        current = json.load(file)

    return previous, current


def load_latest_reports(dataset_id="rainfall_surat"):
    """Load the two most recent reports for one dataset."""
    slug = _dataset_slug(dataset_id)
    return _load_latest_two(
        REPORT_DIR.glob(f"health_report_{slug}_*.json"),
        "health reports",
    )


def load_latest_snapshots(dataset_id="rainfall_surat"):
    """Load the two most recent snapshots for one dataset."""
    slug = _dataset_slug(dataset_id)
    return _load_latest_two(
        RAW_DATA_DIR.glob(f"{slug}_*.json"),
        "raw snapshots",
    )




def compare_snapshots(
    previous,
    current,
    key_fields=("cityname", "month_year"),
):
    """Compare snapshots and detect day-to-day mandi price movements."""
    import math
    from datetime import datetime

    if not key_fields:
        raise ValueError("At least one record identifier field is required.")

    old_records = previous.get("records", [])
    new_records = current.get("records", [])

    if not isinstance(old_records, list) or not isinstance(new_records, list):
        raise ValueError("Snapshot records must be lists.")

    def make_record_map(records):
        record_map = {}

        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Every dataset record must be an object.")

            values = [record.get(field) for field in key_fields]

            if any(value is None or str(value).strip() == "" for value in values):
                raise ValueError(
                    "Cannot compare records: missing identifier field(s) "
                    f"{', '.join(key_fields)}."
                )

            key = tuple(str(value).strip() for value in values)

            if key in record_map:
                raise ValueError(f"Duplicate record identifier found: {key}")

            record_map[key] = record

        return record_map

    old_map = make_record_map(old_records)
    new_map = make_record_map(new_records)

    old_keys = set(old_map)
    new_keys = set(new_map)

    added_keys = sorted(new_keys - old_keys)
    removed_keys = sorted(old_keys - new_keys)
    common_keys = old_keys & new_keys

    def make_identifier(key):
        return dict(zip(key_fields, key))

    modified_records = []

    for key in sorted(common_keys):
        old_record = old_map[key]
        new_record = new_map[key]
        changed_fields = {}

        for field in sorted(set(old_record) | set(new_record)):
            old_value = old_record.get(field)
            new_value = new_record.get(field)

            if old_value != new_value:
                changed_fields[field] = {
                    "previous": old_value,
                    "current": new_value,
                }

        if changed_fields:
            modified_records.append({
                "record_id": make_identifier(key),
                "changed_fields": changed_fields,
            })

    def parse_date(value):
        if not value:
            return None

        for date_format in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(str(value).strip(), date_format)
            except ValueError:
                continue

        return None

    def valid_price(record):
        try:
            price = float(record.get("modal_price"))
        except (TypeError, ValueError):
            return None

        if not math.isfinite(price) or price < 0:
            return None

        return price

    price_changes = []

    # Only run this comparison for the mandi dataset.
    if all(
        records is not None
        for records in (old_records, new_records)
    ) and any(
        "modal_price" in record
        for record in old_records + new_records
        if isinstance(record, dict)
    ):
        identity_fields = (
            "state",
            "district",
            "market",
            "commodity",
            "variety",
            "grade",
        )

        def latest_prices(records):
            latest = {}

            for record in records:
                if not isinstance(record, dict):
                    continue

                identity = tuple(
                    str(record.get(field) or "").strip()
                    for field in identity_fields
                )

                # Avoid matching unrelated or incomplete market records.
                if not all(identity):
                    continue

                price = valid_price(record)
                arrival_date = parse_date(record.get("arrival_date"))

                if price is None or arrival_date is None:
                    continue

                existing = latest.get(identity)

                if (
                    existing is None
                    or arrival_date > existing["_parsed_date"]
                ):
                    latest[identity] = {
                        **record,
                        "_parsed_date": arrival_date,
                        "_parsed_price": price,
                    }

            return latest

        old_prices = latest_prices(old_records)
        new_prices = latest_prices(new_records)

        for identity in sorted(set(old_prices) & set(new_prices)):
            old_record = old_prices[identity]
            new_record = new_prices[identity]

            previous_price = old_record["_parsed_price"]
            current_price = new_record["_parsed_price"]
            difference = round(current_price - previous_price, 2)

            if difference > 0:
                direction = "INCREASE"
            elif difference < 0:
                direction = "DECREASE"
            else:
                direction = "UNCHANGED"

            # A zero previous price has no meaningful percentage change.
            percentage_change = (
                round(difference / previous_price * 100, 2)
                if previous_price != 0
                else None
            )

            # Report only actual price movements.
            if difference == 0:
                continue

            price_changes.append({
                "record_id": dict(zip(identity_fields, identity)),
                "commodity": new_record.get("commodity"),
                "market": new_record.get("market"),
                "district": new_record.get("district"),
                "state": new_record.get("state"),
                "previous_arrival_date": old_record.get("arrival_date"),
                "current_arrival_date": new_record.get("arrival_date"),
                "previous_modal_price": previous_price,
                "current_modal_price": current_price,
                "change_amount": difference,
                "change_percent": percentage_change,
                "direction": direction,
            })

    return {
        "records_previous": len(old_records),
        "records_current": len(new_records),
        "added_count": len(added_keys),
        "removed_count": len(removed_keys),
        "modified_count": len(modified_records),
        "added_records": [make_identifier(key) for key in added_keys],
        "removed_records": [make_identifier(key) for key in removed_keys],
        "modified_records": modified_records,
        "price_changes": price_changes,
        "price_change_count": len(price_changes),
        "price_increases": sum(
            change["direction"] == "INCREASE" for change in price_changes
        ),
        "price_decreases": sum(
            change["direction"] == "DECREASE" for change in price_changes
        ),
    }


def compare_reports(previous, current):
    """Compare two health reports and identify quality changes."""

    old = previous["health_metrics"]
    new = current["health_metrics"]

    changes = []
    alerts = []

    completeness_change = round(
        new["completeness_percent"] - old["completeness_percent"], 2
    )

    if completeness_change != 0:
        changes.append(
            f"Completeness: {old['completeness_percent']}% -> "
            f"{new['completeness_percent']}% ({completeness_change:+.2f} points)"
        )

    if completeness_change <= -COMPLETENESS_DROP_THRESHOLD:
        alerts.append(
            f"Completeness dropped by "
            f"{abs(completeness_change):.2f} percentage points."
        )

    if old["schema_valid"] and not new["schema_valid"]:
        alerts.append("Schema regression: required fields are missing.")
    elif not old["schema_valid"] and new["schema_valid"]:
        changes.append("Schema recovered: all required fields are present.")

    if old["records_fetched"] != new["records_fetched"]:
        changes.append(
            f"Fetched records: {old['records_fetched']} -> "
            f"{new['records_fetched']}"
        )

    if old["records_reported"] != new["records_reported"]:
        changes.append(
            f"Source-reported total: {old['records_reported']} -> "
            f"{new['records_reported']}"
        )

    if not changes:
        changes.append("No changes detected in the monitored metrics.")

    return {"changes": changes, "alerts": alerts}


def main():
    try:
        previous_report, current_report = load_latest_reports()
        previous_snapshot, current_snapshot = load_latest_snapshots()

        result = compare_reports(previous_report, current_report)
        record_changes = compare_snapshots(previous_snapshot, current_snapshot)

        print("\n========== DATAPULSE CHANGE REPORT ==========")
        print("Dataset:", current_report.get("dataset", "Unknown"))
        print("Previous check:", previous_report.get("checked_at"))
        print("Current check:", current_report.get("checked_at"))

        print("\n--- HEALTH METRIC CHANGES ---")
        for change in result["changes"]:
            print("-", change)

        print("\n--- RECORD-LEVEL CHANGES ---")
        print("Previous records:", record_changes["records_previous"])
        print("Current records:", record_changes["records_current"])
        print("Added:", record_changes["added_count"])
        print("Removed:", record_changes["removed_count"])
        print("Modified:", record_changes["modified_count"])

        for record in record_changes["added_records"]:
            print("ADDED:", record)
        for record in record_changes["removed_records"]:
            print("REMOVED:", record)
        for record in record_changes["modified_records"]:
            print("MODIFIED:", record)

        print("\n--- ALERTS ---")
        if result["alerts"]:
            for alert in result["alerts"]:
                print("ALERT:", alert)
        else:
            print("No new quality regressions detected.")

        print("=============================================")

    except (ValueError, OSError, json.JSONDecodeError, KeyError) as error:
        print("Comparison failed:", error)


if __name__ == "__main__":
    main()
