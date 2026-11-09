/*
 ==============================================================================
 Query ID:         Q46_temporal_embedding_drift
 Title:            Temporal Semantic Drift Tracking across Document Embedding Centroids
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 As companies evolve, the meaning of terms like 'security' or 'remote work' shifts. Tracking the cosine distance between monthly embedding centroids reveals semantic concept drift.

 The Hidden Trap:
 Ignoring semantic drift causes older documentation to silently diverge from current employee search queries.

 The DuckDB Advantage:
 DuckDB calculates monthly vector centroids and inter-month drift using LAG.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE monthly_centroids (
                month_date DATE,
                centroid FLOAT[2]
            );
            INSERT INTO monthly_centroids VALUES
                ('2026-01-01', [0.90, 0.10]::FLOAT[2]),
                ('2026-02-01', [0.88, 0.12]::FLOAT[2]),
                ('2026-03-01', [0.70, 0.35]::FLOAT[2]); -- Significant semantic drift

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Track month-over-month semantic drift in concept centroids
            SELECT 
                month_date,
                centroid,
                LAG(centroid) OVER (ORDER BY month_date) AS prev_month_centroid,
                ROUND(
                    1.0 - array_cosine_similarity(
                        centroid, 
                        LAG(centroid) OVER (ORDER BY month_date)
                    ), 4
                ) AS drift_distance_from_prev_month
            FROM monthly_centroids
            ORDER BY month_date;
