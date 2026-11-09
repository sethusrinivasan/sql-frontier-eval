/*
 ==============================================================================
 Query ID:         Q16_sequential_funnel_precedence
 Title:            Chronological Multi-Stage Conversion Funnel with Time Boundaries
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 In product funnels (Signup -> Verify -> Purchase), events must occur in exact chronological order, with each step completed within 24 hours of the previous.

 The Hidden Trap:
 Models join events without checking timestamp ordering (e.g., verifying after purchase), artificially inflating funnel conversion.

 The DuckDB Advantage:
 DuckDB QUALIFY and chained CTEs preserve strict chronological order with pushdown predicates.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE user_actions (
                user_id INT,
                stage VARCHAR,
                action_time TIMESTAMP
            );
            INSERT INTO user_actions VALUES
                (1, 'signup',   '2026-03-01 10:00:00'),
                (1, 'verify',   '2026-03-01 11:00:00'),
                (1, 'purchase', '2026-03-01 15:00:00'),
                (2, 'signup',   '2026-03-01 10:00:00'),
                (2, 'purchase', '2026-03-01 10:30:00'); -- Skipped verify

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Enforce Signup -> Verify -> Purchase chronological order
            WITH step1 AS (
                SELECT user_id, action_time AS signup_time
                FROM user_actions
                WHERE stage = 'signup'
            ),
            step2 AS (
                SELECT s1.user_id, s1.signup_time, MIN(a.action_time) AS verify_time
                FROM step1 s1
                JOIN user_actions a 
                  ON s1.user_id = a.user_id 
                 AND a.stage = 'verify'
                 AND a.action_time >= s1.signup_time
                 AND a.action_time <= s1.signup_time + INTERVAL '24 hours'
                GROUP BY s1.user_id, s1.signup_time
            ),
            step3 AS (
                SELECT s2.user_id, s2.signup_time, s2.verify_time, MIN(a.action_time) AS purchase_time
                FROM step2 s2
                JOIN user_actions a 
                  ON s2.user_id = a.user_id 
                 AND a.stage = 'purchase'
                 AND a.action_time >= s2.verify_time
                 AND a.action_time <= s2.verify_time + INTERVAL '24 hours'
                GROUP BY s2.user_id, s2.signup_time, s2.verify_time
            )
            SELECT 
                COUNT(s1.user_id) AS total_signups,
                COUNT(s2.user_id) AS verified_users,
                COUNT(s3.user_id) AS completed_purchasers,
                ROUND(COUNT(s3.user_id) * 100.0 / COUNT(s1.user_id), 1) AS end_to_end_conversion_pct
            FROM step1 s1
            LEFT JOIN step2 s2 ON s1.user_id = s2.user_id
            LEFT JOIN step3 s3 ON s1.user_id = s3.user_id;
