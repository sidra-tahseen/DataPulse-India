
from src.datapulse.quality import check_anomalies, health_score


def test_flags_obvious_outlier():
    records = [{"x": str(v)} for v in
               [10, 11, 12, 10, 11, 12, 10, 11, 500]]

    result = check_anomalies(records, ["x"])

    assert result["x"]["outlier_count"] == 1
    assert result["x"]["outliers"] == [500]


def test_skips_fields_with_too_few_values():
    result = check_anomalies(
        [{"x": "10"}, {"x": "12"}, {"x": "NA"}],
        ["x"],
    )

    assert result["x"]["outlier_count"] == 0
    assert result["x"]["checked"] == 2


def test_perfect_score_is_100():
    volume = {"records_fetched": 5, "records_reported": 5}

    assert health_score(100, True, "FRESH", volume, 100) == 100


def test_stale_dataset_loses_freshness_points():
    volume = {"records_fetched": 5, "records_reported": 5}

    score = health_score(100, True, "STALE", volume, 100)

    assert score == 85
