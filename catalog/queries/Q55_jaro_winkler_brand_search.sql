/*
 ==============================================================================
 Query ID:         Q55_jaro_winkler_brand_search
 Title:            Brand & Name Fuzzy Search via Jaro-Winkler Prefix Similarity
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 In e-commerce, users often mistype the suffixes of brand names ('Samsumg' vs 'Samsung'). Jaro-Winkler gives higher weight to prefix matches, making it ideal for proper names.

 The Hidden Trap:
 Standard Levenshtein treats mistakes at the start of a word the same as at the end.

 The DuckDB Advantage:
 DuckDB includes native `jaro_winkler_similarity(a, b)` returning normalized [0, 1] scores.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE brands (
                brand_id INT,
                brand_name VARCHAR
            );
            INSERT INTO brands VALUES
                (1, 'Samsung'),
                (2, 'Samsonite'),
                (3, 'Apple'),
                (4, 'Sony');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Match brand query 'Samsun' with threshold >= 0.85
            SELECT 
                brand_id,
                brand_name,
                ROUND(jaro_winkler_similarity(brand_name, 'Samsun'), 4) AS jaro_similarity
            FROM brands
            WHERE jaro_winkler_similarity(brand_name, 'Samsun') >= 0.85
            ORDER BY jaro_similarity DESC;
