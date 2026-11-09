/*
 ==============================================================================
 Query ID:         Q27_euclidean_l2_nearest_neighbors
 Title:            L2 Euclidean Distance Nearest Neighbors Search via array_distance
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 In computer vision feature retrieval (facial recognition, product image matching), feature vectors are compared using Euclidean (L2) distance where lower distance equals higher visual similarity.

 The Hidden Trap:
 LLMs often try to write SQRT(SUM(POW(a - b, 2))) which prevents vectorized hardware acceleration.

 The DuckDB Advantage:
 DuckDB provides native `array_distance(a, b)` for Euclidean L2 metric calculation.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE image_features (
                image_id INT,
                label VARCHAR,
                vector FLOAT[3]
            );
            INSERT INTO image_features VALUES
                (101, 'Red Running Shoe',  [1.0, 2.0, 3.0]::FLOAT[3]),
                (102, 'Crimson Sneaker',   [1.1, 2.1, 2.9]::FLOAT[3]),
                (103, 'Blue Hiking Boot',  [5.0, 8.0, 9.0]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find visual nearest neighbors to query image vector [1.05, 2.05, 3.0]
            SELECT 
                image_id,
                label,
                ROUND(array_distance(vector, [1.05, 2.05, 3.0]::FLOAT[3]), 4) AS l2_distance
            FROM image_features
            ORDER BY l2_distance ASC
            LIMIT 2;
