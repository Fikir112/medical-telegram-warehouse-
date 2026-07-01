"""
Dagster pipeline orchestrating the full medical telegram warehouse pipeline:
scrape → load → dbt transform → yolo enrichment
"""

import subprocess
import sys
from pathlib import Path

from dagster import asset, AssetExecutionContext, Definitions, define_asset_job, AssetSelection

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


@asset(description="Scrape messages and images from Telegram medical channels")
def scraped_messages(context: AssetExecutionContext):
    context.log.info("Starting Telegram scrape...")
    result = subprocess.run(
        [PYTHON, str(PROJECT_ROOT / "src" / "scraper.py")],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Scraper failed: {result.stderr}")
    context.log.info("Scraping complete.")
    return {"status": "success"}


@asset(
    deps=[scraped_messages],
    description="Load scraped JSON files into PostgreSQL raw table"
)
def loaded_raw_data(context: AssetExecutionContext):
    context.log.info("Loading JSON into PostgreSQL...")
    result = subprocess.run(
        [PYTHON, str(PROJECT_ROOT / "src" / "load_to_postgres.py")],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Loader failed: {result.stderr}")
    context.log.info("Load complete.")
    return {"status": "success"}


@asset(
    deps=[loaded_raw_data],
    description="Run dbt models to build star schema"
)
def dbt_star_schema(context: AssetExecutionContext):
    context.log.info("Running dbt models...")
    dbt_path = PROJECT_ROOT / "medical_warehouse"
    dbt_exe = Path(PYTHON).parent / "dbt.exe"

    result = subprocess.run(
        [str(dbt_exe), "run", "--profiles-dir", "."],
        capture_output=True, text=True, cwd=str(dbt_path)
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        raise Exception(f"dbt run failed: {result.stderr}")

    # Also run tests
    test_result = subprocess.run(
        [str(dbt_exe), "test", "--profiles-dir", "."],
        capture_output=True, text=True, cwd=str(dbt_path)
    )
    context.log.info(test_result.stdout)
    context.log.info("dbt complete.")
    return {"status": "success"}


@asset(
    deps=[dbt_star_schema],
    description="Run YOLO object detection on downloaded images"
)
def yolo_enrichment(context: AssetExecutionContext):
    context.log.info("Running YOLO enrichment...")
    result = subprocess.run(
        [PYTHON, str(PROJECT_ROOT / "src" / "yolo_enrichment.py")],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        raise Exception(f"YOLO enrichment failed: {result.stderr}")
    context.log.info("YOLO enrichment complete.")
    return {"status": "success"}


# Define the full pipeline job
full_pipeline_job = define_asset_job(
    name="full_medical_warehouse_pipeline",
    selection=AssetSelection.all()
)

# Dagster definitions
defs = Definitions(
    assets=[scraped_messages, loaded_raw_data, dbt_star_schema, yolo_enrichment],
    jobs=[full_pipeline_job],
)