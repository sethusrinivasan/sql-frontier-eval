/*
 ==============================================================================
 Query ID:         Q29_pre_filter_vs_post_filter_trap
 Title:            The Pre-Filtering Trap: Relational Predicates with Vector Top-K
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 A user searches for 'cheap mechanical keyboard under $50'. If you run vector search Top-K first and filter by price afterwards (post-filtering), you may return zero products because all top-5 matches were $150 keyboards.

 The Hidden Trap:
 Post-filtering vector results breaks recall. Relational constraints (in-stock, price bounds, user tenant_id) must be evaluated as PRE-FILTERS before Top-K ranking.

 The DuckDB Advantage:
 DuckDB seamlessly pushes relational filters directly into the scan before computing expensive vector distances.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE inventory_items (
                item_id INT,
                name VARCHAR,
                price DECIMAL(10,2),
                in_stock BOOLEAN,
                vector FLOAT[3]
            );
            INSERT INTO inventory_items VALUES
                (1, 'Custom Mechanical Keyboard', 180.00, true,  [0.9, 0.1, 0.1]::FLOAT[3]),
                (2, 'Budget Gaming Keyboard',       45.00, true,  [0.85, 0.15, 0.1]::FLOAT[3]),
                (3, 'Cheap Office Keyboard',        25.00, true,  [0.8, 0.2, 0.1]::FLOAT[3]),
                (4, 'Out of Stock Keyboard',        35.00, false, [0.92, 0.1, 0.1]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Pre-filtered vector search: strictly in-stock and under $50 BEFORE ranking top 2
            SELECT 
                item_id,
                name,
                price,
                ROUND(array_cosine_similarity(vector, [0.9, 0.1, 0.1]::FLOAT[3]), 4) AS similarity
            FROM inventory_items
            WHERE in_stock = true
              AND price <= 50.00
            ORDER BY similarity DESC
            LIMIT 2;
