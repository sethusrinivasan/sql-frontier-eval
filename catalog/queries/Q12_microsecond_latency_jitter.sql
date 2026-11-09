/*
 ==============================================================================
 Query ID:         Q12_microsecond_latency_jitter
 Title:            Inter-Packet Network Arrival Jitter at Nanosecond Resolution
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 High-speed network telemetry measures packet arrival jitter (variance in inter-packet delay). Jitter spikes indicate network congestion or buffer bloat.

 The Hidden Trap:
 Standard SQL datetime arithmetic truncates to milliseconds or seconds, losing high-frequency microsecond microbursts.

 The DuckDB Advantage:
 DuckDB natively supports `epoch_ns` and TIMESTAMP with microsecond/nanosecond fidelity.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE packet_stream (
                packet_id INT,
                captured_at TIMESTAMP
            );
            INSERT INTO packet_stream VALUES
                (1, '2026-03-01 12:00:00.000100'),
                (2, '2026-03-01 12:00:00.000150'), -- +50us
                (3, '2026-03-01 12:00:00.000300'), -- +150us (jitter spike)
                (4, '2026-03-01 12:00:00.000350');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute inter-packet arrival delta in microseconds and identify variance
            WITH deltas AS (
                SELECT 
                    packet_id,
                    captured_at,
                    date_diff('microsecond', 
                        LAG(captured_at) OVER (ORDER BY captured_at), 
                        captured_at
                    ) AS delta_microseconds
                FROM packet_stream
            )
            SELECT 
                packet_id,
                captured_at,
                delta_microseconds,
                -- Measure moving jitter variance over last 3 packets
                ROUND(STDDEV(delta_microseconds) OVER (
                    ORDER BY captured_at 
                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                ), 2) AS rolling_jitter_stddev
            FROM deltas
            ORDER BY captured_at;
