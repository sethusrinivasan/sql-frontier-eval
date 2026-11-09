/*
 ==============================================================================
 Query ID:         Q21_temporal_gap_detection
 Title:            Continuous Asset Lease Unallocated Gap Discovery
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Fleet managers track commercial vehicles to find idle 'unrented' gaps between back-to-back rental contracts for fleet utilization auditing.

 The Hidden Trap:
 Comparing each row with LEAD without filtering where next_start > current_end misses adjacent non-overlapping bookings.

 The DuckDB Advantage:
 DuckDB window functions compute discrete idle intervals in a single scan.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE vehicle_leases (
                vehicle_id INT,
                lease_start DATE,
                lease_end DATE
            );
            INSERT INTO vehicle_leases VALUES
                (55, '2026-01-01', '2026-01-10'),
                (55, '2026-01-15', '2026-01-20'), -- 5 day gap (Jan 10 - Jan 15)
                (55, '2026-01-20', '2026-01-30'); -- contiguous

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Identify idle intervals between vehicle leases
            WITH lease_boundaries AS (
                SELECT 
                    vehicle_id,
                    lease_end AS gap_start,
                    LEAD(lease_start) OVER (PARTITION BY vehicle_id ORDER BY lease_start) AS gap_end
                FROM vehicle_leases
            )
            SELECT 
                vehicle_id,
                gap_start,
                gap_end,
                (gap_end - gap_start) AS idle_days
            FROM lease_boundaries
            WHERE gap_end IS NOT NULL 
              AND gap_end > gap_start
            ORDER BY vehicle_id, gap_start;
