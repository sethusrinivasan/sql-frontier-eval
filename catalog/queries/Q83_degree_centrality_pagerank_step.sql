/*
 ==============================================================================
 Query ID:         Q83_degree_centrality_pagerank_step
 Title:            Network Node In-Degree Centrality and Influence Ranking
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Social network influence and API hub criticality are determined by node in-degree centrality (number of inbound links from distinct entities).

 The Hidden Trap:
 Counting total edges without filtering distinct source nodes allows a single spammer to inflate influencer metrics.

 The DuckDB Advantage:
 DuckDB aggregates high-volume graph degree metrics with high-speed hash grouping.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE network_follows (
                follower_id INT,
                target_user_id INT
            );
            INSERT INTO network_follows VALUES
                (101, 1), (102, 1), (103, 1), (104, 1), -- Node 1 has 4 followers
                (101, 2), (102, 2),                     -- Node 2 has 2 followers
                (101, 3);                               -- Node 3 has 1 follower

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute in-degree centrality and influence rank
            SELECT 
                target_user_id AS influencer_id,
                COUNT(DISTINCT follower_id) AS in_degree_centrality,
                DENSE_RANK() OVER (ORDER BY COUNT(DISTINCT follower_id) DESC) AS influence_rank
            FROM network_follows
            GROUP BY target_user_id
            ORDER BY influence_rank;
