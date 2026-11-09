/*
 ==============================================================================
 Query ID:         Q24_sargable_fiscal_partition_prune
 Title:            SARGable Fiscal Year Date Range Partition Pruning
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Data warehouses partition petabyte event tables by date. Wrapping date columns in functions (e.g. `WHERE strftime('%Y', event_time) = '2026'`) breaks partition pruning, forcing a full table scan.

 The Hidden Trap:
 Non-SARGable functions force DuckDB/Snowflake to scan every Parquet row group.

 The DuckDB Advantage:
 Direct boundary comparison (`>= '2026-01-01' AND < '2027-01-01'`) allows DuckDB to prune Parquet files via metadata statistics.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE telemetry_partitions (
                event_id INT,
                event_timestamp TIMESTAMP,
                payload VARCHAR
            );
            INSERT INTO telemetry_partitions VALUES
                (1, '2025-12-31 23:59:59', 'old'),
                (2, '2026-01-01 00:00:00', 'target_start'),
                (3, '2026-06-15 12:00:00', 'target_mid'),
                (4, '2027-01-01 00:00:00', 'out_of_bounds');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Exact SARGable half-open date boundary pruning
            SELECT 
                event_id,
                event_timestamp,
                payload
            FROM telemetry_partitions
            WHERE event_timestamp >= TIMESTAMP '2026-01-01 00:00:00'
              AND event_timestamp <  TIMESTAMP '2027-01-01 00:00:00'
            ORDER BY event_timestamp;
