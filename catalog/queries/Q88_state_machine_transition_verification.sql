/*
 ==============================================================================
 Query ID:         Q88_state_machine_transition_verification
 Title:            Transactional State Machine Transition Sequence Verification
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Financial compliance requires payment transactions to strictly follow the state sequence: INITIATED -> AUTHORIZED -> CAPTURED -> SETTLED. Any transaction skipping steps is flagged as fraudulent.

 The Hidden Trap:
 Verifying status counts without checking transition sequence allows out-of-order state transitions.

 The DuckDB Advantage:
 DuckDB LEAD/LAG checks verify exact valid transition edges against a legal state graph.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE payment_status_audit (
                tx_id INT,
                step_order INT,
                status VARCHAR
            );
            -- Valid tx 1
            INSERT INTO payment_status_audit VALUES
                (1, 1, 'INITIATED'), (1, 2, 'AUTHORIZED'), (1, 3, 'CAPTURED');
            -- Invalid tx 2: Jumped directly from INITIATED to CAPTURED!
            INSERT INTO payment_status_audit VALUES
                (2, 1, 'INITIATED'), (2, 2, 'CAPTURED');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Validate that every state transition matches the legal state machine rules
            WITH transitions AS (
                SELECT 
                    tx_id,
                    status AS current_state,
                    LEAD(status) OVER (PARTITION BY tx_id ORDER BY step_order) AS next_state
                FROM payment_status_audit
            )
            SELECT 
                tx_id,
                current_state,
                next_state,
                CASE 
                    WHEN next_state IS NULL THEN 'TERMINAL_STATE'
                    WHEN current_state = 'INITIATED' AND next_state = 'AUTHORIZED' THEN 'VALID'
                    WHEN current_state = 'AUTHORIZED' AND next_state = 'CAPTURED' THEN 'VALID'
                    WHEN current_state = 'CAPTURED' AND next_state = 'SETTLED' THEN 'VALID'
                    ELSE 'INVALID_ILLEGAL_STATE_JUMP'
                END AS audit_validation_result
            FROM transitions
            ORDER BY tx_id, current_state;
