
from datetime import datetime, timezone


def check_freshness(updated_at, max_age_days=30):
    """Check whether a dataset's last update is recent enough."""

    if not updated_at:
        return {
            "freshness_status": "UNKNOWN",
            "age_days": None,
            "message": "Dataset update timestamp is unavailable.",
        }

    try:
        update_time = datetime.fromisoformat(
            updated_at.replace("Z", "+00:00")
        )

        if update_time.tzinfo is None:
            update_time = update_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_seconds = (now - update_time.astimezone(timezone.utc)).total_seconds()
        age_days = round(age_seconds / 86400, 2)

        if age_seconds < 0:
            return {
                "freshness_status": "UNKNOWN",
                "age_days": age_days,
                "message": "Dataset update timestamp is in the future.",
            }

        status = "FRESH" if age_days <= max_age_days else "STALE"

        return {
            "freshness_status": status,
            "age_days": age_days,
            "message": (
                "Dataset is within the configured age limit."
                if status == "FRESH"
                else "Dataset exceeds the configured age limit."
            ),
        }

    except (ValueError, TypeError):
        return {
            "freshness_status": "UNKNOWN",
            "age_days": None,
            "message": "Dataset update timestamp is invalid.",
        }
