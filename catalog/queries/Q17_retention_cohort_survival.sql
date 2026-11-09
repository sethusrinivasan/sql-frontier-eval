/*
 ==============================================================================
 Query ID:         Q17_retention_cohort_survival
 Title:            Dynamic User Retention Cohort Matrix by Weekly Milestones
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 SaaS analytics track weekly retention curves (Day 0, Day 7, Day 14, Day 30) based on user signup week.

 The Hidden Trap:
 Calculating retention without dynamic date grouping produces rigid, fragile queries requiring manual updates every week.

 The DuckDB Advantage:
 DuckDB date_trunc and conditional aggregation build clean dynamic cohort tables.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE app_users (
                user_id INT,
                signup_date DATE
            );
            CREATE TABLE activity_log (
                user_id INT,
                activity_date DATE
            );
            INSERT INTO app_users VALUES
                (1, '2026-02-01'), (2, '2026-02-01'), (3, '2026-02-08');
            INSERT INTO activity_log VALUES
                (1, '2026-02-01'), (1, '2026-02-08'), (1, '2026-02-15'),
                (2, '2026-02-01'), (2, '2026-02-08'),
                (3, '2026-02-08');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Generate dynamic cohort retention matrix
            SELECT 
                date_trunc('week', u.signup_date) AS cohort_week,
                COUNT(DISTINCT u.user_id) AS cohort_size,
                COUNT(DISTINCT CASE WHEN a.activity_date = u.signup_date THEN u.user_id END) AS day_0_active,
                COUNT(DISTINCT CASE WHEN a.activity_date >= u.signup_date + 7 AND a.activity_date < u.signup_date + 14 THEN u.user_id END) AS day_7_active,
                COUNT(DISTINCT CASE WHEN a.activity_date >= u.signup_date + 14 AND a.activity_date < u.signup_date + 21 THEN u.user_id END) AS day_14_active
            FROM app_users u
            LEFT JOIN activity_log a ON u.user_id = a.user_id
            GROUP BY cohort_week
            ORDER BY cohort_week;
