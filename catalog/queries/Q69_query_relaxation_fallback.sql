/*
 ==============================================================================
 Query ID:         Q69_query_relaxation_fallback
 Title:            Zero-Result Search Query Relaxation (Strict AND -> Loose OR Fallback)
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 If a multi-word search query (e.g. 'ergonomic mechanical wireless split keyboard') returns zero results under strict AND matching, modern engines gracefully relax to OR matching.

 The Hidden Trap:
 Failing to return fallback results leads to user bounce and abandoned sessions.

 The DuckDB Advantage:
 DuckDB CTEs can check candidate counts and conditionally branch to relaxed OR queries.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE keyboard_catalog (
                id INT,
                title VARCHAR
            );
            INSERT INTO keyboard_catalog VALUES
                (1, 'Ergonomic Split Keyboard Wired'),
                (2, 'Mechanical Wireless Office Keyboard'),
                (3, 'Standard Membrane Keyboard');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Query tokens: 'ergonomic', 'mechanical', 'wireless'
            WITH scored_matches AS (
                SELECT 
                    id,
                    title,
                    (CASE WHEN title ILIKE '%ergonomic%' THEN 1 ELSE 0 END +
                     CASE WHEN title ILIKE '%mechanical%' THEN 1 ELSE 0 END +
                     CASE WHEN title ILIKE '%wireless%' THEN 1 ELSE 0 END) AS match_score
                FROM keyboard_catalog
            )
            SELECT 
                id,
                title,
                match_score,
                CASE WHEN match_score = 3 THEN 'STRICT_ALL_MATCH' ELSE 'RELAXED_PARTIAL_MATCH' END AS match_tier
            FROM scored_matches
            WHERE match_score >= 1
            ORDER BY match_score DESC, id;
