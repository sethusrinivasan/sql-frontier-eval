/*
 ==============================================================================
 Query ID:         Q14_time_weighted_average_price_twap
 Title:            Time-Weighted Average Price (TWAP) with Variable Interval Weights
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 TWAP measures the average price of an asset weighted by the duration of time that each price level was sustained, preventing brief price spikes from distorting valuation.

 The Hidden Trap:
 Taking simple AVG(price) biases the result towards periods with frequent tick updates rather than sustained duration.

 The DuckDB Advantage:
 DuckDB LEAD functions cleanly calculate elapsed durations between price revisions.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE price_ticks (
                tick_time TIMESTAMP,
                symbol VARCHAR,
                price DOUBLE
            );
            INSERT INTO price_ticks VALUES
                ('2026-03-01 10:00:00', 'ETH', 3000.00), -- lasted 10 min
                ('2026-03-01 10:10:00', 'ETH', 3050.00), -- lasted 20 min
                ('2026-03-01 10:30:00', 'ETH', 3010.00), -- lasted 30 min
                ('2026-03-01 11:00:00', 'ETH', 3010.00); -- window end

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate 1-hour TWAP from 10:00 to 11:00
            WITH tick_durations AS (
                SELECT 
                    symbol,
                    tick_time,
                    price,
                    date_diff('second', tick_time, 
                        LEAD(tick_time, 1, TIMESTAMP '2026-03-01 11:00:00') OVER (PARTITION BY symbol ORDER BY tick_time)
                    ) AS duration_seconds
                FROM price_ticks
                WHERE tick_time < TIMESTAMP '2026-03-01 11:00:00'
            )
            SELECT 
                symbol,
                ROUND(SUM(price * duration_seconds) / SUM(duration_seconds), 2) AS twap_price,
                SUM(duration_seconds) AS total_duration_seconds
            FROM tick_durations
            GROUP BY symbol;
