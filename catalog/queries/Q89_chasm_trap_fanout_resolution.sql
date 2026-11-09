/*
 ==============================================================================
 Query ID:         Q89_chasm_trap_fanout_resolution
 Title:            Chasm Trap Resolution: Multi-Table 1:N Aggregation without Fan-Out Inflation
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 When an order has multiple discounts AND multiple shipment records, joining both child tables directly to the order creates a cross product that multiplies sales figures by 4x. Pre-aggregating each child table in CTEs before joining preserves financial integrity.

 The Hidden Trap:
 Frontier models routinely join all tables before GROUP BY, causing catastrophic silent metric corruption.

 The DuckDB Advantage:
 DuckDB can evaluate pre-aggregated CTEs in parallel vector pipelines with zero temp-table writes.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE orders (order_id INT, customer_id INT, base_amount DECIMAL(10,2));
            CREATE TABLE order_discounts (discount_id INT, order_id INT, amount DECIMAL(10,2));
            CREATE TABLE order_shipments (shipment_id INT, order_id INT, fee DECIMAL(10,2));
            INSERT INTO orders VALUES (101, 1, 100.00);
            INSERT INTO order_discounts VALUES (1, 101, 10.00), (2, 101, 5.00);
            INSERT INTO order_shipments VALUES (1, 101, 4.00),  (2, 101, 6.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Correctly aggregate discounts and shipments without fan-out inflation
            WITH agg_discounts AS (
                SELECT order_id, SUM(amount) AS total_discount
                FROM order_discounts
                GROUP BY order_id
            ),
            agg_shipments AS (
                SELECT order_id, SUM(fee) AS total_shipping
                FROM order_shipments
                GROUP BY order_id
            )
            SELECT 
                o.customer_id,
                SUM(o.base_amount) AS total_gross_sales,
                COALESCE(SUM(d.total_discount), 0.00) AS total_discount_amount,
                COALESCE(SUM(s.total_shipping), 0.00) AS total_shipping_fees,
                ROUND(SUM(o.base_amount) - COALESCE(SUM(d.total_discount), 0.00) + COALESCE(SUM(s.total_shipping), 0.00), 2) AS net_revenue
            FROM orders o
            LEFT JOIN agg_discounts d ON o.order_id = d.order_id
            LEFT JOIN agg_shipments s ON o.order_id = s.order_id
            GROUP BY o.customer_id;
