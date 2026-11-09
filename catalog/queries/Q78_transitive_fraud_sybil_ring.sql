/*
 ==============================================================================
 Query ID:         Q78_transitive_fraud_sybil_ring
 Title:            Transitive Fraud Ring & Sybil Account Detection via Device Links
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Financial fraudsters create hundreds of fake accounts linked by shared credit cards, device fingerprints, or IP addresses. Finding all accounts transitively connected to a confirmed fraudster exposes the syndicate.

 The Hidden Trap:
 Looking only 1 hop away misses fraudsters who funnel funds through mule intermediary accounts.

 The DuckDB Advantage:
 DuckDB recursive CTEs trace transitive graph edges across multiple hops.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE shared_identifiers (
                account_id INT,
                linked_account_id INT
            );
            INSERT INTO shared_identifiers VALUES
                (101, 102), -- 101 shares credit card with 102
                (102, 103), -- 102 shares device with 103
                (103, 104), -- 103 shares bank account with 104
                (201, 202); -- Separate cluster

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find all accounts transitively linked to known bad actor 101
            WITH RECURSIVE fraud_cluster AS (
                SELECT 
                    101 AS seed_account,
                    linked_account_id AS connected_account,
                    1 AS hop_distance
                FROM shared_identifiers
                WHERE account_id = 101
                
                UNION ALL
                
                SELECT 
                    c.seed_account,
                    s.linked_account_id,
                    c.hop_distance + 1
                FROM fraud_cluster c
                JOIN shared_identifiers s ON c.connected_account = s.account_id
                WHERE c.hop_distance < 5
            )
            SELECT DISTINCT 
                seed_account,
                connected_account,
                MIN(hop_distance) AS shortest_hop_distance
            FROM fraud_cluster
            GROUP BY seed_account, connected_account
            ORDER BY shortest_hop_distance;
