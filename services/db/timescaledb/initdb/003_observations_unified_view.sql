-- Unified read view: recent raw readings + hourly-averaged history.
--
-- Raw per-reading data only exists for the last 2 days (see
-- 002_observations_rollup.sql retention policy). Anything older is only
-- available as an hourly average in observations_hourly. This view stitches
-- the two together into the same column shape as the `observations` table
-- so existing queries/dashboards only need to change which table/view they
-- point at, not how they read `result_numeric`.
--
-- For historical (pre-cutoff) data, `result_numeric` is the hourly AVERAGE
-- for that datastream/hour (not min/max/last) per user preference - that is
-- the only value carried forward for old data.
CREATE OR REPLACE VIEW observations_unified AS
SELECT
    o.id,
    o.datastream_id,
    o.result_time,
    o.result_numeric,
    o.result_text,
    o.result_boolean,
    o.result_complex,
    o.parameters
FROM observations o
UNION ALL
SELECT
    NULL::uuid AS id,
    h.datastream_id,
    h.bucket AS result_time,
    h.avg_numeric AS result_numeric,
    NULL::text AS result_text,
    NULL::boolean AS result_boolean,
    NULL::json AS result_complex,
    NULL::json AS parameters
FROM observations_hourly h
-- Only pull in buckets older than the raw retention cutoff, so the same
-- hour isn't ever returned twice (once as raw rows, once as an average).
WHERE h.bucket < now() - interval '2 days';
