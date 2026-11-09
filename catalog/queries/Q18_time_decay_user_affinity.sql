/*
 ==============================================================================
 Query ID:         Q18_time_decay_user_affinity
 Title:            Exponential Time-Decayed User Affinity Scoring
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Recommendation systems score user interest where recent clicks count significantly more than clicks from 30 days ago, modeled via exponential decay: score * e^(-lambda * delta_days).

 The Hidden Trap:
 Equal-weight counts overemphasize obsolete user interests from months ago.

 The DuckDB Advantage:
 DuckDB vector math supports mathematical functions (`EXP`, `POW`) directly in aggregation pipelines.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE item_clicks (
                user_id INT,
                category VARCHAR,
                click_time TIMESTAMP
            );
            INSERT INTO item_clicks VALUES
                (99, 'laptops', '2026-03-01 10:00:00'), -- Today
                (99, 'laptops', '2026-02-20 10:00:00'), -- 9 days ago
                (99, 'shoes',   '2026-01-01 10:00:00'); -- 60 days ago

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Exponential decay affinity score with 7-day half-life (lambda = ln(2)/7 = ~0.099)
            SELECT 
                user_id,
                category,
                ROUND(SUM(
                    EXP(-0.099 * date_diff('day', click_time, TIMESTAMP '2026-03-01 12:00:00'))
                ), 3) AS decayed_affinity_score
            FROM item_clicks
            GROUP BY user_id, category
            ORDER BY decayed_affinity_score DESC;
