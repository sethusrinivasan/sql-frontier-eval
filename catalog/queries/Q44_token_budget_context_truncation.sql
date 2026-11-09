/*
 ==============================================================================
 Query ID:         Q44_token_budget_context_truncation
 Title:            Dynamic Context Window Token Budget Packing for LLM RAG
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 When assembling retrieved chunks for an LLM prompt, you have a strict token limit (e.g. 1,000 tokens). You must greedily pick highest-similarity chunks until the cumulative token sum would exceed the budget.

 The Hidden Trap:
 Picking a fixed LIMIT 10 can overflow LLM token limits or waste available prompt capacity.

 The DuckDB Advantage:
 DuckDB cumulative window sums (`SUM(token_count) OVER (...)`) cleanly enforce strict budgets.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE rag_candidate_chunks (
                chunk_id INT,
                token_count INT,
                vec FLOAT[2]
            );
            INSERT INTO rag_candidate_chunks VALUES
                (1, 400, [0.95, 0.05]::FLOAT[2]),
                (2, 350, [0.90, 0.10]::FLOAT[2]),
                (3, 400, [0.85, 0.15]::FLOAT[2]); -- Exceeds 1000 total budget

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Greedily pack chunks ordered by similarity up to strict 1,000 token budget
            WITH ranked_chunks AS (
                SELECT 
                    chunk_id,
                    token_count,
                    array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) AS score,
                    SUM(token_count) OVER (
                        ORDER BY array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) DESC
                    ) AS cumulative_tokens
                FROM rag_candidate_chunks
            )
            SELECT 
                chunk_id,
                token_count,
                cumulative_tokens,
                ROUND(score, 4) AS similarity_score
            FROM ranked_chunks
            WHERE cumulative_tokens <= 1000
            ORDER BY similarity_score DESC;
