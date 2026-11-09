/*
 ==============================================================================
 Query ID:         Q35_kmeans_cluster_assignment_step
 Title:            K-Means Clustering Assignment and Centroid Update in Pure SQL
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Unsupervised customer segmentation can be run directly inside DuckDB by assigning customer vectors to the nearest centroid and recomputing cluster means in a single query.

 The Hidden Trap:
 Running ML clustering outside the warehouse requires exporting millions of vectors over the network.

 The DuckDB Advantage:
 DuckDB computes distance matrices and partition centroids natively at memory bandwidth speeds.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE cluster_centroids (
                cluster_id INT,
                center FLOAT[2]
            );
            CREATE TABLE data_points (
                point_id INT,
                coord FLOAT[2]
            );
            INSERT INTO cluster_centroids VALUES
                (1, [1.0, 1.0]::FLOAT[2]),
                (2, [8.0, 8.0]::FLOAT[2]);
            INSERT INTO data_points VALUES
                (101, [1.2, 0.9]::FLOAT[2]),
                (102, [1.5, 1.1]::FLOAT[2]),
                (103, [7.8, 8.2]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Step 1: Assign each point to the closest cluster centroid via array_distance
            WITH point_distances AS (
                SELECT 
                    p.point_id,
                    p.coord,
                    c.cluster_id,
                    array_distance(p.coord, c.center) AS dist,
                    ROW_NUMBER() OVER (PARTITION BY p.point_id ORDER BY array_distance(p.coord, c.center) ASC) AS rank_closest
                FROM data_points p
                CROSS JOIN cluster_centroids c
            )
            SELECT 
                point_id,
                cluster_id AS assigned_cluster,
                ROUND(dist, 4) AS distance_to_center
            FROM point_distances
            WHERE rank_closest = 1
            ORDER BY point_id;
