/*
 ==============================================================================
 Query ID:         Q100_market_basket_association_rules
 Title:            Market Basket Association Rules: Support, Confidence, and Lift in Pure SQL
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Data miners discover product affinities ('Customers who buy Item A also buy Item B') using Support, Confidence, and Lift metrics computed directly from transaction tables.

 The Hidden Trap:
 Generating cross-products across all transactions creates memory spills on large catalogs.

 The DuckDB Advantage:
 DuckDB can evaluate pair frequency matrices and marginal probabilities in memory.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE order_baskets (
                order_id INT,
                item VARCHAR
            );
            INSERT INTO order_baskets VALUES
                (1, 'Bread'), (1, 'Butter'), (1, 'Milk'),
                (2, 'Bread'), (2, 'Butter'),
                (3, 'Bread'), (3, 'Milk'),
                (4, 'Beer'),  (4, 'Diapers');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute Support, Confidence, and Lift for Item A -> Item B
            WITH basket_totals AS (
                SELECT COUNT(DISTINCT order_id) AS total_baskets FROM order_baskets
            ),
            item_counts AS (
                SELECT item, COUNT(DISTINCT order_id) AS item_baskets
                FROM order_baskets
                GROUP BY item
            ),
            pair_counts AS (
                SELECT 
                    a.item AS item_a,
                    b.item AS item_b,
                    COUNT(DISTINCT a.order_id) AS pair_baskets
                FROM order_baskets a
                JOIN order_baskets b 
                  ON a.order_id = b.order_id 
                 AND a.item != b.item
                GROUP BY a.item, b.item
            )
            SELECT 
                p.item_a,
                p.item_b,
                p.pair_baskets,
                -- Support: P(A and B)
                ROUND(p.pair_baskets * 1.0 / t.total_baskets, 3) AS support,
                -- Confidence: P(B | A) = pair / count_a
                ROUND(p.pair_baskets * 1.0 / ca.item_baskets, 3) AS confidence,
                -- Lift: Confidence / P(B) = (pair * total) / (count_a * count_b)
                ROUND((p.pair_baskets * 1.0 * t.total_baskets) / (ca.item_baskets * cb.item_baskets), 3) AS lift
            FROM pair_counts p
            JOIN item_counts ca ON p.item_a = ca.item
            JOIN item_counts cb ON p.item_b = cb.item
            CROSS JOIN basket_totals t
            WHERE p.pair_baskets >= 2
            ORDER BY lift DESC, p.item_a, p.item_b;
