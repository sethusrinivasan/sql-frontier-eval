/*
 ==============================================================================
 Query ID:         Q95_robust_z_score_iqr_normalization
 Title:            Robust Z-Score Normalization using Median and Interquartile Range (IQR)
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Standardizing skewed metrics (like API response latency) for machine learning feature pipelines requires scaling by IQR (Q3 - Q1) rather than standard deviation.

 The Hidden Trap:
 Standard Z-score produces biased features when distributions have heavy tails.

 The DuckDB Advantage:
 DuckDB percentile functions (`QUANTILE_CONT`) compute exact quartiles in a single scan.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE response_times (
                request_id INT,
                latency_ms DOUBLE
            );
            INSERT INTO response_times VALUES
                (1, 45.0), (2, 50.0), (3, 52.0), (4, 48.0), (5, 300.0);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute robust IQR-normalized score: (x - Q2) / (Q3 - Q1)
            WITH quartiles AS (
                SELECT 
                    QUANTILE_CONT(latency_ms, 0.25) AS q1,
                    QUANTILE_CONT(latency_ms, 0.50) AS median_val,
                    QUANTILE_CONT(latency_ms, 0.75) AS q3
                FROM response_times
            )
            SELECT 
                r.request_id,
                r.latency_ms,
                ROUND((r.latency_ms - q.median_val) / NULLIF(q.q3 - q.q1, 0), 3) AS robust_iqr_z_score
            FROM response_times r
            CROSS JOIN quartiles q
            ORDER BY robust_iqr_z_score DESC;
