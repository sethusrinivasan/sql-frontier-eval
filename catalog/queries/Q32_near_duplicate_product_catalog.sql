/*
 ==============================================================================
 Query ID:         Q32_near_duplicate_product_catalog
 Title:            Multi-Merchant Near-Duplicate Catalog Resolution with Price Consistency
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Marketplaces aggregate catalogs from thousands of sellers. Matching identical items requires high semantic vector similarity AND compatible price bounds (e.g. price within 20%).

 The Hidden Trap:
 Vector similarity alone matches accessories to main products; price filtering alone matches unrelated items.

 The DuckDB Advantage:
 DuckDB combines vector math and arithmetic bounds in a single joint execution predicate.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE merchant_catalog (
                sku_id INT,
                merchant VARCHAR,
                title VARCHAR,
                price DECIMAL(10,2),
                vector FLOAT[3]
            );
            INSERT INTO merchant_catalog VALUES
                (1, 'Merchant A', 'Sony WH-1000XM5 Noise-Cancelling Headphones', 349.99, [0.95, 0.1, 0.05]::FLOAT[3]),
                (2, 'Merchant B', 'Sony WH1000XM5 Wireless Headset - Black',     339.00, [0.94, 0.12, 0.04]::FLOAT[3]),
                (3, 'Merchant C', 'Sony Headphone Replacement Ear Cushions',       29.99, [0.88, 0.2, 0.1]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Match identical product listings across merchants (high similarity + price within 20%)
            SELECT 
                a.sku_id AS sku_a,
                a.merchant AS merchant_a,
                a.title AS title_a,
                b.sku_id AS sku_b,
                b.merchant AS merchant_b,
                b.title AS title_b,
                ROUND(array_cosine_similarity(a.vector, b.vector), 4) AS similarity,
                ROUND(ABS(a.price - b.price) / a.price * 100, 1) AS price_difference_pct
            FROM merchant_catalog a
            JOIN merchant_catalog b
              ON a.sku_id < b.sku_id
             AND a.merchant != b.merchant
             AND array_cosine_similarity(a.vector, b.vector) >= 0.90
             AND ABS(a.price - b.price) <= (0.20 * a.price)
            ORDER BY similarity DESC;
