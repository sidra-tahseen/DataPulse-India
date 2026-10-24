
def check_completeness(records, required_fields):
    """Check for missing values in required fields."""

    total_missing = 0
    missing_by_field = {}

    for field in required_fields:
        missing_count = sum(
            1
            for record in records
            if record.get(field) is None
            or str(record.get(field)).strip().upper() in ("", "NA", "N/A", "NULL")
        )

        missing_by_field[field] = missing_count
        total_missing += missing_count

    total_cells = len(records) * len(required_fields)

    completeness = (
        round((1 - total_missing / total_cells) * 100, 2)
        if total_cells > 0
        else 0.0
    )

    return {
        "completeness_percent": completeness,
        "missing_values": total_missing,
        "missing_by_field": missing_by_field,
    }


def check_schema(records, required_fields):
    """Check whether records contain all expected fields."""

    if not records:
        return {
            "schema_valid": False,
            "missing_fields": required_fields.copy(),
        }

    actual_fields = set(records[0].keys())
    missing_fields = [
        field for field in required_fields
        if field not in actual_fields
    ]

    return {
        "schema_valid": len(missing_fields) == 0,
        "missing_fields": missing_fields,
    }


def check_volume(data):
    """Compare the fetched record count with the API-reported total."""

    records = data.get("records", [])
    reported_total = data.get("total")

    return {
        "records_fetched": len(records),
        "records_reported": (
            int(reported_total) if reported_total is not None else None
        ),
    }

def _to_float(value):
    """Convert a value to a number, or return None if invalid."""
    try:
        number = float(str(value).replace(",", "").strip())
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def check_anomalies(records, numeric_fields, k=1.5):
    """Flag potential outliers using IQR fences."""
    result = {}

    for field in numeric_fields:
        values = sorted(
            number
            for number in (_to_float(record.get(field)) for record in records)
            if number is not None
        )

        if len(values) < 8:
            result[field] = {
                "outlier_count": 0,
                "checked": len(values),
                "outliers": [],
                "message": "Not enough numeric values; at least 8 required.",
            }
            continue

        q1 = values[len(values) // 4]
        q3 = values[(3 * len(values)) // 4]
        iqr = q3 - q1
        low = q1 - k * iqr
        high = q3 + k * iqr

        outliers = [
            value for value in values
            if value < low or value > high
        ]

        result[field] = {
            "outlier_count": len(outliers),
            "checked": len(values),
            "fences": [round(low, 2), round(high, 2)],
            "outliers": outliers,
            "message": (
                "Potential outliers detected."
                if outliers
                else "No outliers detected."
            ),
        }

    return result


def health_score(
    completeness,
    schema_valid,
    freshness_status,
    volume,
    success_rate,
):
    """Calculate a weighted dataset health score from 0 to 100."""
    score = 0.35 * completeness
    score += 25 if schema_valid else 0

    score += {
        "FRESH": 20,
        "STALE": 5,
    }.get(freshness_status, 10)

    fetched = volume["records_fetched"]
    reported = volume["records_reported"]

    if reported and fetched >= reported:
        score += 10

    score += 0.10 * success_rate

    return round(max(0, min(100, score)), 1)
