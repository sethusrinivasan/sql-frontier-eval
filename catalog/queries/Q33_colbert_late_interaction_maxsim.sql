/*
 ==============================================================================
 Query ID:         Q33_colbert_late_interaction_maxsim
 Title:            ColBERT Multi-Vector Late Interaction (MaxSim) in Pure SQL
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Advanced retrieval models (ColBERT / Sanity) represent queries and documents as collections of token vectors. Scoring computes MaxSim: for each query token, take the maximum cosine similarity across all document tokens, then sum.

 The Hidden Trap:
 Implementing late interaction typically requires specialized Python tensor pipelines.

 The DuckDB Advantage:
 DuckDB can compute multi-vector token interactions, grouping by query token and document ID in vectorized SQL.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE query_tokens (
                q_token_id INT,
                token_text VARCHAR,
                vec FLOAT[2]
            );
            CREATE TABLE doc_token_embeddings (
                doc_id INT,
                d_token_id INT,
                token_text VARCHAR,
                vec FLOAT[2]
            );
            -- Query: "fast database"
            INSERT INTO query_tokens VALUES
                (1, 'fast',     [1.0, 0.0]::FLOAT[2]),
                (2, 'database', [0.0, 1.0]::FLOAT[2]);
            -- Document 10: "quick relational store"
            INSERT INTO doc_token_embeddings VALUES
                (10, 1, 'quick',      [0.9, 0.1]::FLOAT[2]),
                (10, 2, 'relational', [0.1, 0.85]::FLOAT[2]),
                (10, 3, 'store',      [0.2, 0.7]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- ColBERT MaxSim calculation: SUM_q( MAX_d( sim(q, d) ) )
            WITH token_sims AS (
                SELECT 
                    q.q_token_id,
                    q.token_text AS q_token,
                    d.doc_id,
                    d.token_text AS d_token,
                    array_cosine_similarity(q.vec, d.vec) AS sim
                FROM query_tokens q
                CROSS JOIN doc_token_embeddings d
            ),
            max_sim_per_query_token AS (
                SELECT 
                    doc_id,
                    q_token_id,
                    MAX(sim) AS max_token_sim
                FROM token_sims
                GROUP BY doc_id, q_token_id
            )
            SELECT 
                doc_id,
                ROUND(SUM(max_token_sim), 4) AS colbert_maxsim_score
            FROM max_sim_per_query_token
            GROUP BY doc_id
            ORDER BY colbert_maxsim_score DESC;
