/*
 ==============================================================================
 Query ID:         Q56_multi_field_weighted_scoring
 Title:            Multi-Field Weighted Full-Text Retrieval (Title 3x, Body 1x)
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 A match in a document title or product headline is far more indicative of relevance than a passing mention in the body text.

 The Hidden Trap:
 Concatenating title and body into a single column gives equal weight to all words.

 The DuckDB Advantage:
 DuckDB can evaluate independent field matches and combine them with linear weighting in SQL.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE product_posts (
                post_id INT,
                title VARCHAR,
                body VARCHAR
            );
            INSERT INTO product_posts VALUES
                (1, 'Wireless Noise Canceling Headphones', 'These over-ear headphones feature active noise cancelling technology.'),
                (2, 'Travel Accessories and Gadgets',     'A complete list of travel gear including a wireless charging pad and cables.'),
                (3, 'Coffee Brewing Machines',          'Best espresso makers and grinders for home brewing.');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Search for 'wireless headphones': Title matches weighted 3.0x, Body matches weighted 1.0x
            WITH scored AS (
                SELECT 
                    post_id,
                    title,
                    ROUND(
                        (CASE WHEN title ILIKE '%wireless%' THEN 3.0 ELSE 0.0 END) +
                        (CASE WHEN title ILIKE '%headphones%' THEN 3.0 ELSE 0.0 END) +
                        (CASE WHEN body ILIKE '%wireless%' THEN 1.0 ELSE 0.0 END) +
                        (CASE WHEN body ILIKE '%headphones%' THEN 1.0 ELSE 0.0 END), 2
                    ) AS multi_field_score
                FROM product_posts
            )
            SELECT 
                post_id,
                title,
                multi_field_score
            FROM scored
            WHERE multi_field_score > 0
            ORDER BY multi_field_score DESC;
