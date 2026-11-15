import datetime as dt
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql" 
DEFAULT_LOOKBACK_DAYS = 7

# Main query: insert values and manage ID conflict by updating with the latest value (based on "updated")
UPSERT_SQL = """
INSERT INTO earthquakes
    (id, event_time, updated, magnitude, place, type, status, tsunami, lon, lat, depth)
VALUES
    (:id, :event_time, :updated, :magnitude, :place, :type, :status, :tsunami, :lon, :lat, :depth)
ON CONFLICT(id) DO UPDATE SET
    event_time = excluded.event_time,
    updated    = excluded.updated,
    magnitude  = excluded.magnitude,
    place      = excluded.place,
    type       = excluded.type,
    status     = excluded.status,
    tsunami    = excluded.tsunami, 
    lon        = excluded.lon,
    lat        = excluded.lat,
    depth      = excluded.depth,
    loaded_at  = strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')
WHERE excluded.updated > earthquakes.updated
"""


# ISO date in the same format of transform.py
def utc_now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


# Create connection to SQLite file and execute schema.sql (create tables and indices if they do not exist)
def init_db(db_path):
    conn = sqlite3.connect(db_path) 
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8")) 
    return conn


# Watermark of the last loaded data, or 'now - 7 days' on the first run
def get_updated_after(conn, now=None):
    watermark = conn.execute("SELECT MAX(updated) FROM earthquakes").fetchone()[0]
    if watermark is not None:
        return watermark
    now = now or dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS)
    return start.isoformat(timespec="milliseconds")


def start_run(conn, updatedafter_used):
    cur = conn.execute(
        "INSERT INTO etl_runs (started_at, status, updatedafter_used) VALUES (?, 'running', ?)",
        (utc_now_iso(), updatedafter_used),
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id, status, counts=None, error=None):
    counts = counts or {}
    conn.execute(
        """
        UPDATE etl_runs
        SET finished_at = ?, status = ?, rows_extracted = ?, rows_inserted = ?,
            rows_updated = ?, rows_skipped = ?, error_message = ?
        WHERE run_id = ?
        """,
        (
            utc_now_iso(), status,
            counts.get("extracted"), counts.get("inserted"),
            counts.get("updated"), counts.get("skipped"),
            error, run_id,
        ),
    )
    conn.commit()


# Upsert rows in a single transaction. Returns the counters for etl_runs
def upsert_events(conn, rows):
    if not rows:
        return {"extracted": 0, "inserted": 0, "updated": 0, "skipped": 0}

    with conn:  # commit on success, rollback on exception
        n_before = conn.execute("SELECT COUNT(*) FROM earthquakes").fetchone()[0]
        cur = conn.executemany(UPSERT_SQL, rows)
        n_after = conn.execute("SELECT COUNT(*) FROM earthquakes").fetchone()[0]

    written = cur.rowcount  # inserted + updated (skipped rows are not counted)
    inserted = n_after - n_before
    return {
        "extracted": len(rows),
        "inserted": inserted,
        "updated": written - inserted,
        "skipped": len(rows) - written,
    }