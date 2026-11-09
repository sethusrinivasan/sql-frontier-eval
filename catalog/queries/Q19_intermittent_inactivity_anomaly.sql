/*
 ==============================================================================
 Query ID:         Q19_intermittent_inactivity_anomaly
 Title:            Customer Churn Anomaly Detection vs Historical Purchase Rhythm
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 A customer who normally buys every 3 days is at risk if they haven't bought in 10 days. But a customer who buys quarterly is not. Churn detection must be personalized to each user's cadence.

 The Hidden Trap:
 Static 30-day churn thresholds misflag seasonal or low-frequency high-value customers.

 The DuckDB Advantage:
 DuckDB window functions compute user-specific median purchase intervals.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE orders_history (
                customer_id INT,
                order_date DATE
            );
            INSERT INTO orders_history VALUES
                (1, '2026-01-01'), (1, '2026-01-04'), (1, '2026-01-07'), -- Rhythm: 3 days
                (2, '2026-01-01'), (2, '2026-02-01'), (2, '2026-03-01'); -- Rhythm: 30 days

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate median inter-purchase days and compare against days elapsed since latest order
            WITH purchase_intervals AS (
                SELECT 
                    customer_id,
                    order_date,
                    order_date - LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS days_between
                FROM orders_history
            ),
            user_cadence AS (
                SELECT 
                    customer_id,
                    MAX(order_date) AS last_order_date,
                    MEDIAN(days_between) AS median_purchase_interval_days
                FROM purchase_intervals
                GROUP BY customer_id
            )
            SELECT 
                customer_id,
                last_order_date,
                median_purchase_interval_days,
                (DATE '2026-03-10' - last_order_date) AS days_since_last_order,
                CASE 
                    WHEN (DATE '2026-03-10' - last_order_date) > (2.5 * median_purchase_interval_days) 
                    THEN 'HIGH_CHURN_RISK' 
                    ELSE 'NORMAL' 
                END AS churn_risk_status
            FROM user_cadence
            ORDER BY customer_id;
