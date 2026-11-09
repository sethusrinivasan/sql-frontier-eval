/*
 ==============================================================================
 Query ID:         Q94_median_absolute_deviation_mad
 Title:            Median Absolute Deviation (MAD) Robust Statistical Outlier Detection
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Traditional standard deviation Z-scores fail in the presence of extreme outliers because the outliers themselves distort the mean and standard deviation. MAD is a robust statistical scale estimator.

 The Hidden Trap:
 Mean and standard deviation break down completely on fat-tailed or skewed data distributions.

 The DuckDB Advantage:
 DuckDB can compute medians of deviations in standard analytical CTEs.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE payment_volumes (
                tx_id INT,
                amount DOUBLE
            );
            INSERT INTO payment_volumes VALUES
                (1, 10.0), (2, 12.0), (3, 11.0), (4, 13.0), (5, 12.0),
                (6, 1000.0); -- Massive outlier

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute Median Absolute Deviation (MAD) and flag robust outliers
            -- MAD = MEDIAN( |x - MEDIAN(x)| )
            WITH med AS (
                SELECT MEDIAN(amount) AS overall_median
                FROM payment_volumes
            ),
            deviations AS (
                SELECT 
                    p.tx_id,
                    p.amount,
                    m.overall_median,
                    ABS(p.amount - m.overall_median) AS abs_deviation
                FROM payment_volumes p
                CROSS JOIN med m
            ),
            mad_val AS (
                SELECT MEDIAN(abs_deviation) AS mad_score
                FROM deviations
            )
            SELECT 
                d.tx_id,
                d.amount,
                d.overall_median,
                ROUND(d.abs_deviation / NULLIF(v.mad_score, 0), 2) AS robust_mad_score,
                CASE 
                    WHEN (d.abs_deviation / NULLIF(v.mad_score, 0)) > 3.0 
                    THEN 'ROBUST_OUTLIER' 
                    ELSE 'NORMAL' 
                END AS anomaly_flag
            FROM deviations d
            CROSS JOIN mad_val v
            ORDER BY robust_mad_score DESC;
