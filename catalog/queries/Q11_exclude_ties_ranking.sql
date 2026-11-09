/*
 ==============================================================================
 Query ID:         Q11_exclude_ties_ranking
 Title:            Excluding Ties in Percentile Ranks via EXCLUDE TIES
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 When evaluating employee sales performance, ties should not inflate the percentile score against colleagues who achieved the exact same result.

 The Hidden Trap:
 Using standard RANK() causes tied individuals to push each other's percentiles higher or lower inconsistently.

 The DuckDB Advantage:
 DuckDB's `EXCLUDE TIES` window frame syntax accurately handles identical duplicate metrics.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE rep_sales (
                rep_id INT,
                sales_quota_achieved DECIMAL(5,2)
            );
            INSERT INTO rep_sales VALUES
                (1, 120.00),
                (2, 115.00),
                (3, 115.00), -- Tie
                (4, 95.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute cumulative sales sum excluding tied peers in current row calculation
            SELECT 
                rep_id,
                sales_quota_achieved,
                SUM(sales_quota_achieved) OVER (
                    ORDER BY sales_quota_achieved DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    EXCLUDE TIES
                ) AS cumulative_sales_exclusive_of_ties
            FROM rep_sales
            ORDER BY sales_quota_achieved DESC, rep_id;
