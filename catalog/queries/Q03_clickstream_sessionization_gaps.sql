/*
 ==============================================================================
 Query ID:         Q03_clickstream_sessionization_gaps
 Title:            Clickstream Sessionization with Inactivity Timeouts (Gaps & Islands)
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Digital analytics platforms group raw user pageviews into 'sessions'. If a user is inactive for more than 30 minutes, the next click begins a brand-new session.

 The Hidden Trap:
 Models mistakenly partition by user_id and take ROW_NUMBER(), which fails to segment sessions by time gaps, or use self-joins which scale quadratically.

 The DuckDB Advantage:
 Window functions (LAG) combined with cumulative conditional sums (SUM(is_new_session) OVER) produce linear O(N) streaming session identifiers.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE user_events (
                user_id INT,
                event_time TIMESTAMP,
                page_url VARCHAR
            );
            INSERT INTO user_events VALUES
                (101, '2026-03-01 10:00:00', '/home'),
                (101, '2026-03-01 10:05:00', '/products'),
                (101, '2026-03-01 10:45:00', '/checkout'), -- 40m gap -> New session
                (101, '2026-03-01 10:50:00', '/confirmation');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Detect session breaks (>30 min inactivity) and assign deterministic session UUIDs
            WITH event_lags AS (
                SELECT 
                    user_id,
                    event_time,
                    page_url,
                    -- Compare against preceding event timestamp for this user
                    LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_event_time
                FROM user_events
            ),
            session_flags AS (
                SELECT 
                    user_id,
                    event_time,
                    page_url,
                    -- Mark 1 if first event or gap exceeds 30 minutes, else 0
                    CASE 
                        WHEN prev_event_time IS NULL THEN 1
                        WHEN date_diff('second', prev_event_time, event_time) > 1800 THEN 1 
                        ELSE 0 
                    END AS is_new_session
                FROM event_lags
            )
            SELECT 
                user_id,
                event_time,
                page_url,
                -- Cumulative sum over flags establishes monotonically increasing session ID
                SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_time) AS session_id
            FROM session_flags
            ORDER BY user_id, event_time;
