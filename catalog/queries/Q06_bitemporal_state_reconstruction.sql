/*
 ==============================================================================
 Query ID:         Q06_bitemporal_state_reconstruction
 Title:            Bitemporal Auditing: Valid-Time vs. Transaction-Time Alignment
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Financial compliance requires knowing: 'What did we believe customer Alice's credit limit was on May 15th, based on what was entered into our database as of June 1st?' (Bitemporal query).

 The Hidden Trap:
 Relying on a single timestamp column confuses retroactive corrections with real-world effective dates, causing compliance audit failures.

 The DuckDB Advantage:
 DuckDB can evaluate dual closed-open temporal intervals (`[valid_from, valid_to)` and `[system_from, system_to)`) with high-speed range predicates.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE credit_limits_audit (
                customer_id INT,
                credit_limit DECIMAL(10,2),
                valid_from DATE,
                valid_to DATE,
                system_from TIMESTAMP,
                system_to TIMESTAMP
            );
            INSERT INTO credit_limits_audit VALUES
                -- Original belief entered on May 1st
                (501, 5000.00, '2026-05-01', '2026-12-31', '2026-05-01 09:00:00', '2026-06-01 10:00:00'),
                -- Retroactive correction entered on June 1st backdating Alice's limit to $8,000 effective May 15th
                (501, 8000.00, '2026-05-15', '2026-12-31', '2026-06-01 10:00:00', '9999-12-31 23:59:59');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Query credit limit effective on 2026-05-20 as known to the system on 2026-05-25 (before retroactive update)
            SELECT 
                customer_id,
                credit_limit AS limit_as_known_then,
                valid_from,
                valid_to,
                system_from,
                system_to
            FROM credit_limits_audit
            WHERE customer_id = 501
              -- As-of Business Date: 2026-05-20
              AND DATE '2026-05-20' >= valid_from 
              AND DATE '2026-05-20' < valid_to
              -- As-of System State: 2026-05-25
              AND TIMESTAMP '2026-05-25 00:00:00' >= system_from 
              AND TIMESTAMP '2026-05-25 00:00:00' < system_to;
