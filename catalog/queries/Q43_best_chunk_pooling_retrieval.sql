/*
 ==============================================================================
 Query ID:         Q43_best_chunk_pooling_retrieval
 Title:            Document-Level Aggregation with Best-Chunk Pooling in RAG
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Long PDF manuals are split into 50 chunks each. To avoid returning 5 chunks from the exact same PDF manual, we retrieve the best chunk per document and aggregate at the document level.

 The Hidden Trap:
 Returning raw chunk Top-K dominates the context window with duplicates from a single document.

 The DuckDB Advantage:
 DuckDB QUALIFY clause filters for the top chunk per document without nested CTEs.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE document_chunks (
                chunk_id INT,
                doc_id INT,
                doc_title VARCHAR,
                chunk_text VARCHAR,
                vec FLOAT[2]
            );
            INSERT INTO document_chunks VALUES
                (101, 1, 'Manual A', 'Setup guide section 1', [0.95, 0.1]::FLOAT[2]),
                (102, 1, 'Manual A', 'Setup guide section 2', [0.92, 0.15]::FLOAT[2]),
                (103, 2, 'Manual B', 'Troubleshooting section 1', [0.88, 0.2]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Retrieve the single highest-scoring chunk per document using QUALIFY
            SELECT 
                doc_id,
                doc_title,
                chunk_id,
                chunk_text,
                ROUND(array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]), 4) AS chunk_score
            FROM document_chunks
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY doc_id 
                ORDER BY array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) DESC
            ) = 1
            ORDER BY chunk_score DESC;
