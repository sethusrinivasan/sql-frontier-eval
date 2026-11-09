/*
 ==============================================================================
 Query ID:         Q71_search_journey_order_attribution
 Title:            Customer Search-to-Purchase Path Attribution (Session Query Lift)
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 E-commerce search product managers need to know which search queries drove actual revenue. We link search queries to checkout events within the same 30-minute session.

 The Hidden Trap:
 Attributing purchases to search queries that occurred after the purchase order was placed.

 The DuckDB Advantage:
 DuckDB temporal range joins ensure search queries precede the checkout timestamp.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE user_search_queries (
                user_id INT,
                query_term VARCHAR,
                searched_at TIMESTAMP
            );
            CREATE TABLE completed_orders (
                order_id INT,
                user_id INT,
                order_total DECIMAL(10,2),
                ordered_at TIMESTAMP
            );
            INSERT INTO user_search_queries VALUES
                (50, 'noise canceling headphones', '2026-03-01 14:10:00'),
                (50, 'sony xm5 sale',              '2026-03-01 14:15:00');
            INSERT INTO completed_orders VALUES
                (1001, 50, 349.99, '2026-03-01 14:25:00');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Attribute purchase to the most recent search query prior to order
            SELECT 
                o.order_id,
                o.user_id,
                o.order_total,
                s.query_term AS attributing_search_query,
                s.searched_at,
                o.ordered_at
            FROM completed_orders o
            ASOF JOIN user_search_queries s
              ON o.user_id = s.user_id
             AND o.ordered_at >= s.searched_at
            ORDER BY o.order_id;
