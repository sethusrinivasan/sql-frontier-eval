/*
 ==============================================================================
 Query ID:         Q34_user_profile_embedding_centroid
 Title:            User Profile Preference Vector Centroid Aggregation
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 To personalize feeds, recommendation engines compute a dynamic user preference vector by calculating the average centroid of the embeddings of products the user clicked in the last 7 days.

 The Hidden Trap:
 SQL standard lacks native array averaging; unnesting arrays without proper positional indexes scrambles vector dimensions.

 The DuckDB Advantage:
 DuckDB array indexing and UNNEST WITH ORDINALITY allow dimension-wise vector averaging.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE user_clicks_vectors (
                user_id INT,
                item_id INT,
                item_vector FLOAT[3]
            );
            INSERT INTO user_clicks_vectors VALUES
                (42, 1, [0.8, 0.2, 0.1]::FLOAT[3]),
                (42, 2, [0.6, 0.4, 0.2]::FLOAT[3]),
                (42, 3, [0.7, 0.3, 0.3]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate element-wise centroid vector for user 42
            WITH unnested_dims AS (
                SELECT 
                    user_id,
                    item_id,
                    UNNEST(item_vector) AS val,
                    GENERATE_SUBSCRIPTS(item_vector, 1) AS dim_idx
                FROM user_clicks_vectors
            ),
            avg_dims AS (
                SELECT 
                    user_id,
                    dim_idx,
                    ROUND(AVG(val), 4) AS avg_dim_val
                FROM unnested_dims
                GROUP BY user_id, dim_idx
                ORDER BY user_id, dim_idx
            )
            SELECT 
                user_id,
                LIST(avg_dim_val)::FLOAT[3] AS user_preference_centroid
            FROM avg_dims
            GROUP BY user_id;
