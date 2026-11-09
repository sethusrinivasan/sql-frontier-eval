/*
 ==============================================================================
 Query ID:         Q01_asof_trade_quote_matching
 Title:            Tick-Level Trade Execution Matching via Native ASOF JOIN
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 In algorithmic trading, every buy or sell order must be evaluated against the most recent prevailing market quote. Standard relational equality joins fail because quotes and trades happen at irregular microsecond intervals.

 The Hidden Trap:
 LLMs typically write quadratic triangular self-joins (WHERE q.ts <= t.ts) or window functions with LAG/LAST_VALUE, which create massive memory spikes on high-frequency streams.

 The DuckDB Advantage:
 DuckDB native `ASOF JOIN` performs an O(N log M) binary search scan directly across partitioned timestamp indices without sorting intermediate cross products.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE quotes (
                quote_time TIMESTAMP,
                symbol VARCHAR,
                bid_price DOUBLE,
                ask_price DOUBLE
            );
            CREATE TABLE trades (
                trade_time TIMESTAMP,
                symbol VARCHAR,
                trade_id INT,
                executed_price DOUBLE,
                shares INT
            );
            INSERT INTO quotes VALUES
                ('2026-03-01 09:30:00.100', 'NVDA', 850.10, 850.25),
                ('2026-03-01 09:30:00.250', 'NVDA', 850.15, 850.30),
                ('2026-03-01 09:30:00.400', 'NVDA', 850.20, 850.35);
            INSERT INTO trades VALUES
                ('2026-03-01 09:30:00.150', 'NVDA', 101, 850.25, 100),
                ('2026-03-01 09:30:00.300', 'NVDA', 102, 850.30, 200),
                ('2026-03-01 09:30:00.450', 'NVDA', 103, 850.32, 150);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Match each executed trade with the latest market quote effective at that exact microsecond
            SELECT 
                t.trade_id,
                t.symbol,
                t.trade_time,
                t.executed_price,
                t.shares,
                q.quote_time AS prevailing_quote_time,
                q.bid_price,
                q.ask_price,
                -- Effective slippage calculation (difference between ask and executed price)
                ROUND(t.executed_price - q.ask_price, 4) AS slippage
            FROM trades t
            ASOF JOIN quotes q
              ON t.symbol = q.symbol
             AND t.trade_time >= q.quote_time
            ORDER BY t.trade_time;
