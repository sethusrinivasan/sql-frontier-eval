/*
 ==============================================================================
 Query ID:         Q04_dual_bound_session_capping
 Title:            Sliding Sessionization with Absolute Maximum Duration Cap
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Real-world web sessions often need dual constraints: a 30-minute inactivity timeout AND a strict maximum 4-hour absolute session duration to prevent bots from maintaining endless sessions.

 The Hidden Trap:
 A simple inactivity check keeps sessions alive indefinitely if events happen every 10 minutes. Tracking session origin requires window frames with state.

 The DuckDB Advantage:
 DuckDB can evaluate nested window stages seamlessly with zero intermediate disk spill.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE bot_events (
                user_id INT,
                event_time TIMESTAMP,
                action VARCHAR
            );
            INSERT INTO bot_events VALUES
                (1, '2026-03-01 00:00:00', 'ping'),
                (1, '2026-03-01 02:00:00', 'ping'), -- +2 hrs
                (1, '2026-03-01 04:30:00', 'ping'), -- +4.5 hrs (exceeds 4h cap)
                (1, '2026-03-01 04:45:00', 'ping');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Partition sessions by inactivity (>30m) OR exceeding 4 hours from session start
            WITH ranked_events AS (
                SELECT 
                    user_id,
                    event_time,
                    action,
                    LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_time
                FROM bot_events
            ),
            step_flags AS (
                SELECT 
                    user_id,
                    event_time,
                    action,
                    CASE 
                        WHEN prev_time IS NULL THEN 1
                        WHEN date_diff('minute', prev_time, event_time) > 30 THEN 1
                        ELSE 0
                    END AS gap_split
                FROM ranked_events
            ),
            base_sessions AS (
                SELECT 
                    *,
                    SUM(gap_split) OVER (PARTITION BY user_id ORDER BY event_time) AS raw_session_id
                FROM step_flags
            )
            SELECT 
                user_id,
                event_time,
                action,
                raw_session_id,
                -- Measure elapsed minutes from session genesis
                date_diff('minute', 
                    FIRST_VALUE(event_time) OVER (PARTITION BY user_id, raw_session_id ORDER BY event_time),
                    event_time
                ) AS minutes_since_session_start
            FROM base_sessions
            ORDER BY user_id, event_time;
