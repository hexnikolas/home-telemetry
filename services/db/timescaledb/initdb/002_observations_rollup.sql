-- Continuous aggregate + retention policy for the `observations` hypertable.
--
-- Raw readings are kept for 2 days (1 day requested + 1 day safety margin so the
-- continuous aggregate always has time to materialize a bucket before the raw
-- rows backing it are dropped). After that, only the hourly rollup survives.
--
-- NOTE: This file only runs automatically on a brand-new/empty DB volume
-- (docker-entrypoint-initdb.d scripts only execute once, on first init).
-- It was also applied manually to the already-running database.

-- Hourly rollup per datastream.
-- `last()` picks the most recent value in the bucket ordered by result_time,
-- which is the right choice for cumulative/monotonic metrics (e.g. Energy Total)
-- where averaging doesn't make sense.
CREATE MATERIALIZED VIEW IF NOT EXISTS observations_hourly
WITH (timescaledb.continuous) AS
SELECT
    datastream_id,
    time_bucket('1 hour', result_time) AS bucket,
    avg(result_numeric)   AS avg_numeric,
    min(result_numeric)   AS min_numeric,
    max(result_numeric)   AS max_numeric,
    count(result_numeric) AS sample_count,
    last(result_numeric, result_time) AS last_numeric
FROM observations
GROUP BY datastream_id, bucket
WITH NO DATA;

CREATE INDEX IF NOT EXISTS ix_observations_hourly_datastream_bucket
    ON observations_hourly (datastream_id, bucket DESC);

-- Keep the rollup up to date automatically: every 30 min, (re)materialize
-- the window from 3 days ago up to 1 hour ago (end_offset leaves the most
-- recent, still-filling-up hour bucket alone).
SELECT add_continuous_aggregate_policy('observations_hourly',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists => TRUE
);

-- Drop raw observation rows older than 2 days; the hourly rollup above
-- retains the historical avg/min/max/count/last for anything older.
SELECT add_retention_policy('observations', INTERVAL '2 days', if_not_exists => TRUE);
