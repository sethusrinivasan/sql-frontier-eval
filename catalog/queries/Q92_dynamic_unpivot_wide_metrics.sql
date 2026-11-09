/*
 ==============================================================================
 Query ID:         Q92_dynamic_unpivot_wide_metrics
 Title:            Dynamic UNPIVOT of Wide Tabular Sensor / Survey Metrics
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Legacy data or spreadsheet exports often arrive with metric names as column headers (cpu, memory, disk). Normalizing them into key-value pairs is necessary for time-series modeling.

 The Hidden Trap:
 Chaining 10 UNION ALL queries multiplies read passes over the source data.

 The DuckDB Advantage:
 DuckDB native `UNPIVOT` performs unpivoting in a single streaming pass.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE wide_telemetry (
                host_id VARCHAR,
                captured_date DATE,
                cpu_metric DOUBLE,
                mem_metric DOUBLE,
                disk_metric DOUBLE
            );
            INSERT INTO wide_telemetry VALUES
                ('srv-01', '2026-03-01', 45.2, 78.5, 92.1);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Transform wide metric columns into normalized key-value rows
            UNPIVOT wide_telemetry
            ON cpu_metric, mem_metric, disk_metric
            INTO
                NAME metric_name
                VALUE metric_value;
