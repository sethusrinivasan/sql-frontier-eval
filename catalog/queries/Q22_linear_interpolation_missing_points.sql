/*
 ==============================================================================
 Query ID:         Q22_linear_interpolation_missing_points
 Title:            Bi-directional Linear Value Interpolation between Observations
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 When a sensor drops offline for 30 minutes, data scientists prefer linear interpolation between the last known reading and the next recovered reading rather than flat zero-filling.

 The Hidden Trap:
 Requires simultaneous look-behind (LAG) and look-ahead (LEAD) across varying time distances.

 The DuckDB Advantage:
 DuckDB calculates multi-point interpolation in a single query.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE pressure_readings (
                ts TIMESTAMP,
                psi DOUBLE
            );
            INSERT INTO pressure_readings VALUES
                ('2026-03-01 10:00:00', 100.0),
                ('2026-03-01 10:01:00', NULL),
                ('2026-03-01 10:02:00', NULL),
                ('2026-03-01 10:03:00', 130.0);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Linearly interpolate missing PSI values based on preceding and following known points
            WITH bounds AS (
                SELECT 
                    ts,
                    psi,
                    LAST_VALUE(psi IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS prev_psi,
                    LAST_VALUE(ts IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS prev_ts,
                    FIRST_VALUE(psi IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS next_psi,
                    FIRST_VALUE(ts IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS next_ts
                FROM pressure_readings
            )
            SELECT 
                ts,
                psi AS raw_psi,
                CASE 
                    WHEN psi IS NOT NULL THEN psi
                    ELSE ROUND(
                        prev_psi + (next_psi - prev_psi) * 
                        (date_diff('second', prev_ts, ts) * 1.0 / date_diff('second', prev_ts, next_ts)), 2
                    )
                END AS interpolated_psi
            FROM bounds
            ORDER BY ts;
