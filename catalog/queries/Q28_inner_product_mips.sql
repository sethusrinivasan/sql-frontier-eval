/*
 ==============================================================================
 Query ID:         Q28_inner_product_mips
 Title:            Maximum Inner Product Search (MIPS) for Normalized Embeddings
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 For unit-normalized vectors (e.g. OpenAI text-embedding-3 or Cohere embeddings), cosine similarity is identical to the inner product (dot product), which executes even faster.

 The Hidden Trap:
 Re-normalizing vectors in every query wastes compute when embeddings are pre-normalized upon insertion.

 The DuckDB Advantage:
 DuckDB native `array_inner_product(a, b)` provides the fastest dot-product vector scoring path.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE product_catalog_vectors (
                product_id INT,
                product_name VARCHAR,
                norm_vector FLOAT[3]
            );
            INSERT INTO product_catalog_vectors VALUES
                (1, 'Ultra Laptop', [0.8, 0.6, 0.0]::FLOAT[3]),
                (2, 'Smart Phone',  [0.6, 0.8, 0.0]::FLOAT[3]),
                (3, 'Coffee Maker', [0.0, 0.0, 1.0]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- MIPS search for normalized user query vector [0.85, 0.52, 0.0]
            SELECT 
                product_id,
                product_name,
                ROUND(array_inner_product(norm_vector, [0.85, 0.52, 0.0]::FLOAT[3]), 4) AS dot_product_score
            FROM product_catalog_vectors
            ORDER BY dot_product_score DESC
            LIMIT 2;
