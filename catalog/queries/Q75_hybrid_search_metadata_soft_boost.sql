/*
 ==============================================================================
 Query ID:         Q75_hybrid_search_metadata_soft_boost
 Title:            Hybrid Search with Hard Categorical Filter & Soft Merchant Quality Boost
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Top marketplaces enforce strict hard filters (in-stock, prime shipping) while soft-boosting items based on merchant review rating: final_score = text_relevance * (1.0 + 0.1 * merchant_rating).

 The Hidden Trap:
 Hard-filtering by rating eliminates high-relevance new merchants with few reviews.

 The DuckDB Advantage:
 DuckDB combines hard boolean filtering with continuous multiplicative rating boosts.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE merchant_inventory (
                item_id INT,
                category VARCHAR,
                title VARCHAR,
                merchant_rating DOUBLE,
                is_available BOOLEAN
            );
            INSERT INTO merchant_inventory VALUES
                (1, 'Audio', 'Pro Studio Monitor Headphones', 4.9, true),
                (2, 'Audio', 'Budget Studio Headphones',       3.8, true),
                (3, 'Audio', 'Discontinued Vintage Headphones', 4.8, false);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Search 'Headphones' in 'Audio': Hard filter available=true, soft-boost by merchant rating
            WITH text_matches AS (
                SELECT 
                    item_id,
                    title,
                    merchant_rating,
                    -- Base relevance score from keyword matches
                    (CASE WHEN title ILIKE '%studio%' THEN 2.0 ELSE 1.0 END) AS base_relevance
                FROM merchant_inventory
                WHERE category = 'Audio'
                  AND is_available = true
                  AND title ILIKE '%Headphones%'
            )
            SELECT 
                item_id,
                title,
                merchant_rating,
                base_relevance,
                ROUND(base_relevance * (1.0 + (merchant_rating / 5.0) * 0.50), 2) AS boosted_final_score
            FROM text_matches
            ORDER BY boosted_final_score DESC;
