
import json
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.datapulse.datasets import get_dataset, list_datasets
from src.datapulse.price_history import (
    get_price_history,
    get_price_changes,
)
from src.datapulse.reliability import get_reliability_summary


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

monitor_lock = threading.Lock()
scheduler = BackgroundScheduler(timezone="UTC")

monitor_status = {
    "running": False,
    "last_started_at": None,
    "last_completed_at": None,
    "last_result": "Not run since API startup",
    "last_error": None,
    "last_dataset_id": None,
}


def get_reports(dataset_id="rainfall_surat"):
    """Return reports belonging to one dataset."""
    get_dataset(dataset_id)

    if not REPORTS_DIR.exists():
        return []

    return sorted(
        REPORTS_DIR.glob(f"health_report_{dataset_id}_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def read_latest_report(dataset_id="rainfall_surat"):
    reports = get_reports(dataset_id)

    if not reports:
        return None

    with reports[0].open("r", encoding="utf-8") as file:
        return json.load(file)


def execute_monitor(dataset_id="rainfall_surat"):
    """Run monitoring for the selected dataset."""
    get_dataset(dataset_id)

    if not monitor_lock.acquire(blocking=False):
        return False, "Another monitoring run is already in progress."

    monitor_status["running"] = True
    monitor_status["last_started_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    monitor_status["last_dataset_id"] = dataset_id

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.datapulse.monitor",
                "--dataset",
                dataset_id,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            import logging

            logging.getLogger(__name__).error(
                "Monitoring subprocess failed for dataset=%s, exit_code=%s",
                dataset_id,
                result.returncode,
            )
            error = "Monitoring run failed. Check the backend logs for details."
            monitor_status["last_result"] = "FAILED"
            monitor_status["last_error"] = error
            return False, error

        monitor_status["last_result"] = "SUCCESS"
        monitor_status["last_error"] = None
        return True, result.stdout

    except subprocess.TimeoutExpired:
        error = "Monitoring run timed out."
        monitor_status["last_result"] = "FAILED"
        monitor_status["last_error"] = error
        return False, error

    except OSError as exc:
        import logging

        logging.getLogger(__name__).error(
            "Could not start monitoring subprocess: %s",
            type(exc).__name__,
        )
        error = "Could not start the monitoring process."
        monitor_status["last_result"] = "FAILED"
        monitor_status["last_error"] = error
        return False, error
    finally:
        monitor_status["running"] = False
        monitor_status["last_completed_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        monitor_lock.release()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for dataset in list_datasets():
        scheduler.add_job(
            execute_monitor,
            "interval",
            minutes=15,
            kwargs={"dataset_id": dataset["id"]},
            id=f"monitor_{dataset['id']}",
            replace_existing=True,
        )

    scheduler.start()
    print("Automatic monitoring scheduled every 15 minutes.")

    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title="DataPulse India API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://data-pulse-india.vercel.app",],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "DataPulse India API is running"}


@app.get("/api/datasets")
def datasets():
    return {"datasets": list_datasets()}


@app.get("/api/health/latest")
def latest_report(
    dataset_id: str = Query(default="rainfall_surat"),
):
    try:
        get_dataset(dataset_id)
        report = read_latest_report(dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the latest monitoring report.",
        ) from exc

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No monitoring reports found for this dataset. "
                "Run the monitor first."
            ),
        )

    return report


