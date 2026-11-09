/*
 ==============================================================================
 Query ID:         Q37_hybrid_relational_vector_cohort_join
 Title:            Cohort-Constrained Vector Match with Geographical Regionality
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Real-world matchmaking (dating apps, gig-economy driver matching) requires vector personality/skill compatibility joined with strict relational geographic and category boundaries.

 The Hidden Trap:
 Matching vectors globally without partitioning by region produces candidates located 3,000 miles away.

 The DuckDB Advantage:
 DuckDB joins relational partitions (region = 'NA-WEST') directly with vector distance.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE candidates (
                candidate_id INT,
                region VARCHAR,
                skills_vec FLOAT[3]
            );
            CREATE TABLE job_openings (
                job_id INT,
                region VARCHAR,
                required_vec FLOAT[3]
            );
            INSERT INTO candidates VALUES
                (1, 'US-WEST', [0.8, 0.5, 0.2]::FLOAT[3]),
                (2, 'EU-CENTRAL', [0.85, 0.5, 0.2]::FLOAT[3]);
            INSERT INTO job_openings VALUES
                (101, 'US-WEST', [0.82, 0.48, 0.18]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Match jobs to candidates strictly within matching geographical region ordered by skill compatibility
            SELECT 
                j.job_id,
                j.region,
                c.candidate_id,
                ROUND(array_cosine_similarity(c.skills_vec, j.required_vec), 4) AS skill_fit_score
            FROM job_openings j
            JOIN candidates c
              ON j.region = c.region
            ORDER BY skill_fit_score DESC;
