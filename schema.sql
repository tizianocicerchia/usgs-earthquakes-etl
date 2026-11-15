CREATE TABLE IF NOT EXISTS earthquakes (
    id TEXT     PRIMARY KEY, 
    event_time  TEXT NOT NULL,
    place       TEXT, 
    type        TEXT,
    magnitude   REAL,
    tsunami     INTEGER CHECK (tsunami IN (0, 1)),
    status      TEXT,
    updated     TEXT NOT NULL,
    lat         REAL CHECK (lat BETWEEN -90 AND 90),
    lon         REAL CHECK (lon BETWEEN -180 AND 180),
    depth       REAL,
    loaded_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'))
);
    

CREATE INDEX IF NOT EXISTS idx_earthquakes_event_time ON earthquakes (event_time);
CREATE INDEX IF NOT EXISTS idx_earthquakes_updated    ON earthquakes (updated);


CREATE TABLE IF NOT EXISTS etl_runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    watermark_used  TEXT,
    rows_extracted  INTEGER,   
    rows_inserted   INTEGER,   
    rows_updated    INTEGER,   
    rows_skipped    INTEGER,   
    error_message   TEXT
);

