/*
 ==============================================================================
 Query ID:         Q25_multi_touch_marketing_attribution
 Title:            Multi-Touch Marketing Attribution Comparison in a Single Pass
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 CMOs need to compare 3 attribution models (First-Touch, Last-Touch, and Uniform Linear) for touchpoints occurring within 30 days prior to conversion.

 The Hidden Trap:
 Running three separate join queries triples warehouse compute costs and risks data inconsistency.

 The DuckDB Advantage:
 DuckDB window functions compute First-Touch, Last-Touch, and touchpoint counts simultaneously in one query.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE ad_clicks (
                user_id INT,
                channel VARCHAR,
                click_time TIMESTAMP
            );
            CREATE TABLE conversions (
                user_id INT,
                conversion_time TIMESTAMP,
                revenue DECIMAL(10,2)
            );
            INSERT INTO ad_clicks VALUES
                (10, 'Google Search', '2026-03-01 09:00:00'),
                (10, 'Facebook Ad',   '2026-03-05 14:00:00'),
                (10, 'Email Promo',   '2026-03-10 18:00:00');
            INSERT INTO conversions VALUES
                (10, '2026-03-11 10:00:00', 300.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Multi-touch attribution comparison (First-touch, Last-touch, Linear)
            WITH eligible_touches AS (
                SELECT 
                    c.user_id,
                    c.revenue,
                    a.channel,
                    a.click_time,
                    ROW_NUMBER() OVER (PARTITION BY c.user_id ORDER BY a.click_time ASC) AS touch_asc,
                    ROW_NUMBER() OVER (PARTITION BY c.user_id ORDER BY a.click_time DESC) AS touch_desc,
                    COUNT(*) OVER (PARTITION BY c.user_id) AS total_touches
                FROM conversions c
                JOIN ad_clicks a 
                  ON c.user_id = a.user_id 
                 AND a.click_time >= c.conversion_time - INTERVAL '30 days'
                 AND a.click_time <= c.conversion_time
            )
            SELECT 
                channel,
                -- First Touch: 100% credit if first
                SUM(CASE WHEN touch_asc = 1 THEN revenue ELSE 0 END) AS first_touch_revenue,
                -- Last Touch: 100% credit if last
                SUM(CASE WHEN touch_desc = 1 THEN revenue ELSE 0 END) AS last_touch_revenue,
                -- Linear: Equal credit across all touchpoints
                ROUND(SUM(revenue / total_touches), 2) AS linear_touch_revenue
            FROM eligible_touches
            GROUP BY channel
            ORDER BY channel;
