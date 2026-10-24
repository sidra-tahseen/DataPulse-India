# DataPulse India

**Open-source data quality monitoring for Indian government datasets.**

DataPulse India is a Python and React application that monitors the quality, freshness, volume, and reliability of open government data. It collects data from the Government of India's Open Government Data API, runs configurable quality checks, records monitoring reports, and presents results through an interactive dashboard.

## Features

- **Completeness checks:** Measure missing values in required fields, including empty strings and common missing-value markers.
- **Schema validation:** Check whether records contain the expected required fields.
- **Volume validation:** Compare the number of fetched records with the total reported by the source.
- **Freshness monitoring:** Track source update dates and classify dataset freshness.
- **Historical monitoring:** Save snapshots and reports to support comparisons over time.
- **Reliability metrics:** Record API request latency, status, success or failure, and retry attempts.
- **Record-level price history:** Track observations and detected price movements for the mandi price dataset.
- **Automated monitoring:** Run monitoring jobs through APScheduler.
- **Interactive dashboard:** Explore monitoring reports, trends, historical records, and dataset information using React and Recharts.
- **REST API:** Access monitoring results and history through FastAPI endpoints.

> **Scope note:** Required-field validation is not yet comprehensive schema-drift detection. Statistical anomaly detection and a unified 0–100 dataset health score are planned improvements, not current features.

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
                  |
                  v
         Quality checks
   completeness, schema, volume,
             freshness
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
│   └── vite.config.js
├── data/
│   ├── raw/
│   ├── reports/
│   ├── metrics/
│   └── history/
├── requirements.txt
├── .gitignore
└── README.md
```

Generated monitoring data and local secrets should remain outside version control.

## Getting started

### Prerequisites

- Python 3.12
- Node.js and npm
- A data.gov.in API key

### 1. Clone the repository

```bash
git clone https://github.com/sidra-tahseen/DataPulse-India.git
cd DataPulse-India
```

### 2. Set up the Python environment

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure the API key

Create a `.env` file in the project root:

```dotenv
DATAGOV_API_KEY=your_data_gov_in_api_key
```

Replace the placeholder with your own API key. Never commit `.env` or expose the key in frontend code, logs, screenshots, or public error messages.

### 4. Run the backend

From the project root:

```powershell
python -m uvicorn src.datapulse.api:app --reload --port 8000
```

The API runs locally at:

- API root: http://localhost:8000/
- Interactive API documentation: http://localhost:8000/docs

### 5. Run the frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173/ in your browser.

### 6. Run the tests

From the project root, with the Python environment activated:

```powershell
python -m pytest
```

Build the frontend for production:

```powershell
cd frontend
npm run build
```

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/datasets` | List registered datasets |
| `GET /api/health/latest` | Retrieve the latest monitoring report |
| `GET /api/health/history` | Retrieve historical monitoring reports |
| `GET /api/health/compare` | Compare the latest reports and snapshots |
| `GET /api/health/trends` | Retrieve historical quality trends |
| `GET /api/reliability` | Retrieve API reliability metrics |
| `POST /api/monitor/run` | Trigger a monitoring run |
| `GET /api/monitor/status` | Inspect monitoring and scheduler status |
| `GET /api/prices/history` | Retrieve saved mandi price observations |
| `GET /api/prices/changes` | Retrieve recorded mandi price movements |

Dataset-specific endpoints accept a `dataset_id` parameter where applicable. See `/docs` for request parameters and response schemas.

## Testing and validation

The project uses pytest for automated tests covering:

- Dataset comparison
- Freshness classification
- Ingestion retries and reliability recording
- Data quality checks
- Reliability metrics and summaries

Run the complete suite using `python -m pytest`. Report test results based on the latest actual run rather than assuming a fixed test count.

## Current limitations

- Only two datasets are registered.
- Schema checks validate required fields; comprehensive schema evolution and type-drift detection remain future work.
- Statistical anomaly detection and a unified dataset health score are not yet implemented.
- Monitoring snapshots, reports, price history, and metrics are stored locally. This is suitable for development but requires a persistence strategy for production deployment.
- Monitoring frequency and freshness thresholds need to be configured appropriately for each dataset.
- The frontend production build currently emits a large-bundle warning; code splitting can be explored as a performance improvement.

## Roadmap

1. Complete API-key redaction and regression tests for failure paths.
2. Deduplicate unchanged snapshots to reduce unnecessary storage.
3. Expand and validate the registry with additional curated government datasets.
4. Configure dataset-specific freshness thresholds and monitoring intervals.
5. Add statistical anomaly detection for suitable numeric fields.
6. Introduce a documented, tested dataset health score.
7. Add continuous integration with GitHub Actions.
8. Deploy the application with configurable CORS, environment-based API URLs, and persistent storage.
9. Collect real monitoring results over time to evaluate data quality and reliability trends.

## Contributing

Contributions are welcome. Before submitting changes, run the Python tests and build the frontend. Keep credentials and generated runtime data out of commits, and ensure that documentation reflects implemented functionality.

## License

See the repository's `LICENSE` file.
