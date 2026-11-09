/*
 ==============================================================================
 Query ID:         Q13_order_book_snapshot_reconstruction
 Title:            Point-in-Time Limit Order Book (LOB) State Reconstruction
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Market microstructure researchers need to reconstruct the exact bids and asks available at an arbitrary point in time from an append-only event stream of place, cancel, and fill orders.

 The Hidden Trap:
 Summing active orders without filtering out cancellations that occurred before the target time produces a phantom order book.

 The DuckDB Advantage:
 DuckDB can evaluate event lifespans and aggregate active depth efficiently in a single scan.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE order_events (
                event_id INT,
                order_id INT,
                event_type VARCHAR, -- 'INSERT', 'CANCEL', 'FILL'
                side VARCHAR,       -- 'BID', 'ASK'
                price DOUBLE,
                quantity INT,
                event_time TIMESTAMP
            );
            INSERT INTO order_events VALUES
                (1, 101, 'INSERT', 'BID', 100.50, 10, '2026-03-01 09:30:01'),
                (2, 102, 'INSERT', 'BID', 100.25, 20, '2026-03-01 09:30:02'),
                (3, 101, 'CANCEL', 'BID', 100.50, 10, '2026-03-01 09:30:05'),
                (4, 103, 'INSERT', 'BID', 100.60, 15, '2026-03-01 09:30:06');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Reconstruct order book state at exactly 09:30:05
            WITH snapshot_events AS (
                SELECT *
                FROM order_events
                WHERE event_time <= TIMESTAMP '2026-03-01 09:30:05'
            ),
            active_orders AS (
                SELECT 
                    order_id,
                    side,
                    price,
                    -- Net quantity remaining after cancellations/fills
                    SUM(CASE WHEN event_type = 'INSERT' THEN quantity ELSE -quantity END) AS remaining_qty
                FROM snapshot_events
                GROUP BY order_id, side, price
                HAVING SUM(CASE WHEN event_type = 'INSERT' THEN quantity ELSE -quantity END) > 0
            )
            SELECT 
                side,
                price,
                SUM(remaining_qty) AS aggregate_depth
            FROM active_orders
            GROUP BY side, price
            ORDER BY price DESC;
