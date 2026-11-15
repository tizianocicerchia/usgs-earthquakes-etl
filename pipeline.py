import json
from extract import extract_and_save
from transform import flatten_events
from load import init_db, get_updated_after, start_run, upsert_events, finish_run
import datetime as dt

def build_raw_filename(run_id):
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"events_run{run_id:04d}_{ts}.geojson"

DB_PATH = "earthquakes.db"

def main():
    conn = init_db(DB_PATH)
    try:
        update_after = get_updated_after(conn)
        run_id = start_run(conn, update_after)

        try:
            params = {
                "format": "geojson", 
                "updatedafter" : update_after, 
                "minmagnitude": 2.5, 
                "limit": 20000}
            file_name = build_raw_filename(run_id)
            text = extract_and_save(params, file_name)
            data = flatten_events(json.loads(text))
            counts = upsert_events(conn, data)
            finish_run(conn, run_id, "success", counts)
            print(counts)
        except Exception as exc:
            finish_run(conn, run_id, "failed", error=str(exc))
            raise
    finally:
        conn.close()



if __name__ == "__main__":
    main()