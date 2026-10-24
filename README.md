# DataPulse India

**Open-source data quality monitoring for Indian government datasets.**

DataPulse India is a Python and React application that monitors the quality, freshness, volume, and reliability of open government data. It collects data from the Government of India's Open Government Data API, runs configurable quality checks, records monitoring reports, and presents results through an interactive dashboard.

## Features

- **Completeness checks:** Measure missing values in required fields, including empty strings and common missing-value markers.
- **Schema validation:** Check whether records contain the expected required fields.
- **Volume validation:** Compare the number of fetched records with the total reported by the source.
- **Freshness monitoring:** Track source update dates and classify dataset freshness.
- **Historical monitoring:** Save snapshots and reports to support comparisons over time.
- **Snapshot deduplication:** Reuse existing snapshots when the fetched dataset content has not changed.
- **Statistical anomaly detection:** Identify potential outliers in suitable numeric fields using the interquartile range (IQR) method.
- **Dataset health score:** Calculate a unified score from 0 to 100 using the implemented quality and monitoring metrics.
- **Reliability metrics:** Record API request latency, status, success or failure, and retry attempts.
- **Record-level price history:** Track observations and detected price movements for the mandi price dataset.
- **Automated monitoring:** Run monitoring jobs through APScheduler.
- **Interactive dashboard:** Explore monitoring reports, trends, historical records, and dataset information using React and Recharts.
- **REST API:** Access monitoring results and history through FastAPI endpoints.

> **Scope note:** Schema validation currently focuses on required fields rather than comprehensive schema-drift or type-drift detection. Statistical outliers are potential anomalies, not necessarily erroneous records. The health score is a summary indicator, not a guarantee of overall data accuracy.

## Supported datasets

The current registry contains two datasets from data.gov.in:

| Dataset ID | Dataset | Required-field checks |
|---|---|---|
| `rainfall_surat` | Rainfall Monthly Surat | `cityname`, `month_year`, `total_rainfall` |
| `mandi_prices` | Daily Mandi Commodity Prices | State, district, market, commodity, arrival date, and price fields |

Dataset definitions and resource IDs are maintained in `src/datapulse/datasets.py`.

The number of datasets is intentionally limited while the ingestion, quality checks, monitoring, and historical tracking workflows are being validated.

## Architecture

```text
Government Open Data API (data.gov.in)
                  |
                  v
          Data ingestion
       retries and API metrics
                  |
                  v
       Timestamped snapshots
       with deduplication
                  |
                  v
         Quality checks
   completeness, schema, volume,
     freshness, anomaly detection
                  |
                  v
       Health score calculation
                  |
                  v
       Monitoring reports
       and price history
                  |
                  v
           FastAPI REST API
                  |
                  v
        React + Recharts UI

       APScheduler runs monitoring
       jobs automatically.
```

### Technology stack

- **Language:** Python
- **Backend:** FastAPI, Uvicorn
- **Data ingestion:** Requests, python-dotenv
- **Scheduling:** APScheduler
- **Frontend:** React, Vite
- **Charts:** Recharts
- **Testing:** pytest
- **Data storage:** Local JSON and JSONL files

## Project structure

```text
DataPulse-India/
├── src/
│   └── datapulse/
│       ├── api.py
│       ├── compare.py
│       ├── datasets.py
│       ├── freshness.py
│       ├── ingestion.py
│       ├── monitor.py
│       ├── price_history.py
│       ├── quality.py
│       ├── reliability.py
│       └── reporting.py
├── tests/
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── data/
│   ├── raw/
│   ├── reports/
│   ├── metrics/
│   └── history/
├── check
