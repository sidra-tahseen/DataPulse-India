
import argparse

from src.datapulse.datasets import get_dataset
from src.datapulse.ingestion import fetch_all_data, save_snapshot
from src.datapulse.quality import (
    check_completeness,
    check_schema,
    check_volume,
    check_anomalies,
    health_score,
)
from src.datapulse.freshness import check_freshness
from src.datapulse.reporting import save_health_report
from src.datapulse.price_history import record_price_history
from src.datapulse.reliability import get_reliability_summary


def main(dataset_id="rainfall_surat"):
    config = get_dataset(dataset_id)

    # Fetch dataset records
    data = fetch_all_data(limit=100, dataset_id=dataset_id)
    records = data.get("records", [])

    # Save a snapshot and record price history
    snapshot_path = save_snapshot(data, dataset_id=dataset_id)

    price_changes = record_price_history(
        records,
        dataset_id=dataset_id,
    )

    # Run existing data quality checks
    required_fields = config["required_fields"]

    completeness = check_completeness(records, required_fields)
    schema = check_schema(records, required_fields)
    volume = check_volume(data)
    freshness = check_freshness(data.get("updated_date"))

    # Detect potential outliers in configured numeric fields
    anomalies = check_anomalies(
        records,
        config.get("numeric_fields", []),
    )

    # Get API reliability statistics
    reliability = get_reliability_summary(dataset_id=dataset_id)
    success_rate = float(reliability.get("success_rate", 0))

    # Calculate the overall dataset health score
    score = health_score(
        completeness["completeness_percent"],
        schema["schema_valid"],
        freshness["freshness_status"],
        volume,
        success_rate,
    )

    # Save the complete health report
    report_path = save_health_report(
        dataset=data.get("title", config["name"]),
        completeness=completeness,
        schema=schema,
        volume=volume,
        freshness=freshness,
        dataset_id=dataset_id,
        anomalies=anomalies,
        score=score,
        success_rate=success_rate,
    )

    # Display monitoring results
    print("\n========== DATAPULSE INDIA ==========")
    print("Dataset:", data.get("title", config["name"]))
    print("Dataset ID:", dataset_id)

    print("\n--- COMPLETENESS ---")
    print("Completeness:", f"{completeness['completeness_percent']}%")
    print("Missing values:", completeness["missing_values"])

    print("\n--- SCHEMA ---")
    print("Schema valid:", schema["schema_valid"])
    print("Missing fields:", schema["missing_fields"])

    print("\n--- VOLUME ---")
    print("Records fetched:", volume["records_fetched"])
    print("Records reported:", volume["records_reported"])

    print("\n--- FRESHNESS ---")
    print("Source update date:", data.get("updated_date"))
    print("Freshness status:", freshness["freshness_status"])
    print("Dataset age (days):", freshness["age_days"])
    print(freshness["message"])

    print("\n--- ANOMALIES ---")
    if anomalies:
        for field, result in anomalies.items():
            print(
                f"{field}: {result['outlier_count']} potential outlier(s) "
                f"from {result['checked']} numeric values"
            )
    else:
        print("No numeric fields configured for anomaly detection.")

    print("\n--- OVERALL HEALTH ---")
    print(f"Health score: {score}/100")
    print(f"API success rate: {success_rate}%")

    print("\n--- SNAPSHOT & PRICE HISTORY ---")
    print("Snapshot saved:", snapshot_path)
    print("Price observations saved:", dataset_id == "mandi_prices")
    print("Price movements detected:", len(price_changes))

    print("\nHealth report saved:", report_path)
    print("=====================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default="rainfall_surat",
        help="ID of the configured dataset to monitor",
    )
    args = parser.parse_args()
    main(args.dataset)
