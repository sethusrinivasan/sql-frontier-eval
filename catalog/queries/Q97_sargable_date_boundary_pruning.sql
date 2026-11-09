/*
 ==============================================================================
 Query ID:         Q97_sargable_date_boundary_pruning
 Title:            SARGable Partition Pruning: Exact Half-Open Date Boundary Ranges
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 When filtering analytical partitions for a calendar month, `BETWEEN '2026-01-01' AND '2026-01-31'` leaks into February 1st if timestamps contain hours/minutes, while `strftime('%m', ts) = '01'` disables partition pruning entirely.

 The Hidden Trap:
 Subtle boundary leakage or full table scans caused by non-SARGable WHERE predicates.

 The DuckDB Advantage:
 Half-open `>= '2026-01-01' AND < '2026-02-01'` ensures exact month boundaries and 100% metadata partition pruning.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE audit_events (
                event_id INT,
                created_at TIMESTAMP
            );
            INSERT INTO audit_events VALUES
                (1, '2026-01-31 23:59:59'),
                (2, '2026-02-01 00:00:00'), -- Should NOT be in January
                (3, '2026-01-15 12:00:00');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Exact SARGable half-open January 2026 boundary query
            SELECT 
                event_id,
                created_at
            FROM audit_events
            WHERE created_at >= TIMESTAMP '2026-01-01 00:00:00'
              AND created_at <  TIMESTAMP '2026-02-01 00:00:00'
            ORDER BY created_at;
