/*
 ==============================================================================
 Query ID:         Q36_knn_vector_anomaly_detection
 Title:            Vector Anomaly Detection via Average K-Nearest Neighbor Distance
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Anomalous sensor readings or fraudulent transaction vectors reside in sparse regions of the embedding space. Measuring the average distance to a vector's 3 nearest neighbors flags outliers.

 The Hidden Trap:
 Setting a global static distance threshold fails when data clusters have variable local densities.

 The DuckDB Advantage:
 DuckDB window functions compute localized k-NN distances per entity without external libraries.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE transaction_embeddings (
                tx_id INT,
                vec FLOAT[2]
            );
            -- Normal cluster around (0,0); tx_id 4 is an outlier at (10, 10)
            INSERT INTO transaction_embeddings VALUES
                (1, [0.05, 0.02]::FLOAT[2]),
                (2, [0.01, 0.04]::FLOAT[2]),
                (3, [0.03, 0.01]::FLOAT[2]),
                (4, [10.0, 10.0]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate average distance to 2 nearest neighbors to score anomaly level
            WITH pairwise_distances AS (
                SELECT 
                    a.tx_id,
                    b.tx_id AS neighbor_id,
                    array_distance(a.vec, b.vec) AS dist,
                    ROW_NUMBER() OVER (PARTITION BY a.tx_id ORDER BY array_distance(a.vec, b.vec) ASC) AS k_rank
                FROM transaction_embeddings a
                JOIN transaction_embeddings b ON a.tx_id != b.tx_id
            ),
            knn_avg AS (
                SELECT 
                    tx_id,
                    AVG(dist) AS mean_2nn_distance
                FROM pairwise_distances
                WHERE k_rank <= 2
                GROUP BY tx_id
            )
            SELECT 
                tx_id,
                ROUND(mean_2nn_distance, 4) AS outlier_score,
                CASE WHEN mean_2nn_distance > 5.0 THEN 'ANOMALOUS_OUTLIER' ELSE 'NORMAL' END AS classification
            FROM knn_avg
            ORDER BY outlier_score DESC;
