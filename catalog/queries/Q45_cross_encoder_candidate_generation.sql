/*
 ==============================================================================
 Query ID:         Q45_cross_encoder_candidate_generation
 Title:            Two-Stage Retrieval: Bi-Encoder Candidate Generation for Re-ranking
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Modern enterprise search uses a 2-stage pipeline: Fast bi-encoder vector search retrieves Top-50 candidates, which are then passed to a computationally heavy cross-encoder for final scoring.

 The Hidden Trap:
 Running heavy cross-encoder models across entire datasets is computationally impossible.

 The DuckDB Advantage:
 DuckDB can quickly filter millions of rows down to 50 candidates in milliseconds.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE knowledge_articles (
                article_id INT,
                category VARCHAR,
                vec FLOAT[2]
            );
            INSERT INTO knowledge_articles VALUES
                (1, 'tech', [0.9, 0.1]::FLOAT[2]),
                (2, 'tech', [0.8, 0.2]::FLOAT[2]),
                (3, 'hr',   [0.1, 0.9]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- First-stage candidate extraction: Top candidates in relevant category
            SELECT 
                article_id,
                category,
                ROUND(array_cosine_similarity(vec, [0.95, 0.05]::FLOAT[2]), 4) AS stage1_biencoder_score
            FROM knowledge_articles
            WHERE category = 'tech'
            ORDER BY stage1_biencoder_score DESC
            LIMIT 50;
