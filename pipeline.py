import json
from extract import extract_and_save
from transform import flatten_events
from load import init_db, get_updated_after, start_run, upsert_events, finish_run
import datetime as dt
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path


DB_PATH = "earthquakes.db"
LOG_DIR = Path("logs")

logger = logging.getLogger(__name__)


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )
    formatter.converter = time.gmtime  # timestamps in UTC, like the data

    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = RotatingFileHandler(
        LOG_DIR / "pipeline.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    for handler in (console_handler, file_handler):
        handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])



def build_raw_filename(run_id):
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"events_run{run_id:04d}_{ts}.geojson"


def main():
    setup_logging()
    conn = init_db(DB_PATH)
    try:
        updated_after = get_updated_after(conn)
        run_id = start_run(conn, updated_after)
        logger.info("Run %d started (updatedafter=%s)", run_id, updated_after)

        try:
            params = {
                "format": "geojson", 
                "updatedafter" : updated_after, 
                "minmagnitude": 2.5, 
                "limit": 20000}
            file_name = build_raw_filename(run_id)
            text = extract_and_save(params, file_name)
            rows = flatten_events(json.loads(text))
            logger.info("Transformed %d events", len(rows))

            counts = upsert_events(conn, rows)
            finish_run(conn, run_id, "success", counts)
            logger.info("Run %d finished: %s", run_id, counts)
        except Exception as exc:
            logger.exception("Run %d failed", run_id)
            finish_run(conn, run_id, "failed", error=str(exc))
            raise
    finally:
        conn.close()



if __name__ == "__main__":
    main()