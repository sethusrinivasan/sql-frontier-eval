/*
 ==============================================================================
 Query ID:         Q02_dynamic_point_in_time_fx
 Title:            Multi-Currency Point-in-Time FX Conversion via ASOF JOIN
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 Global payments systems record transactions in local currencies (EUR, JPY, GBP) that must be converted to USD using the prevailing exchange rate at the exact transaction millisecond.

 The Hidden Trap:
 Joining to a daily FX table using DATE(ts) loses intraday volatility and causes currency conversion discrepancies of up to 1-2% during volatile market events.

 The DuckDB Advantage:
 DuckDB's ASOF JOIN enables continuous real-time currency conversion with millisecond granularity.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE fx_rates (
                rate_time TIMESTAMP,
                currency VARCHAR,
                rate_to_usd DOUBLE
            );
            CREATE TABLE payments (
                payment_id INT,
                payment_time TIMESTAMP,
                currency VARCHAR,
                amount_local DOUBLE
            );
            INSERT INTO fx_rates VALUES
                ('2026-03-01 12:00:00', 'EUR', 1.0820),
                ('2026-03-01 12:15:00', 'EUR', 1.0845),
                ('2026-03-01 12:30:00', 'EUR', 1.0810);
            INSERT INTO payments VALUES
                (1, '2026-03-01 12:05:00', 'EUR', 5000.00),
                (2, '2026-03-01 12:20:00', 'EUR', 12000.00),
                (3, '2026-03-01 12:45:00', 'EUR', 7500.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Convert international payments to USD using the most recent point-in-time exchange rate
            SELECT 
                p.payment_id,
                p.payment_time,
                p.currency,
                p.amount_local,
                fx.rate_to_usd,
                ROUND(p.amount_local * fx.rate_to_usd, 2) AS amount_usd,
                fx.rate_time AS fx_snapshot_time
            FROM payments p
            ASOF JOIN fx_rates fx
              ON p.currency = fx.currency
             AND p.payment_time >= fx.rate_time
            ORDER BY p.payment_id;
