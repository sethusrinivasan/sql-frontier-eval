/*
 ==============================================================================
 Query ID:         Q54_fuzzy_levenshtein_length_pruning
 Title:            Typo-Tolerant Search with Levenshtein Edit Distance & Length Bounds
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Users frequently misspell search terms (e.g. 'postgre' -> 'postgresql'). Levenshtein distance counts insertions, deletions, and substitutions.

 The Hidden Trap:
 Computing Levenshtein distance on every catalog word is CPU intensive without pre-filtering on string length (ABS(len_a - len_b) <= max_distance).

 The DuckDB Advantage:
 DuckDB pushes string length checks ahead of native `levenshtein()` evaluations.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE catalog_keywords (
                keyword_id INT,
                keyword VARCHAR
            );
            INSERT INTO catalog_keywords VALUES
                (1, 'postgresql'),
                (2, 'postgres'),
                (3, 'postgress'),
                (4, 'python'),
                (5, 'javascript');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find keywords within edit distance <= 2 of search query 'posgresql'
            SELECT 
                keyword_id,
                keyword,
                levenshtein(keyword, 'posgresql') AS edit_distance
            FROM catalog_keywords
            -- Pre-filter: word length cannot differ by more than max allowed edit distance (2)
            WHERE ABS(LENGTH(keyword) - LENGTH('posgresql')) <= 2
              AND levenshtein(keyword, 'posgresql') <= 2
            ORDER BY edit_distance ASC;
