/*
 ==============================================================================
 Query ID:         Q09_ledger_balance_duplicate_timestamps
 Title:            Financial Ledger Cumulative Balance with Duplicate Timestamp Ties
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Ledger entries can occur at the exact same millisecond. Financial ledgers must preserve strict incremental balances rather than bunching peer rows.

 The Hidden Trap:
 SQL window functions default to `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which aggregates identical timestamps together into the same running total.

 The DuckDB Advantage:
 Explicit `ROWS BETWEEN` frames guarantee deterministic transaction-by-transaction cumulative balances.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE ledger (
                entry_id INT,
                account_id INT,
                posted_time TIMESTAMP,
                amount DECIMAL(10,2)
            );
            INSERT INTO ledger VALUES
                (1, 7001, '2026-03-01 14:00:00', 500.00),
                (2, 7001, '2026-03-01 14:00:00', -150.00), -- Duplicate timestamp
                (3, 7001, '2026-03-01 14:05:00', 200.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate strict running ledger balance using ROWS frame to prevent peer bunching
            SELECT 
                entry_id,
                account_id,
                posted_time,
                amount,
                -- ROWS frame evaluates row-by-row even when posted_time is identical
                SUM(amount) OVER (
                    PARTITION BY account_id
                    ORDER BY posted_time, entry_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS running_balance
            FROM ledger
            ORDER BY posted_time, entry_id;
