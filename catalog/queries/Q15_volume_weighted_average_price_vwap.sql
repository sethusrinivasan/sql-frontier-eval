/*
 ==============================================================================
 Query ID:         Q15_volume_weighted_average_price_vwap
 Title:            Intraday Volume-Weighted Average Price (VWAP) Resetting Daily
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 VWAP provides institutional traders the definitive benchmark price weighted by traded volume, resetting to zero at the start of every trading day.

 The Hidden Trap:
 Failing to partition by trading date mixes multi-day volume into the intraday numerator and denominator.

 The DuckDB Advantage:
 DuckDB calculates cumulative sums in a single pass without subqueries.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE market_trades (
                symbol VARCHAR,
                trade_time TIMESTAMP,
                price DOUBLE,
                volume INT
            );
            INSERT INTO market_trades VALUES
                ('AAPL', '2026-03-01 09:35:00', 180.00, 1000),
                ('AAPL', '2026-03-01 09:40:00', 181.00, 2000),
                ('AAPL', '2026-03-02 09:35:00', 182.00, 500); -- Next day reset

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Intraday continuous VWAP calculation
            SELECT 
                symbol,
                trade_time,
                price,
                volume,
                ROUND(
                    SUM(price * volume) OVER (
                        PARTITION BY symbol, CAST(trade_time AS DATE)
                        ORDER BY trade_time
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) / 
                    SUM(volume) OVER (
                        PARTITION BY symbol, CAST(trade_time AS DATE)
                        ORDER BY trade_time
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ), 2
                ) AS intraday_vwap
            FROM market_trades
            ORDER BY symbol, trade_time;