@app.get("/api/health/history")
def report_history(
    dataset_id: str = Query(default="rainfall_surat"),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        reports = get_reports(dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    history = []

    for path in reports[:limit]:
        try:
            with path.open("r", encoding="utf-8") as file:
                report = json.load(file)

            history.append({
                "filename": path.name,
                "report": report,
            })
        except (OSError, json.JSONDecodeError):
            continue

    return {
        "count": len(history),
        "history": history,
    }


@app.post("/api/monitor/run")
def run_monitor(
    dataset_id: str = Query(default="rainfall_surat"),
):
    try:
        get_dataset(dataset_id)
        success, output = execute_monitor(dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if not success:
        raise HTTPException(
            status_code=500,
            detail=output,
        )

    try:
        report = read_latest_report(dataset_id)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the generated report.",
        ) from exc

    if report is None:
        raise HTTPException(
            status_code=500,
            detail="Monitor completed, but no report was found.",
        )

    return {
        "message": "Monitoring completed successfully.",
        "report": report,
    }


@app.get("/api/monitor/status")
def get_monitor_status():
    jobs = []

    for dataset in list_datasets():
        job = scheduler.get_job(f"monitor_{dataset['id']}")

        jobs.append({
            "dataset_id": dataset["id"],
            "scheduled": job is not None,
            "next_scheduled_run": (
                job.next_run_time.isoformat()
                if job and job.next_run_time
                else None
            ),
        })

    default_job = scheduler.get_job("monitor_rainfall_surat")

    return {
        **monitor_status,
        "schedule_interval_minutes": 15,
        "next_scheduled_run": (
            default_job.next_run_time.isoformat()
            if default_job and default_job.next_run_time
            else None
        ),
        "jobs": jobs,
    }


@app.get("/api/health/compare")
def compare_health(
    dataset_id: str = Query(default="rainfall_surat"),
):
    try:
        get_dataset(dataset_id)

        from src.datapulse.compare import (
            load_latest_reports,
            load_latest_snapshots,
            compare_reports,
            compare_snapshots,
        )

        config = get_dataset(dataset_id)

        # Health reports are generated on each monitoring run.
        previous_report, current_report = load_latest_reports(dataset_id)

        health_result = compare_reports(
            previous_report,
            current_report,
        )

        # Snapshots are saved only when dataset content changes, so there
        # may not yet be two distinct snapshots to compare.
        try:
            previous_snapshot, current_snapshot = load_latest_snapshots(
                dataset_id
            )

            record_changes = compare_snapshots(
                previous_snapshot,
                current_snapshot,
                key_fields=tuple(config["key_fields"]),
            )
            snapshot_status = "COMPARISON_AVAILABLE"

        except ValueError:
            record_changes = {
                "status": "INSUFFICIENT_HISTORY",
                "message": (
                    "Not enough distinct snapshots are available "
                    "to compare dataset records yet."
                ),
                "added_count": 0,
                "removed_count": 0,
                "modified_count": 0,
                "added": [],
                "removed": [],
                "modified": [],
                "price_changes": [],
                "price_increases": 0,
                "price_decreases": 0,
            }
            snapshot_status = "INSUFFICIENT_HISTORY"

        return {
            "dataset": current_report.get("dataset", "Unknown"),
            "dataset_id": dataset_id,
            "previous_checked_at": previous_report.get("checked_at"),
            "current_checked_at": current_report.get("checked_at"),
            "changes": health_result["changes"],
            "alerts": health_result["alerts"],
            "snapshot_status": snapshot_status,
            "record_changes": record_changes,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not compare the latest health reports "
                "and snapshots."
            ),
        ) from exc


@app.get("/api/health/trends")
def health_trends(
    dataset_id: str = Query(default="rainfall_surat"),
):
    try:
        reports = list(reversed(get_reports(dataset_id)))
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    trends = []

    for path in reports:
        try:
            with path.open("r", encoding="utf-8") as file:
                report = json.load(file)

            metrics = report.get("health_metrics", {})

            trends.append({
                "checked_at": report.get("checked_at"),
                "completeness_percent": metrics.get(
                    "completeness_percent"
                ),
                "missing_values": metrics.get("missing_values"),
                "source_age_days": metrics.get("age_days"),
                "freshness_status": metrics.get("freshness_status"),
            })

        except (OSError, json.JSONDecodeError):
            continue

    return {
        "count": len(trends),
        "trends": trends,
    }


@app.get("/api/reliability")
def get_reliability(
    dataset_id: str = Query(default="rainfall_surat"),
):
    try:
        get_dataset(dataset_id)
        metrics = get_reliability_summary(dataset_id=dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "dataset_id": dataset_id,
        "metrics": metrics,
    }


@app.get("/api/prices/history")
def price_history(
    limit: int = Query(default=100, ge=1, le=500),
):
    """Return saved mandi price observations."""
    try:
        observations = get_price_history(limit=limit)

        return {
            "dataset_id": "mandi_prices",
            "count": len(observations),
            "observations": observations,
        }

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read mandi price history.",
        ) from exc


@app.get("/api/prices/changes")
def price_changes(
    limit: int = Query(default=100, ge=1, le=500),
):
    """Return recorded mandi price movements."""
    try:
        changes = get_price_changes(limit=limit)

        return {
            "dataset_id": "mandi_prices",
            "count": len(changes),
            "changes": changes,
        }

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read mandi price changes.",
        ) from exc
