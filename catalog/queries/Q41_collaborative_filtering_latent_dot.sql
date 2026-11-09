/*
 ==============================================================================
 Query ID:         Q41_collaborative_filtering_latent_dot
 Title:            Latent Factor Matrix Factorization Dot Product Recommendation
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Matrix factorization (SVD / ALS) maps users and movies to latent factor vectors. Predicted rating is dot product of user vector and movie vector plus user and movie bias terms.

 The Hidden Trap:
 Omitting bias terms causes popular movies to be underrated and niche items to be overrated.

 The DuckDB Advantage:
 DuckDB can evaluate latent factor dot products combined with additive scalar bias terms.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE user_latent (
                user_id INT,
                user_bias DOUBLE,
                u_vec FLOAT[3]
            );
            CREATE TABLE item_latent (
                movie_id INT,
                title VARCHAR,
                movie_bias DOUBLE,
                m_vec FLOAT[3]
            );
            INSERT INTO user_latent VALUES
                (1, 0.2, [0.5, 0.3, 0.1]::FLOAT[3]);
            INSERT INTO item_latent VALUES
                (101, 'Sci-Fi Odyssey', 0.5, [0.6, 0.2, 0.1]::FLOAT[3]),
                (102, 'Romantic Comedy', -0.1, [0.1, 0.7, 0.2]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Predict user rating: baseline (3.5) + u_bias + m_bias + (u_vec . m_vec)
            SELECT 
                u.user_id,
                m.movie_id,
                m.title,
                ROUND(
                    3.5 + u.user_bias + m.movie_bias + array_inner_product(u.u_vec, m.m_vec), 2
                ) AS predicted_rating
            FROM user_latent u
            CROSS JOIN item_latent m
            WHERE u.user_id = 1
            ORDER BY predicted_rating DESC;
