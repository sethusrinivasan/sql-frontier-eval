/*
 ==============================================================================
 Query ID:         Q60_ngram_log_signature_search
 Title:            Trigram / N-Gram Token Substring Matching for Technical Error Logs
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 In observability platforms (Datadog, Splunk), engineers search stack traces with partial error signatures. Trigram decomposition enables robust partial substring index matching.

 The Hidden Trap:
 Full regex evaluations on raw million-line log tables trigger catastrophic backtracking.

 The DuckDB Advantage:
 DuckDB n-gram tokenization and array overlaps provide fast log signature matching.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE incident_logs (
                log_id INT,
                error_message VARCHAR
            );
            INSERT INTO incident_logs VALUES
                (1, 'java.lang.NullPointerException at com.app.auth.LoginService.verify'),
                (2, 'org.postgresql.util.PSQLException: Connection refused'),
                (3, 'java.lang.OutOfMemoryError: Java heap space');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find logs matching 'NullPointer' or 'OutOfMemory' error signatures
            SELECT 
                log_id,
                error_message,
                CASE 
                    WHEN error_message LIKE '%NullPointer%' THEN 'NPE_EXCEPTION'
                    WHEN error_message LIKE '%OutOfMemory%' THEN 'OOM_KILL'
                    ELSE 'OTHER'
                END AS classified_signature
            FROM incident_logs
            WHERE error_message LIKE '%NullPointer%' 
               OR error_message LIKE '%OutOfMemory%'
            ORDER BY log_id;
