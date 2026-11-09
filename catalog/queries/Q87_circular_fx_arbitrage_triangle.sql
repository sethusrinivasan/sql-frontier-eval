/*
 ==============================================================================
 Query ID:         Q87_circular_fx_arbitrage_triangle
 Title:            Triangular FX Currency Arbitrage Detection (Loop Profitability)
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 High-frequency FX trading bots scan for triangular arbitrage where converting USD -> EUR -> JPY -> USD yields more than 1.00 USD after exchange rates.

 The Hidden Trap:
 Missing currency conversion bid-ask spreads causes false positive arbitrage signals that lose money in practice.

 The DuckDB Advantage:
 DuckDB evaluates 3-hop currency cycles and product rates in sub-millisecond execution.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE fx_pairs (
                from_curr VARCHAR,
                to_curr VARCHAR,
                exchange_rate DOUBLE
            );
            INSERT INTO fx_pairs VALUES
                ('USD', 'EUR', 0.92),
                ('EUR', 'JPY', 160.0),
                ('JPY', 'USD', 0.0069); -- Arbitrage loop: 0.92 * 160 * 0.0069 = 1.01568 (+1.5% profit)

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Detect 3-hop triangular arbitrage opportunities where effective rate > 1.005
            SELECT 
                a.from_curr AS curr_start,
                a.to_curr AS curr_mid1,
                b.to_curr AS curr_mid2,
                c.to_curr AS curr_end,
                ROUND(a.exchange_rate * b.exchange_rate * c.exchange_rate, 4) AS loop_multiplier,
                ROUND((a.exchange_rate * b.exchange_rate * c.exchange_rate - 1.0) * 100, 2) AS profit_margin_pct
            FROM fx_pairs a
            JOIN fx_pairs b ON a.to_curr = b.from_curr
            JOIN fx_pairs c ON b.to_curr = c.from_curr AND c.to_curr = a.from_curr
            WHERE (a.exchange_rate * b.exchange_rate * c.exchange_rate) > 1.005;
