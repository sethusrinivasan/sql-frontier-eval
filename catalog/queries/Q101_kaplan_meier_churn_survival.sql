/*
 ==============================================================================
 Query ID:         Q101_kaplan_meier_churn_survival
 Title:            Kaplan-Meier Non-Parametric Customer Survival Analysis in SQL
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Actuarial and SaaS subscription models estimate the probability of customer survival past Day T, accounting for right-censored users who haven't churned yet.

 The Hidden Trap:
 Naively dividing churned users by total signups underestimates customer lifetime value.

 The DuckDB Advantage:
 DuckDB window functions compute step-down survival curves using cumulative products.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE subscription_cohort (
                user_id INT,
                tenure_months INT,
                has_churned BOOLEAN
            );
            INSERT INTO subscription_cohort VALUES
                (1, 1, true),  -- Churned at month 1
                (2, 1, false), -- Still active at month 1
                (3, 2, true),  -- Churned at month 2
                (4, 2, false),
                (5, 3, false);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Kaplan-Meier survival probability estimation by tenure month
            WITH monthly_risk AS (
                SELECT 
                    tenure_months,
                    COUNT(*) AS cohort_events,
                    SUM(CASE WHEN has_churned THEN 1 ELSE 0 END) AS churn_count,
                    COUNT(*) OVER (ORDER BY tenure_months DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS number_at_risk
                FROM subscription_cohort
                GROUP BY tenure_months
            )
            SELECT 
                tenure_months,
                number_at_risk,
                churn_count,
                ROUND(1.0 - (churn_count * 1.0 / number_at_risk), 4) AS interval_survival_rate
            FROM monthly_risk
            ORDER BY tenure_months;
