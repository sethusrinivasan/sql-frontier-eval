/*
 ==============================================================================
 Query ID:         Q85_multilevel_referral_commissions
 Title:            Multi-Level Affiliate Referral Tree Commission Rollup (Tier 1-3)
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Affiliate programs reward referrals up to 3 tiers deep (Direct referrer gets 10%, Tier 2 gets 5%, Tier 3 gets 2.5% of purchase amount).

 The Hidden Trap:
 Hardcoded 3-way self-joins fail to handle users whose upline is only 1 or 2 tiers deep without complex coalesce logic.

 The DuckDB Advantage:
 DuckDB recursive CTEs assign dynamic commission percentages based on recursion depth.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE referral_links (
                user_id INT,
                referrer_id INT
            );
            CREATE TABLE user_purchases (
                purchase_id INT,
                user_id INT,
                amount DECIMAL(10,2)
            );
            INSERT INTO referral_links VALUES
                (4, 3), -- 4 referred by 3
                (3, 2), -- 3 referred by 2
                (2, 1); -- 2 referred by 1 (Grandparent)
            INSERT INTO user_purchases VALUES
                (101, 4, 1000.00); -- Purchase by user 4

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate multi-tier referral payout for purchase 101
            WITH RECURSIVE upline AS (
                -- Level 1: Direct referrer
                SELECT 
                    r.user_id AS buyer_id,
                    r.referrer_id AS beneficiary_id,
                    1 AS tier,
                    0.10 AS commission_rate
                FROM referral_links r
                WHERE r.user_id = 4
                
                UNION ALL
                
                -- Level 2 and 3 upline
                SELECT 
                    u.buyer_id,
                    r.referrer_id AS beneficiary_id,
                    u.tier + 1,
                    CASE WHEN u.tier + 1 = 2 THEN 0.05 ELSE 0.025 END AS commission_rate
                FROM upline u
                JOIN referral_links r ON u.beneficiary_id = r.user_id
                WHERE u.tier < 3
            )
            SELECT 
                u.buyer_id,
                u.beneficiary_id,
                u.tier,
                p.amount AS purchase_amount,
                ROUND(p.amount * u.commission_rate, 2) AS commission_earned
            FROM upline u
            JOIN user_purchases p ON u.buyer_id = p.user_id
            ORDER BY u.tier;
