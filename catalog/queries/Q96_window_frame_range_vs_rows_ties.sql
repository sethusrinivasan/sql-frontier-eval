/*
 ==============================================================================
 Query ID:         Q96_window_frame_range_vs_rows_ties
 Title:            Financial Ledger Running Total: ROWS vs. RANGE Semantic Contrast
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 In financial auditing, understanding the exact behavioral difference between `ROWS BETWEEN` and `RANGE BETWEEN` prevents duplicate-timestamp errors from failing regulatory ledger reconciliations.

 The Hidden Trap:
 The ANSI SQL default for window frames with ORDER BY is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which aggregates identical peers together into one lump sum.

 The DuckDB Advantage:
 DuckDB provides explicit window execution options and deterministic ordering.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE audit_ledger (
                tx_id INT,
                val_date DATE,
                amount DECIMAL(10,2)
            );
            INSERT INTO audit_ledger VALUES
                (1, '2026-03-01', 100.00),
                (2, '2026-03-01', 50.00),  -- Same date!
                (3, '2026-03-02', 20.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compare the difference between default RANGE (peer bunching) vs ROWS (strict sequential)
            SELECT 
                tx_id,
                val_date,
                amount,
                -- Default RANGE behavior: bunches tied dates together ($150 on row 1 and 2)
                SUM(amount) OVER (
                    ORDER BY val_date
                    RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS bunched_range_total,
                -- Explicit ROWS behavior: increments strictly row by row ($100 then $150)
                SUM(amount) OVER (
                    ORDER BY val_date, tx_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS strict_rows_total
            FROM audit_ledger
            ORDER BY val_date, tx_id;
