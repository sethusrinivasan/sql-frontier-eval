/*
 ==============================================================================
 Query ID:         Q08_hopping_sliding_time_buckets
 Title:            Hopping / Overlapping Window Aggregations via time_bucket
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Real-time surveillance monitors rolling 15-minute average latency stepped forward every 5 minutes (a hopping window).

 The Hidden Trap:
 Standard GROUP BY time_bucket only produces non-overlapping tumbling windows, missing cross-boundary bursts.

 The DuckDB Advantage:
 DuckDB can evaluate multi-frequency time_bucket queries combined with generate_series hops in memory.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE server_metrics (
                server_id VARCHAR,
                metric_time TIMESTAMP,
                cpu_utilization DOUBLE
            );
            INSERT INTO server_metrics VALUES
                ('web-01', '2026-03-01 10:02:00', 45.0),
                ('web-01', '2026-03-01 10:07:00', 78.0),
                ('web-01', '2026-03-01 10:12:00', 92.0),
                ('web-01', '2026-03-01 10:17:00', 60.0);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Generate 15-minute sliding windows stepped every 5 minutes (hopping window)
            WITH window_steps AS (
                SELECT UNNEST(generate_series(
                    TIMESTAMP '2026-03-01 10:00:00',
                    TIMESTAMP '2026-03-01 10:15:00',
                    INTERVAL '5 minutes'
                )) AS window_start
            )
            SELECT 
                w.window_start,
                w.window_start + INTERVAL '15 minutes' AS window_end,
                m.server_id,
                COUNT(m.cpu_utilization) AS sample_count,
                ROUND(AVG(m.cpu_utilization), 2) AS avg_cpu,
                MAX(m.cpu_utilization) AS peak_cpu
            FROM window_steps w
            JOIN server_metrics m
              ON m.metric_time >= w.window_start
             AND m.metric_time < w.window_start + INTERVAL '15 minutes'
            GROUP BY w.window_start, m.server_id
            ORDER BY w.window_start;
