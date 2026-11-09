/*
 ==============================================================================
 Query ID:         Q23_trimmed_mean_rolling_window
 Title:            Outlier-Resistant Rolling Window (Trimmed Mean Aggregation)
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Financial risk models compute a 7-day rolling average excluding the highest and lowest single observations in each 7-day window to eliminate transient flash crashes.

 The Hidden Trap:
 Writing self-joins with sub-aggregations to filter min/max results in huge query execution trees.

 The DuckDB Advantage:
 DuckDB window functions compute rolling sum, min, and max in parallel O(1) passes.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE daily_settlement (
                trade_date DATE,
                settlement_amount DOUBLE
            );
            INSERT INTO daily_settlement VALUES
                ('2026-03-01', 50.0),
                ('2026-03-02', 52.0),
                ('2026-03-03', 500.0), -- Flash spike outlier
                ('2026-03-04', 51.0),
                ('2026-03-05', 49.0);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate trimmed rolling mean excluding min and max values within a 5-day window
            WITH windowed_stats AS (
                SELECT 
                    trade_date,
                    settlement_amount,
                    COUNT(*) OVER w AS win_count,
                    SUM(settlement_amount) OVER w AS win_sum,
                    MIN(settlement_amount) OVER w AS win_min,
                    MAX(settlement_amount) OVER w AS win_max
                FROM daily_settlement
                WINDOW w AS (ORDER BY trade_date ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING)
            )
            SELECT 
                trade_date,
                settlement_amount,
                -- Subtract min and max from sum and divide by (count - 2)
                CASE 
                    WHEN win_count > 2 THEN ROUND((win_sum - win_min - win_max) / (win_count - 2), 2)
                    ELSE settlement_amount
                END AS trimmed_mean_5d
            FROM windowed_stats
            ORDER BY trade_date;
