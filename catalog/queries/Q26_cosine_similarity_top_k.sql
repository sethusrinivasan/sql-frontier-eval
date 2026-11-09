/*
 ==============================================================================
 Query ID:         Q26_cosine_similarity_top_k
 Title:            Dense Vector Cosine Similarity Nearest Neighbors (Top-K ANN)
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 When a user asks a question in an AI assistant, the query is embedded into a dense vector (e.g. 4-dimensional here for illustration, or 384/1536 in prod). We retrieve the top most semantically relevant documentation chunks.

 The Hidden Trap:
 Models frequently try to calculate cosine similarity manually using dot product divided by norms in SQL, which is slow, verbose, and numerically unstable with zero vectors.

 The DuckDB Advantage:
 DuckDB has high-performance native SIMD-accelerated `array_cosine_similarity(a, b)` over fixed-size arrays `FLOAT[N]`.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE doc_embeddings (
                doc_id INT,
                title VARCHAR,
                embedding FLOAT[4]
            );
            INSERT INTO doc_embeddings VALUES
                (1, 'DuckDB Architecture Overview', [0.9, 0.1, 0.2, 0.0]::FLOAT[4]),
                (2, 'PostgreSQL Vacuum Internals',  [0.1, 0.8, 0.3, 0.1]::FLOAT[4]),
                (3, 'Vector Search & Embeddings',   [0.85, 0.15, 0.3, 0.05]::FLOAT[4]),
                (4, 'Kafka Event Streaming Guide',  [0.0, 0.2, 0.9, 0.4]::FLOAT[4]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find the top 2 documents closest to the query embedding [0.9, 0.1, 0.25, 0.0]
            WITH scored_docs AS (
                SELECT 
                    doc_id,
                    title,
                    embedding,
                    -- Native SIMD cosine similarity
                    array_cosine_similarity(embedding, [0.9, 0.1, 0.25, 0.0]::FLOAT[4]) AS cosine_score
                FROM doc_embeddings
            )
            SELECT 
                doc_id,
                title,
                ROUND(cosine_score, 4) AS similarity_score
            FROM scored_docs
            ORDER BY cosine_score DESC
            LIMIT 2;
