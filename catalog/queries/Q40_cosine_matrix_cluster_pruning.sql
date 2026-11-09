/*
 ==============================================================================
 Query ID:         Q40_cosine_matrix_cluster_pruning
 Title:            Pairwise Vector Similarity Self-Join with Coarse Cluster Pruning
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Finding all similar document pairs across 100,000 docs is O(N^2) (10 billion checks). Partitioning into coarse category buckets first reduces search to O(N * (N/K)).

 The Hidden Trap:
 Unpartitioned cross joins cause out-of-memory crashes on analytical engines.

 The DuckDB Advantage:
 DuckDB evaluates equi-join partition keys before computing array_cosine_similarity.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE corpus (
                doc_id INT,
                bucket_id INT,
                vector FLOAT[2]
            );
            INSERT INTO corpus VALUES
                (1, 10, [0.9, 0.1]::FLOAT[2]),
                (2, 10, [0.88, 0.12]::FLOAT[2]),
                (3, 20, [0.1, 0.9]::FLOAT[2]),
                (4, 20, [0.12, 0.88]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Pairwise similarity evaluated ONLY within shared bucket partitions
            SELECT 
                a.doc_id AS doc_a,
                b.doc_id AS doc_b,
                a.bucket_id,
                ROUND(array_cosine_similarity(a.vector, b.vector), 4) AS similarity
            FROM corpus a
            JOIN corpus b
              ON a.bucket_id = b.bucket_id
             AND a.doc_id < b.doc_id
            WHERE array_cosine_similarity(a.vector, b.vector) >= 0.85
            ORDER BY similarity DESC;
