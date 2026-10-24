DATASETS = {
    "rainfall_surat": {
        "name": "Rainfall Monthly Surat",
        "resource_id": "ef07ba1e-a7c3-4897-aa78-ddb2652f7821",
        "required_fields": [
            "cityname",
            "month_year",
            "total_rainfall",
        ],
        "key_fields": ["cityname", "month_year"],
        "numeric_fields": ["total_rainfall"],
    },
        "mandi_prices": {
        "name": "Daily Mandi Commodity Prices",
        "resource_id": "9ef84268-d588-465a-a308-a864a43d0070",
        "required_fields": [
            "state",
            "district",
            "market",
            "commodity",
            "arrival_date",
            "min_price",
            "max_price",
            "modal_price",
        ],
        "key_fields": [
            "state",
            "district",
            "market",
            "commodity",
            "variety",
            "grade",
            "arrival_date",
        ],
        "numeric_fields": [
            "min_price",
            "max_price",
            "modal_price",
        ],
    },
}


def get_dataset(dataset_id="rainfall_surat"):
    """Return configuration for a registered dataset."""
    if dataset_id not in DATASETS:
        raise ValueError(f"Unknown dataset_id: {dataset_id}")
    return DATASETS[dataset_id]


def list_datasets():
    """Return dataset metadata suitable for the frontend."""
    return [
        {
            "id": dataset_id,
            "name": config["name"],
        }
        for dataset_id, config in DATASETS.items()
    ]
