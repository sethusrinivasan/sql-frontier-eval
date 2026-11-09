/*
 ==============================================================================
 Query ID:         Q57_exact_phrase_proximity_boost
 Title:            Exact Phrase Proximity Boosting in Keyword Retrieval
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 If a user searches for 'machine learning', an article containing the exact phrase 'machine learning' should rank higher than an article where 'machine' is in paragraph 1 and 'learning' is in paragraph 8.

 The Hidden Trap:
 Pure bag-of-words keyword matches ignore token proximity and phrase boundaries.

 The DuckDB Advantage:
 DuckDB combines exact phrase substring checks with token matching.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE articles_proximity (
                article_id INT,
                text_content VARCHAR
            );
            INSERT INTO articles_proximity VALUES
                (1, 'Recent breakthroughs in machine learning algorithms have transformed AI.'),
                (2, 'The washing machine broke down, so I am learning how to fix the belt.'),
                (3, 'Database indexing structures and query execution plans.');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Query: 'machine' AND 'learning', with a 5.0x boost for exact phrase match
            SELECT 
                article_id,
                text_content,
                (CASE WHEN text_content ILIKE '%machine%' THEN 1.0 ELSE 0.0 END +
                 CASE WHEN text_content ILIKE '%learning%' THEN 1.0 ELSE 0.0 END +
                 CASE WHEN text_content ILIKE '%machine learning%' THEN 5.0 ELSE 0.0 END) AS relevance_score
            FROM articles_proximity
            WHERE text_content ILIKE '%machine%' AND text_content ILIKE '%learning%'
            ORDER BY relevance_score DESC;
