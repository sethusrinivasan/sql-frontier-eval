/*
 ==============================================================================
 Query ID:         Q65_search_position_bias_dcg
 Title:            Discounted Cumulative Gain (DCG) with Search Position Bias Discount
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Users are far more likely to click the #1 search result than the #5 result regardless of relevance. Ranking quality is measured via Discounted Cumulative Gain: DCG = SUM(relevance / log2(rank + 1)).

 The Hidden Trap:
 Simple click counts reward poorly placed relevant items unfairly.

 The DuckDB Advantage:
 DuckDB math functions (`LOG2`) compute logarithmic rank discounts in vectorized window expressions.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE search_impressions (
                query_id INT,
                rank_position INT,
                relevance_label INT -- 0=irrelevant, 1=relevant, 2=perfect
            );
            INSERT INTO search_impressions VALUES
                (1, 1, 2), -- Rank 1: perfect match
                (1, 2, 0), -- Rank 2: bad match
                (1, 3, 1); -- Rank 3: good match

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate DCG@3 for query 1
            SELECT 
                query_id,
                ROUND(SUM(relevance_label / LOG2(rank_position + 1)), 4) AS dcg_at_3
            FROM search_impressions
            WHERE rank_position <= 3
            GROUP BY query_id;
