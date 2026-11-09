/*
 ==============================================================================
 Query ID:         Q91_dynamic_pivot_monthly_revenue
 Title:            Dynamic PIVOT of Monthly Revenue by Product Category
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Financial reporting requires transforming normalized long-form transaction rows into cross-tabulated wide financial matrices (Months along the top, Categories down the side).

 The Hidden Trap:
 Writing dozens of manual `CASE WHEN month = '2026-01' THEN amount ELSE 0 END` expressions is brittle and verbose.

 The DuckDB Advantage:
 DuckDB has first-class native `PIVOT` syntax.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE sales_facts (
                category VARCHAR,
                sale_month VARCHAR,
                revenue DECIMAL(10,2)
            );
            INSERT INTO sales_facts VALUES
                ('Electronics', '2026-01', 50000.00),
                ('Electronics', '2026-02', 65000.00),
                ('Apparel',     '2026-01', 30000.00),
                ('Apparel',     '2026-02', 32000.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Reshape monthly revenue into wide cross-tabulation using DuckDB PIVOT
            PIVOT sales_facts
            ON sale_month
            USING SUM(revenue)
            GROUP BY category
            ORDER BY category;
