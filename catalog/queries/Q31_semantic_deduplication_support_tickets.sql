/*
 ==============================================================================
 Query ID:         Q31_semantic_deduplication_support_tickets
 Title:            Semantic Deduplication of IT Incident Tickets via Vector Cosine Threshold
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 During service outages, hundreds of users submit identically phrased IT support tickets ('login down', 'cannot access account'). Clustering tickets with vector similarity > 0.88 consolidates duplicates into a single incident.

 The Hidden Trap:
 Quadratic N x N self-joins without ordering check (`t1.id < t2.id`) double compute and compare tickets to themselves.

 The DuckDB Advantage:
 Triangle inequality pruning and symmetric self-join filtering in DuckDB.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE support_tickets (
                ticket_id INT,
                subject VARCHAR,
                vector FLOAT[3]
            );
            INSERT INTO support_tickets VALUES
                (1, 'Cannot log into customer portal',  [0.9, 0.1, 0.0]::FLOAT[3]),
                (2, 'Portal login failing with 500 error', [0.89, 0.12, 0.01]::FLOAT[3]),
                (3, 'Billing address invoice update',   [0.1, 0.8, 0.2]::FLOAT[3]),
                (4, 'Unable to authenticate on website', [0.91, 0.09, 0.02]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Detect duplicate ticket pairs with cosine similarity >= 0.88
            SELECT 
                t1.ticket_id AS primary_ticket_id,
                t1.subject AS primary_subject,
                t2.ticket_id AS duplicate_ticket_id,
                t2.subject AS duplicate_subject,
                ROUND(array_cosine_similarity(t1.vector, t2.vector), 4) AS similarity
            FROM support_tickets t1
            JOIN support_tickets t2 
              ON t1.ticket_id < t2.ticket_id -- strictly upper triangle to avoid duplicates and self-matching
             AND array_cosine_similarity(t1.vector, t2.vector) >= 0.88
            ORDER BY similarity DESC;
