
from datetime import datetime, timedelta, timezone

from src.datapulse.freshness import check_freshness


def test_recent_update_is_fresh():
    updated_at = datetime.now(timezone.utc).isoformat()

    result = check_freshness(updated_at, max_age_days=30)

    assert result["freshness_status"] == "FRESH"


def test_old_update_is_stale():
    old_date = datetime.now(timezone.utc) - timedelta(days=60)

    result = check_freshness(old_date.isoformat(), max_age_days=30)

    assert result["freshness_status"] == "STALE"


def test_missing_timestamp_is_unknown():
    result = check_freshness(None)

    assert result["freshness_status"] == "UNKNOWN"


def test_invalid_timestamp_is_unknown():
    result = check_freshness("not-a-date")

    assert result["freshness_status"] == "UNKNOWN"
