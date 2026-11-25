# USGS Earthquakes ETL Pipeline

A small ETL pipeline in Python that downloads earthquake data from the USGS API, cleans it, and stores it in a SQLite database, loading only what is new or revised at each run.

This is a personal project built for learning purposes: its goal is to understand how an ETL pipeline works end to end (extraction, transformation, loading, incremental updates, run tracking, logging) using a simple, real-world example. It is intentionally small and not meant for production use.

**Current state:** the pipeline is complete and working as it is: it extracts, transforms and loads data incrementally, tracks every run and writes logs. It can be enriched in several ways (see [Possible improvements](#possible-improvements)), but nothing listed there is needed to run it.

## The data

The [USGS](https://earthquake.usgs.gov/) (United States Geological Survey) publishes data on earthquakes worldwide. It offers both static feeds (latest hour, day, week, month, optionally filtered by magnitude) and a query API, documented at https://earthquake.usgs.gov/fdsnws/event/1/. This project uses the query API, which allows filtering by date, magnitude, last update time and more.

An important property of this data: **events are revised over time**. An earthquake is first registered with an automatic estimate of magnitude, location and depth. Seismologists and algorithms then review it, so the magnitude can change by a few tenths and the location can shift. The same event, with the same identifier, therefore appears with different values at different moments.

This shapes the whole design: the pipeline must make sure that the database always contains the **latest version** of each event, without duplicates.

## Pipeline overview

```
                  updatedafter (watermark)
                 ┌──────────────────────────────────────────┐
                 │                                          │
USGS API ──► Extract ──► raw/ (GeoJSON) ──► Transform ──► Load ──► SQLite
                                                                   ├─ earthquakes
                                                                   └─ etl_runs
```

## How each stage works

### 1. Extract (`extract.py`)

Sends an HTTP request to the USGS API and saves the **unmodified response** in `raw/`. Query parameters (last update time, minimum magnitude, limit, ...) are passed as a dictionary. HTTP errors stop the run (`raise_for_status`).

Each raw file is named after the run that produced it and the time of the download (e.g. `events_run0005_20261115T170312Z.geojson`), so every API response is kept and can be traced back to a row of `etl_runs`.

Why keep the raw files? They are a record of exactly what the API returned: if a bug is found in the transformation, the data can be reprocessed without downloading it again.

### 2. Transform (`transform.py`)

Turns the nested GeoJSON into flat rows, one per event, keeping only the fields of interest (id, event time, last update, magnitude, place, type, status, tsunami flag, longitude, latitude, depth).

- USGS provides times as milliseconds since 1970 (Unix epoch). They are converted to **ISO 8601 timestamps in UTC with millisecond precision** (e.g. `2026-11-10T14:32:05.123+00:00`). The format is always the same length, so strings sort chronologically and can be compared directly, which the incremental logic relies on.
- Missing values (e.g. an event without magnitude) are kept as `None` instead of crashing the pipeline.

### 3. Load (`schema.sql`, `load.py`)

Rows are written to a SQLite database. The schema in `schema.sql` is part of the design:

- `id` is the **primary key**, so an event can exist only once.
- `NOT NULL` on the fields every event must have (`id`, `event_time`, `updated`), while `magnitude` is nullable because USGS sometimes does not provide it.
- `CHECK` constraints on longitude and latitude ranges. There are none on magnitude or depth, since negative values are legitimate for some events.
- Indexes on `event_time` and `updated`, the columns used for filtering and for the watermark.
- A `loaded_at` audit column with the time of the last write of each row.
- The schema uses `CREATE ... IF NOT EXISTS`, so it can be applied at every run.

Rows are written with an **upsert** (`INSERT ... ON CONFLICT(id) DO UPDATE`) inside a **single transaction**:

- If the event is new, it is inserted. If it already exists, it is updated.
- The update only happens if the incoming version is **more recent** (`excluded.updated > earthquakes.updated`): an older version never overwrites a newer one.
- The transaction is all-or-nothing: if the load fails halfway, it is rolled back and no partial data remains.

This makes the pipeline **idempotent**: running it several times on the same data leaves the database in the same state, and revised events replace their older versions.

For every load the pipeline counts how many rows were **inserted** (new events), **updated** (existing events with a newer version) and **skipped** (already up to date), so that `extracted = inserted + updated + skipped`.

### 4. Incremental loading with `updatedafter`

Downloading everything at each run would be wasteful. The `updatedafter` parameter of the API returns only the events created or modified after a given time, which is exactly what is needed to pick up new events and revisions of old ones. (Filtering by `starttime` would not work, because it refers to when the earthquake happened, not to when its data changed.)

The pipeline keeps a **watermark**: the latest `updated` value found in the database.

- **First run** (empty database): `updatedafter` is set to 7 days before the run.
- **Following runs**: `updatedafter` is the watermark, `SELECT MAX(updated) FROM earthquakes`. The load is atomic, so the table only contains data from successful runs, and a failed run is simply retried from the same point.

Observed behaviour: the API includes the event whose `updated` is exactly equal to the watermark, so one already-loaded event comes back at every run and is counted as `skipped`. This overlap is intentional and harmless: with an idempotent upsert it guarantees that no event is lost, at the cost of re-reading one row.

### 5. Orchestration and run tracking (`pipeline.py`)

`pipeline.py` only decides the order of the steps; the logic lives in the modules. Every run is recorded in the `etl_runs` table:

1. A row with status `running` is inserted and **committed immediately**.
2. Extract, transform and load run. The load has its own transaction.
3. The row is updated with `success` and the counters, or with `failed` and the error message (the exception is then re-raised, so the failure is not silent).

Keeping the run record outside the transaction of the data is deliberate: if the load fails and is rolled back, the `failed` record survives. A row left in `running` means the process did not finish (for example, it crashed).

### 6. Logging

The standard `logging` module writes the progress of each run (parameters of the request, size of the saved file, number of events, final counters) and, in case of errors, the full traceback. Messages go to the console and to `logs/pipeline.log`, which is rotated when it reaches about 1 MB (three old copies are kept). Timestamps are in UTC, like the data.

Logging and `etl_runs` complement each other: the table is a structured summary of every run that can be queried with SQL, the log is the detailed account of what happened inside it.

## Technical choices

- **SQLite**: it is part of Python's standard library (`sqlite3`), requires no installation or server, and anyone can clone the repository and run the project immediately. For a small learning project this is the right trade-off. The limits are the weak typing of dates (stored as ISO 8601 text) and the lack of concurrent writers; a production system would use a server database such as PostgreSQL.
- **Plain Python and `requests`**: no orchestration framework, to keep every step visible. In a real setting a scheduler such as Airflow or cron would run the pipeline.
- **Raw files on disk**: simple and enough for this scale. A real system would use object storage.

## Verification

The behaviour was checked by hand against the real API:

- The number of events loaded in the first run matches the count returned by the API `count` endpoint for the same time window.
- A second run only receives the overlapping event and counts it as `skipped`. The number of rows in `earthquakes` equals the sum of `rows_inserted` in `etl_runs`.
- All timestamp columns have the same length, which confirms that the formats are consistent.
- An invalid query parameter makes the API respond with `400`: the run is recorded as `failed` with the error message and no data is written.

Automated tests currently cover the transform stage (timestamp conversion, flattening of events, field values, missing magnitude).

## Known limitations

- **No pagination, and no explicit guard against truncation.** The API limits a single query to 20,000 events and the pipeline makes one request per run. With the small time windows used here (a few hundred events per day) this does not happen, but a run that needed more events could fail or return a truncated result, and since the watermark moves forward, the missing events could be skipped.
- **Filters apply to the current version of an event.** If an event is revised from magnitude 2.6 to 2.4, the API stops returning it when `minmagnitude=2.5`, and the database keeps the old version. Events deleted by USGS are not removed from the database either.
- **No retries**: a transient network error fails the run, which is picked up again at the next execution (the watermark has not moved).
- **The load stage has no automated tests yet**.
- **Parameters are set in the code** (`pipeline.py`, `load.py`), not from the command line.


## Project structure

```
.
├── extract.py        # download from the USGS API, save the raw response
├── transform.py      # flatten GeoJSON, convert timestamps
├── load.py           # database init, watermark, upsert, run tracking
├── schema.sql        # table definitions (earthquakes, etl_runs)
├── pipeline.py       # runs the stages in order, sets up logging
├── raw/              # raw API responses (not versioned)
├── logs/             # log files (not versioned)
├── tests/
└── requirements.txt
```

## Running the project

Developed with Python 3.13.

```bash
pip install -r requirements.txt
python pipeline.py
```

This creates `earthquakes.db` on the first run. To inspect it:

```bash
sqlite3 earthquakes.db "SELECT * FROM etl_runs;"
sqlite3 earthquakes.db "SELECT id, event_time, magnitude, place FROM earthquakes ORDER BY event_time DESC LIMIT 10;"
```

## Tests

```bash
pytest
```
