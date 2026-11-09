/*
 ==============================================================================
 Query ID:         Q20_interval_overlap_concurrency
 Title:            Peak Concurrent Workforce Capacity via Interval Overlap Scan
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Workforce managers must calculate maximum concurrent staffing levels from employee shift start and end times to ensure warehouse safety limits are never breached.

 The Hidden Trap:
 Pairwise self-joins between overlapping shifts blow up to O(N^2) complexity.

 The DuckDB Advantage:
 Transforming shifts into discrete (+1 start, -1 end) point events reduces peak concurrency calculation to a single O(N log N) streaming pass.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE staff_shifts (
                shift_id INT,
                worker_id INT,
                start_time TIMESTAMP,
                end_time TIMESTAMP
            );
            INSERT INTO staff_shifts VALUES
                (1, 101, '2026-03-01 08:00:00', '2026-03-01 12:00:00'),
                (2, 102, '2026-03-01 09:00:00', '2026-03-01 13:00:00'),
                (3, 103, '2026-03-01 10:00:00', '2026-03-01 11:30:00');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Transform start/end intervals into delta events and compute peak concurrent staffing
            WITH shift_events AS (
                SELECT start_time AS event_time, 1 AS delta FROM staff_shifts
                UNION ALL
                SELECT end_time AS event_time, -1 AS delta FROM staff_shifts
            ),
            running_occupancy AS (
                SELECT 
                    event_time,
                    SUM(delta) OVER (ORDER BY event_time, delta DESC) AS concurrent_workers
                FROM shift_events
            )
            SELECT 
                MAX(concurrent_workers) AS peak_concurrent_workers
            FROM running_occupancy;
