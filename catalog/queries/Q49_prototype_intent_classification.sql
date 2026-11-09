/*
 ==============================================================================
 Query ID:         Q49_prototype_intent_classification
 Title:            Zero-Shot Query Intent Classification via Prototype Vector Distance
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Instead of training a BERT classifier, user query vectors are compared against pre-computed 'intent prototype vectors' (e.g. Navigational, Transactional, Informational). The closest prototype labels the query intent.

 The Hidden Trap:
 Maintaining external classifier microservices adds 50ms latency to query planning.

 The DuckDB Advantage:
 DuckDB classifies intent in pure SQL with sub-millisecond execution.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE intent_prototypes (
                intent_name VARCHAR,
                prototype_vector FLOAT[2]
            );
            CREATE TABLE inbound_queries (
                query_id INT,
                query_text VARCHAR,
                query_vector FLOAT[2]
            );
            INSERT INTO intent_prototypes VALUES
                ('TRANSACTIONAL_BUY', [0.9, 0.1]::FLOAT[2]),
                ('INFORMATIONAL_FAQ', [0.1, 0.9]::FLOAT[2]);
            INSERT INTO inbound_queries VALUES
                (1, 'where to purchase macbook pro', [0.88, 0.15]::FLOAT[2]),
                (2, 'how does duckdb storage work',   [0.15, 0.85]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Classify each query to its closest intent prototype
            WITH ranked_intents AS (
                SELECT 
                    q.query_id,
                    q.query_text,
                    p.intent_name,
                    array_cosine_similarity(q.query_vector, p.prototype_vector) AS intent_similarity,
                    ROW_NUMBER() OVER (
                        PARTITION BY q.query_id 
                        ORDER BY array_cosine_similarity(q.query_vector, p.prototype_vector) DESC
                    ) AS rank_match
                FROM inbound_queries q
                CROSS JOIN intent_prototypes p
            )
            SELECT 
                query_id,
                query_text,
                intent_name AS predicted_intent,
                ROUND(intent_similarity, 4) AS confidence
            FROM ranked_intents
            WHERE rank_match = 1
            ORDER BY query_id;
