/*
 ==============================================================================
 Query ID:         Q07_scd2_open_ended_intervals
 Title:            Slowly Changing Dimension Type 2 Join with Open-Ended Future
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Customers change addresses or account tiers over time. Joining historical orders to customer profile dimensions requires matching the order date to the active validity interval.

 The Hidden Trap:
 Current active records typically have `valid_to IS NULL`. A simple `order_date BETWEEN valid_from AND valid_to` drops all current active records.

 The DuckDB Advantage:
 DuckDB optimizes COALESCE null bounds directly into range filter pushdown.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE dim_customer_scd (
                customer_id INT,
                tier VARCHAR,
                valid_from DATE,
                valid_to DATE
            );
            CREATE TABLE fact_orders (
                order_id INT,
                customer_id INT,
                order_date DATE,
                amount DECIMAL(10,2)
            );
            INSERT INTO dim_customer_scd VALUES
                (88, 'Silver', '2026-01-01', '2026-02-01'),
                (88, 'Gold',   '2026-02-01', NULL);
            INSERT INTO fact_orders VALUES
                (1, 88, '2026-01-15', 100.00),
                (2, 88, '2026-02-20', 250.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Join fact orders to historical customer dimension without dropping active records
            SELECT 
                o.order_id,
                o.customer_id,
                o.order_date,
                o.amount,
                c.tier AS customer_tier_at_purchase
            FROM fact_orders o
            JOIN dim_customer_scd c
              ON o.customer_id = c.customer_id
             AND o.order_date >= c.valid_from
             AND o.order_date < COALESCE(c.valid_to, DATE '9999-12-31')
            ORDER BY o.order_id;
