/*
 ==============================================================================
 Query ID:         Q53_min_max_convex_hybrid_search
 Title:            Min-Max Normalized Convex Combination Hybrid Search
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 An alternative to rank-based RRF is score-based fusion: min-max scale lexical scores to [0, 1] and vector scores to [0, 1], then take alpha * lexical + (1 - alpha) * vector.

 The Hidden Trap:
 Division by zero when all scores in a small result set are identical.

 The DuckDB Advantage:
 DuckDB NULLIF and window MIN/MAX cleanly handle degenerate score distributions.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE search_candidates (
                doc_id INT,
                title VARCHAR,
                raw_bm25 DOUBLE,
                vector_sim DOUBLE
            );
            INSERT INTO search_candidates VALUES
                (101, 'Data Warehousing Fundamentals', 25.0, 0.85),
                (102, 'Columnar Storage Internals',    10.0, 0.92),
                (103, 'SQL Query Optimization',         5.0, 0.70);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Min-Max normalization and 50/50 convex combination
            WITH bounds AS (
                SELECT 
                    doc_id,
                    title,
                    raw_bm25,
                    vector_sim,
                    MIN(raw_bm25) OVER () AS min_bm25,
                    MAX(raw_bm25) OVER () AS max_bm25,
                    MIN(vector_sim) OVER () AS min_vec,
                    MAX(vector_sim) OVER () AS max_vec
                FROM search_candidates
            ),
            normalized AS (
                SELECT 
                    doc_id,
                    title,
                    COALESCE((raw_bm25 - min_bm25) / NULLIF(max_bm25 - min_bm25, 0), 1.0) AS norm_bm25,
                    COALESCE((vector_sim - min_vec) / NULLIF(max_vec - min_vec, 0), 1.0) AS norm_vec
                FROM bounds
            )
            SELECT 
                doc_id,
                title,
                ROUND(norm_bm25, 4) AS norm_bm25,
                ROUND(norm_vec, 4) AS norm_vec,
                ROUND(0.50 * norm_bm25 + 0.50 * norm_vec, 4) AS convex_hybrid_score
            FROM normalized
            ORDER BY convex_hybrid_score DESC;
