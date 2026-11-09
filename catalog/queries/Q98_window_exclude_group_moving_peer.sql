/*
 ==============================================================================
 Query ID:         Q98_window_exclude_group_moving_peer
 Title:            Window Peer Frame Exclusion: EXCLUDE GROUP for Clean Cross-Group Contrast
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 When comparing sales across product categories or dates, analysts want to compute the average of all other groups, strictly excluding the entire current group.

 The Hidden Trap:
 Computing group baselines without excluding the current group dilutes contrast in small sample sizes.

 The DuckDB Advantage:
 DuckDB fully supports SQL:2011 `EXCLUDE GROUP` window syntax.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE regional_orders (
                region VARCHAR,
                order_id INT,
                sale_amount DOUBLE
            );
            INSERT INTO regional_orders VALUES
                ('North', 1, 100.0),
                ('North', 2, 120.0),
                ('South', 3, 200.0),
                ('East',  4, 150.0);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute baseline average across other regions strictly excluding current region group
            SELECT 
                region,
                order_id,
                sale_amount,
                ROUND(AVG(sale_amount) OVER (
                    ORDER BY region
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    EXCLUDE GROUP
                ), 2) AS other_regions_baseline_avg
            FROM regional_orders
            ORDER BY region, order_id;
