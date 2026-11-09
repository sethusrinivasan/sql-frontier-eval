/*
 ==============================================================================
 Query ID:         Q93_list_lambdas_nested_json_arrays
 Title:            List Lambdas for High-Performance Nested Array Transformations
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Modern analytical warehouses store nested array payloads (e.g. array of discount percentages). Transforming or filtering elements directly inside the array without unnesting and re-aggregating saves massive compute.

 The Hidden Trap:
 Unnesting arrays to flat rows and re-aggregating with LIST() triggers expensive hash shuffles.

 The DuckDB Advantage:
 DuckDB list lambdas (`list_transform`, `list_filter`) execute in-place vectorized functions directly on array vectors.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE shopping_carts (
                cart_id INT,
                discounts_applied INT[],
                item_prices DOUBLE[]
            );
            INSERT INTO shopping_carts VALUES
                (1, [5, 15, 25], [100.0, 50.0, 20.0]),
                (2, [0, 10],     [200.0, 80.0]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Filter out discounts <= 5% and double remaining discount percentages using list lambdas
            SELECT 
                cart_id,
                discounts_applied AS raw_discounts,
                list_filter(discounts_applied, lambda x: x > 5) AS qualifying_discounts,
                list_transform(
                    list_filter(discounts_applied, lambda x: x > 5), 
                    lambda x: x * 2
                ) AS doubled_qualifying_discounts
            FROM shopping_carts
            ORDER BY cart_id;
