/*
 ==============================================================================
 Query ID:         Q47_hierarchical_vector_coarse_fine
 Title:            Hierarchical Coarse-to-Fine Multi-Level Vector Filtering
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 In massive enterprise catalogs, searching 100 million items is accelerated by first matching high-level department embedding centroids, then searching specific item vectors inside matching departments.

 The Hidden Trap:
 Flat brute-force vector search over hundreds of millions of items consumes excessive compute.

 The DuckDB Advantage:
 DuckDB joins coarse department vectors directly to fine item vectors in a single query.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE departments (
                dept_id INT,
                dept_name VARCHAR,
                dept_centroid FLOAT[2]
            );
            CREATE TABLE items (
                item_id INT,
                dept_id INT,
                item_name VARCHAR,
                item_vector FLOAT[2]
            );
            INSERT INTO departments VALUES
                (1, 'Electronics', [0.9, 0.1]::FLOAT[2]),
                (2, 'Gardening',   [0.1, 0.9]::FLOAT[2]);
            INSERT INTO items VALUES
                (101, 1, 'Noise-canceling earphones', [0.92, 0.08]::FLOAT[2]),
                (102, 1, 'USB-C Cable',               [0.85, 0.15]::FLOAT[2]),
                (201, 2, 'Lawn Mower',                [0.12, 0.88]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find best matching department, then retrieve top items strictly within that department
            WITH top_dept AS (
                SELECT dept_id
                FROM departments
                ORDER BY array_cosine_similarity(dept_centroid, [0.95, 0.05]::FLOAT[2]) DESC
                LIMIT 1
            )
            SELECT 
                i.item_id,
                i.item_name,
                ROUND(array_cosine_similarity(i.item_vector, [0.95, 0.05]::FLOAT[2]), 4) AS fine_sim_score
            FROM items i
            JOIN top_dept d ON i.dept_id = d.dept_id
            ORDER BY fine_sim_score DESC;
