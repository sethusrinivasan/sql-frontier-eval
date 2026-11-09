/*
 ==============================================================================
 Query ID:         Q05_iot_sensor_gap_fill_locf
 Title:            IoT Sensor Telemetry Gap-Filling via generate_series and LOCF
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Industrial IoT sensors emit readings intermittently to save bandwidth. Downstream machine learning models require strict continuous 1-minute time grids with Last Observation Carried Forward (LOCF).

 The Hidden Trap:
 Using OUTER JOIN without dynamic range generation leaves temporal voids, leading to missing periods in downstream feature stores.

 The DuckDB Advantage:
 DuckDB `generate_series` produces virtual timestamp arrays directly joined with windowed `IGNORE NULLS` forward-fills.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE sensor_telemetry (
                device_id INT,
                recorded_at TIMESTAMP,
                temperature DOUBLE
            );
            INSERT INTO sensor_telemetry VALUES
                (42, '2026-03-01 08:00:00', 21.5),
                (42, '2026-03-01 08:02:00', 22.0),
                (42, '2026-03-01 08:05:00', 22.8);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Resample sparse telemetry into continuous 1-minute intervals with Last Observation Carried Forward
            WITH time_grid AS (
                SELECT UNNEST(generate_series(
                    TIMESTAMP '2026-03-01 08:00:00',
                    TIMESTAMP '2026-03-01 08:05:00',
                    INTERVAL '1 minute'
                )) AS bucket_time
            ),
            aligned_readings AS (
                SELECT 
                    grid.bucket_time,
                    42 AS device_id,
                    st.temperature
                FROM time_grid grid
                LEFT JOIN sensor_telemetry st
                  ON grid.bucket_time = st.recorded_at
                 AND st.device_id = 42
            )
            SELECT 
                bucket_time,
                device_id,
                temperature AS raw_reading,
                -- Forward fill the most recent non-null temperature
                COALESCE(
                    temperature,
                    LAST_VALUE(temperature IGNORE NULLS) OVER (
                        PARTITION BY device_id 
                        ORDER BY bucket_time 
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
                ) AS filled_temperature
            FROM aligned_readings
            ORDER BY bucket_time;
