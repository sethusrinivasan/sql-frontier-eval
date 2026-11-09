/*
 ==============================================================================
 Query ID:         Q30_adaptive_similarity_threshold
 Title:            Adaptive Similarity Thresholding with Fallback Top-K Guarantee
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 RAG systems want high-confidence matches (similarity > 0.85) to avoid hallucinations, but if no document exceeds 0.85, they need a guaranteed top-1 fallback to provide at least some context.

 The Hidden Trap:
 A hard WHERE similarity > 0.85 yields empty sets, while a raw LIMIT 5 includes irrelevant noise.

 The DuckDB Advantage:
 DuckDB window functions and conditional filtering allow hybrid thresholding in a single query.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE knowledge_base (
                kb_id INT,
                content VARCHAR,
                vector FLOAT[3]
            );
            INSERT INTO knowledge_base VALUES
                (1, 'DuckDB uses columnar storage', [0.4, 0.4, 0.1]::FLOAT[3]),
                (2, 'DuckDB vector execution engine', [0.5, 0.3, 0.2]::FLOAT[3]),
                (3, 'French cuisine recipes',        [0.0, 0.1, 0.9]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Score items, guarantee top 1 fallback even if below 0.85 threshold
            WITH scored AS (
                SELECT 
                    kb_id,
                    content,
                    array_cosine_similarity(vector, [0.9, 0.2, 0.1]::FLOAT[3]) AS sim_score,
                    ROW_NUMBER() OVER (ORDER BY array_cosine_similarity(vector, [0.9, 0.2, 0.1]::FLOAT[3]) DESC) AS rank_pos
                FROM knowledge_base
            )
            SELECT 
                kb_id,
                content,
                ROUND(sim_score, 4) AS sim_score,
                rank_pos,
                CASE WHEN sim_score >= 0.85 THEN 'CONFIDENT_MATCH' ELSE 'FALLBACK_TOP_MATCH' END AS match_type
            FROM scored
            WHERE sim_score >= 0.85 OR rank_pos = 1
            ORDER BY rank_pos;
