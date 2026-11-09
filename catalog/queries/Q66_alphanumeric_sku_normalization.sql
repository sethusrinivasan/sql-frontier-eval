/*
 ==============================================================================
 Query ID:         Q66_alphanumeric_sku_normalization
 Title:            Alphanumeric SKU Matching with Punctuation & Case Invariance
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Customers search for model numbers in messy formats: 'wh-1000xm5', 'WH1000-XM5', 'wh 1000 xm5'. Robust search normalizes punctuation and whitespace before matching.

 The Hidden Trap:
 Exact string equality misses 90% of technical product searches due to hyphens and spaces.

 The DuckDB Advantage:
 DuckDB `regexp_replace` cleanses alphanumeric identifiers efficiently.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE inventory_skus (
                sku_id INT,
                raw_sku VARCHAR,
                product_title VARCHAR
            );
            INSERT INTO inventory_skus VALUES
                (1, 'WH-1000XM5/B', 'Sony Premium Wireless Headphones Black'),
                (2, 'AIR-MAX-90-W',  'Nike Air Max 90 White Sneaker');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Cleanse search query 'wh1000xm5b' by stripping non-alphanumeric characters
            SELECT 
                sku_id,
                raw_sku,
                product_title
            FROM inventory_skus
            WHERE lower(regexp_replace(raw_sku, '[^a-zA-Z0-9]', '', 'g')) = lower(regexp_replace('wh 1000-xm5/b', '[^a-zA-Z0-9]', '', 'g'));
