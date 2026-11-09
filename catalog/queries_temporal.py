# Domain 1: High-Frequency Temporal & Time-Series Analytics (Queries 01 - 25)

TEMPORAL_QUERIES = [
    {
        "id": "Q01_asof_trade_quote_matching",
        "title": "Tick-Level Trade Execution Matching via Native ASOF JOIN",
        "domain": "Temporal & Time-Series",
        "human_context": "In algorithmic trading, every buy or sell order must be evaluated against the most recent prevailing market quote. Standard relational equality joins fail because quotes and trades happen at irregular microsecond intervals.",
        "hidden_trap": "LLMs typically write quadratic triangular self-joins (WHERE q.ts <= t.ts) or window functions with LAG/LAST_VALUE, which create massive memory spikes on high-frequency streams.",
        "duckdb_advantage": "DuckDB native `ASOF JOIN` performs an O(N log M) binary search scan directly across partitioned timestamp indices without sorting intermediate cross products.",
        "setup_sql": """
            CREATE TABLE quotes (
                quote_time TIMESTAMP,
                symbol VARCHAR,
                bid_price DOUBLE,
                ask_price DOUBLE
            );
            CREATE TABLE trades (
                trade_time TIMESTAMP,
                symbol VARCHAR,
                trade_id INT,
                executed_price DOUBLE,
                shares INT
            );
            INSERT INTO quotes VALUES
                ('2026-03-01 09:30:00.100', 'NVDA', 850.10, 850.25),
                ('2026-03-01 09:30:00.250', 'NVDA', 850.15, 850.30),
                ('2026-03-01 09:30:00.400', 'NVDA', 850.20, 850.35);
            INSERT INTO trades VALUES
                ('2026-03-01 09:30:00.150', 'NVDA', 101, 850.25, 100),
                ('2026-03-01 09:30:00.300', 'NVDA', 102, 850.30, 200),
                ('2026-03-01 09:30:00.450', 'NVDA', 103, 850.32, 150);
        """,
        "sql": """
            -- Match each executed trade with the latest market quote effective at that exact microsecond
            SELECT 
                t.trade_id,
                t.symbol,
                t.trade_time,
                t.executed_price,
                t.shares,
                q.quote_time AS prevailing_quote_time,
                q.bid_price,
                q.ask_price,
                -- Effective slippage calculation (difference between ask and executed price)
                ROUND(t.executed_price - q.ask_price, 4) AS slippage
            FROM trades t
            ASOF JOIN quotes q
              ON t.symbol = q.symbol
             AND t.trade_time >= q.quote_time
            ORDER BY t.trade_time;
        """
    },
    {
        "id": "Q02_dynamic_point_in_time_fx",
        "title": "Multi-Currency Point-in-Time FX Conversion via ASOF JOIN",
        "domain": "Temporal & Time-Series",
        "human_context": "Global payments systems record transactions in local currencies (EUR, JPY, GBP) that must be converted to USD using the prevailing exchange rate at the exact transaction millisecond.",
        "hidden_trap": "Joining to a daily FX table using DATE(ts) loses intraday volatility and causes currency conversion discrepancies of up to 1-2% during volatile market events.",
        "duckdb_advantage": "DuckDB's ASOF JOIN enables continuous real-time currency conversion with millisecond granularity.",
        "setup_sql": """
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
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q03_clickstream_sessionization_gaps",
        "title": "Clickstream Sessionization with Inactivity Timeouts (Gaps & Islands)",
        "domain": "Temporal & Time-Series",
        "human_context": "Digital analytics platforms group raw user pageviews into 'sessions'. If a user is inactive for more than 30 minutes, the next click begins a brand-new session.",
        "hidden_trap": "Models mistakenly partition by user_id and take ROW_NUMBER(), which fails to segment sessions by time gaps, or use self-joins which scale quadratically.",
        "duckdb_advantage": "Window functions (LAG) combined with cumulative conditional sums (SUM(is_new_session) OVER) produce linear O(N) streaming session identifiers.",
        "setup_sql": """
            CREATE TABLE user_events (
                user_id INT,
                event_time TIMESTAMP,
                page_url VARCHAR
            );
            INSERT INTO user_events VALUES
                (101, '2026-03-01 10:00:00', '/home'),
                (101, '2026-03-01 10:05:00', '/products'),
                (101, '2026-03-01 10:45:00', '/checkout'), -- 40m gap -> New session
                (101, '2026-03-01 10:50:00', '/confirmation');
        """,
        "sql": """
            -- Detect session breaks (>30 min inactivity) and assign deterministic session UUIDs
            WITH event_lags AS (
                SELECT 
                    user_id,
                    event_time,
                    page_url,
                    -- Compare against preceding event timestamp for this user
                    LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_event_time
                FROM user_events
            ),
            session_flags AS (
                SELECT 
                    user_id,
                    event_time,
                    page_url,
                    -- Mark 1 if first event or gap exceeds 30 minutes, else 0
                    CASE 
                        WHEN prev_event_time IS NULL THEN 1
                        WHEN date_diff('second', prev_event_time, event_time) > 1800 THEN 1 
                        ELSE 0 
                    END AS is_new_session
                FROM event_lags
            )
            SELECT 
                user_id,
                event_time,
                page_url,
                -- Cumulative sum over flags establishes monotonically increasing session ID
                SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_time) AS session_id
            FROM session_flags
            ORDER BY user_id, event_time;
        """
    },
    {
        "id": "Q04_dual_bound_session_capping",
        "title": "Sliding Sessionization with Absolute Maximum Duration Cap",
        "domain": "Temporal & Time-Series",
        "human_context": "Real-world web sessions often need dual constraints: a 30-minute inactivity timeout AND a strict maximum 4-hour absolute session duration to prevent bots from maintaining endless sessions.",
        "hidden_trap": "A simple inactivity check keeps sessions alive indefinitely if events happen every 10 minutes. Tracking session origin requires window frames with state.",
        "duckdb_advantage": "DuckDB can evaluate nested window stages seamlessly with zero intermediate disk spill.",
        "setup_sql": """
            CREATE TABLE bot_events (
                user_id INT,
                event_time TIMESTAMP,
                action VARCHAR
            );
            INSERT INTO bot_events VALUES
                (1, '2026-03-01 00:00:00', 'ping'),
                (1, '2026-03-01 02:00:00', 'ping'), -- +2 hrs
                (1, '2026-03-01 04:30:00', 'ping'), -- +4.5 hrs (exceeds 4h cap)
                (1, '2026-03-01 04:45:00', 'ping');
        """,
        "sql": """
            -- Partition sessions by inactivity (>30m) OR exceeding 4 hours from session start
            WITH ranked_events AS (
                SELECT 
                    user_id,
                    event_time,
                    action,
                    LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_time
                FROM bot_events
            ),
            step_flags AS (
                SELECT 
                    user_id,
                    event_time,
                    action,
                    CASE 
                        WHEN prev_time IS NULL THEN 1
                        WHEN date_diff('minute', prev_time, event_time) > 30 THEN 1
                        ELSE 0
                    END AS gap_split
                FROM ranked_events
            ),
            base_sessions AS (
                SELECT 
                    *,
                    SUM(gap_split) OVER (PARTITION BY user_id ORDER BY event_time) AS raw_session_id
                FROM step_flags
            )
            SELECT 
                user_id,
                event_time,
                action,
                raw_session_id,
                -- Measure elapsed minutes from session genesis
                date_diff('minute', 
                    FIRST_VALUE(event_time) OVER (PARTITION BY user_id, raw_session_id ORDER BY event_time),
                    event_time
                ) AS minutes_since_session_start
            FROM base_sessions
            ORDER BY user_id, event_time;
        """
    },
    {
        "id": "Q05_iot_sensor_gap_fill_locf",
        "title": "IoT Sensor Telemetry Gap-Filling via generate_series and LOCF",
        "domain": "Temporal & Time-Series",
        "human_context": "Industrial IoT sensors emit readings intermittently to save bandwidth. Downstream machine learning models require strict continuous 1-minute time grids with Last Observation Carried Forward (LOCF).",
        "hidden_trap": "Using OUTER JOIN without dynamic range generation leaves temporal voids, leading to missing periods in downstream feature stores.",
        "duckdb_advantage": "DuckDB `generate_series` produces virtual timestamp arrays directly joined with windowed `IGNORE NULLS` forward-fills.",
        "setup_sql": """
            CREATE TABLE sensor_telemetry (
                device_id INT,
                recorded_at TIMESTAMP,
                temperature DOUBLE
            );
            INSERT INTO sensor_telemetry VALUES
                (42, '2026-03-01 08:00:00', 21.5),
                (42, '2026-03-01 08:02:00', 22.0),
                (42, '2026-03-01 08:05:00', 22.8);
        """,
        "sql": """
            -- Resample sparse telemetry into continuous 1-minute intervals with Last Observation Carried Forward
            WITH time_grid AS (
                SELECT UNNEST(generate_series(
                    TIMESTAMP '2026-03-01 08:00:00',
                    TIMESTAMP '2026-03-01 08:05:00',
                    INTERVAL '1 minute'
                )) AS bucket_time
            ),
            aligned_readings AS (
                SELECT 
                    grid.bucket_time,
                    42 AS device_id,
                    st.temperature
                FROM time_grid grid
                LEFT JOIN sensor_telemetry st
                  ON grid.bucket_time = st.recorded_at
                 AND st.device_id = 42
            )
            SELECT 
                bucket_time,
                device_id,
                temperature AS raw_reading,
                -- Forward fill the most recent non-null temperature
                COALESCE(
                    temperature,
                    LAST_VALUE(temperature IGNORE NULLS) OVER (
                        PARTITION BY device_id 
                        ORDER BY bucket_time 
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
                ) AS filled_temperature
            FROM aligned_readings
            ORDER BY bucket_time;
        """
    },
    {
        "id": "Q06_bitemporal_state_reconstruction",
        "title": "Bitemporal Auditing: Valid-Time vs. Transaction-Time Alignment",
        "domain": "Temporal & Time-Series",
        "human_context": "Financial compliance requires knowing: 'What did we believe customer Alice's credit limit was on May 15th, based on what was entered into our database as of June 1st?' (Bitemporal query).",
        "hidden_trap": "Relying on a single timestamp column confuses retroactive corrections with real-world effective dates, causing compliance audit failures.",
        "duckdb_advantage": "DuckDB can evaluate dual closed-open temporal intervals (`[valid_from, valid_to)` and `[system_from, system_to)`) with high-speed range predicates.",
        "setup_sql": """
            CREATE TABLE credit_limits_audit (
                customer_id INT,
                credit_limit DECIMAL(10,2),
                valid_from DATE,
                valid_to DATE,
                system_from TIMESTAMP,
                system_to TIMESTAMP
            );
            INSERT INTO credit_limits_audit VALUES
                -- Original belief entered on May 1st
                (501, 5000.00, '2026-05-01', '2026-12-31', '2026-05-01 09:00:00', '2026-06-01 10:00:00'),
                -- Retroactive correction entered on June 1st backdating Alice's limit to $8,000 effective May 15th
                (501, 8000.00, '2026-05-15', '2026-12-31', '2026-06-01 10:00:00', '9999-12-31 23:59:59');
        """,
        "sql": """
            -- Query credit limit effective on 2026-05-20 as known to the system on 2026-05-25 (before retroactive update)
            SELECT 
                customer_id,
                credit_limit AS limit_as_known_then,
                valid_from,
                valid_to,
                system_from,
                system_to
            FROM credit_limits_audit
            WHERE customer_id = 501
              -- As-of Business Date: 2026-05-20
              AND DATE '2026-05-20' >= valid_from 
              AND DATE '2026-05-20' < valid_to
              -- As-of System State: 2026-05-25
              AND TIMESTAMP '2026-05-25 00:00:00' >= system_from 
              AND TIMESTAMP '2026-05-25 00:00:00' < system_to;
        """
    },
    {
        "id": "Q07_scd2_open_ended_intervals",
        "title": "Slowly Changing Dimension Type 2 Join with Open-Ended Future",
        "domain": "Temporal & Time-Series",
        "human_context": "Customers change addresses or account tiers over time. Joining historical orders to customer profile dimensions requires matching the order date to the active validity interval.",
        "hidden_trap": "Current active records typically have `valid_to IS NULL`. A simple `order_date BETWEEN valid_from AND valid_to` drops all current active records.",
        "duckdb_advantage": "DuckDB optimizes COALESCE null bounds directly into range filter pushdown.",
        "setup_sql": """
            CREATE TABLE dim_customer_scd (
                customer_id INT,
                tier VARCHAR,
                valid_from DATE,
                valid_to DATE
            );
            CREATE TABLE fact_orders (
                order_id INT,
                customer_id INT,
                order_date DATE,
                amount DECIMAL(10,2)
            );
            INSERT INTO dim_customer_scd VALUES
                (88, 'Silver', '2026-01-01', '2026-02-01'),
                (88, 'Gold',   '2026-02-01', NULL);
            INSERT INTO fact_orders VALUES
                (1, 88, '2026-01-15', 100.00),
                (2, 88, '2026-02-20', 250.00);
        """,
        "sql": """
            -- Join fact orders to historical customer dimension without dropping active records
            SELECT 
                o.order_id,
                o.customer_id,
                o.order_date,
                o.amount,
                c.tier AS customer_tier_at_purchase
            FROM fact_orders o
            JOIN dim_customer_scd c
              ON o.customer_id = c.customer_id
             AND o.order_date >= c.valid_from
             AND o.order_date < COALESCE(c.valid_to, DATE '9999-12-31')
            ORDER BY o.order_id;
        """
    },
    {
        "id": "Q08_hopping_sliding_time_buckets",
        "title": "Hopping / Overlapping Window Aggregations via time_bucket",
        "domain": "Temporal & Time-Series",
        "human_context": "Real-time surveillance monitors rolling 15-minute average latency stepped forward every 5 minutes (a hopping window).",
        "hidden_trap": "Standard GROUP BY time_bucket only produces non-overlapping tumbling windows, missing cross-boundary bursts.",
        "duckdb_advantage": "DuckDB can evaluate multi-frequency time_bucket queries combined with generate_series hops in memory.",
        "setup_sql": """
            CREATE TABLE server_metrics (
                server_id VARCHAR,
                metric_time TIMESTAMP,
                cpu_utilization DOUBLE
            );
            INSERT INTO server_metrics VALUES
                ('web-01', '2026-03-01 10:02:00', 45.0),
                ('web-01', '2026-03-01 10:07:00', 78.0),
                ('web-01', '2026-03-01 10:12:00', 92.0),
                ('web-01', '2026-03-01 10:17:00', 60.0);
        """,
        "sql": """
            -- Generate 15-minute sliding windows stepped every 5 minutes (hopping window)
            WITH window_steps AS (
                SELECT UNNEST(generate_series(
                    TIMESTAMP '2026-03-01 10:00:00',
                    TIMESTAMP '2026-03-01 10:15:00',
                    INTERVAL '5 minutes'
                )) AS window_start
            )
            SELECT 
                w.window_start,
                w.window_start + INTERVAL '15 minutes' AS window_end,
                m.server_id,
                COUNT(m.cpu_utilization) AS sample_count,
                ROUND(AVG(m.cpu_utilization), 2) AS avg_cpu,
                MAX(m.cpu_utilization) AS peak_cpu
            FROM window_steps w
            JOIN server_metrics m
              ON m.metric_time >= w.window_start
             AND m.metric_time < w.window_start + INTERVAL '15 minutes'
            GROUP BY w.window_start, m.server_id
            ORDER BY w.window_start;
        """
    },
    {
        "id": "Q09_ledger_balance_duplicate_timestamps",
        "title": "Financial Ledger Cumulative Balance with Duplicate Timestamp Ties",
        "domain": "Temporal & Time-Series",
        "human_context": "Ledger entries can occur at the exact same millisecond. Financial ledgers must preserve strict incremental balances rather than bunching peer rows.",
        "hidden_trap": "SQL window functions default to `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which aggregates identical timestamps together into the same running total.",
        "duckdb_advantage": "Explicit `ROWS BETWEEN` frames guarantee deterministic transaction-by-transaction cumulative balances.",
        "setup_sql": """
            CREATE TABLE ledger (
                entry_id INT,
                account_id INT,
                posted_time TIMESTAMP,
                amount DECIMAL(10,2)
            );
            INSERT INTO ledger VALUES
                (1, 7001, '2026-03-01 14:00:00', 500.00),
                (2, 7001, '2026-03-01 14:00:00', -150.00), -- Duplicate timestamp
                (3, 7001, '2026-03-01 14:05:00', 200.00);
        """,
        "sql": """
            -- Calculate strict running ledger balance using ROWS frame to prevent peer bunching
            SELECT 
                entry_id,
                account_id,
                posted_time,
                amount,
                -- ROWS frame evaluates row-by-row even when posted_time is identical
                SUM(amount) OVER (
                    PARTITION BY account_id
                    ORDER BY posted_time, entry_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS running_balance
            FROM ledger
            ORDER BY posted_time, entry_id;
        """
    },
    {
        "id": "Q10_peer_exclusion_moving_average",
        "title": "Window Frame Exclusion: Peer Period Average via EXCLUDE CURRENT ROW",
        "domain": "Temporal & Time-Series",
        "human_context": "To detect anomalous spikes, analysts compare a metric against the average of neighboring days, strictly excluding the current day's value to avoid skewing the baseline.",
        "hidden_trap": "Computing rolling averages without excluding the current row inflates the baseline during the spike itself, hiding the anomaly.",
        "duckdb_advantage": "DuckDB supports standard SQL:2011 window frame exclusion clauses: `EXCLUDE CURRENT ROW`.",
        "setup_sql": """
            CREATE TABLE daily_api_calls (
                service_id VARCHAR,
                call_date DATE,
                total_calls INT
            );
            INSERT INTO daily_api_calls VALUES
                ('auth-svc', '2026-03-01', 1000),
                ('auth-svc', '2026-03-02', 1050),
                ('auth-svc', '2026-03-03', 9500), -- Major spike
                ('auth-svc', '2026-03-04', 1020),
                ('auth-svc', '2026-03-05', 1010);
        """,
        "sql": """
            -- Calculate 5-day baseline average strictly excluding current row
            SELECT 
                service_id,
                call_date,
                total_calls,
                -- 2 days before and 2 days after, excluding current day
                ROUND(AVG(total_calls) OVER (
                    PARTITION BY service_id
                    ORDER BY call_date
                    ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
                    EXCLUDE CURRENT ROW
                ), 2) AS peer_baseline_avg,
                -- Spikiness ratio
                ROUND(total_calls / AVG(total_calls) OVER (
                    PARTITION BY service_id
                    ORDER BY call_date
                    ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
                    EXCLUDE CURRENT ROW
                ), 2) AS spike_factor
            FROM daily_api_calls
            ORDER BY call_date;
        """
    },
    {
        "id": "Q11_exclude_ties_ranking",
        "title": "Excluding Ties in Percentile Ranks via EXCLUDE TIES",
        "domain": "Temporal & Time-Series",
        "human_context": "When evaluating employee sales performance, ties should not inflate the percentile score against colleagues who achieved the exact same result.",
        "hidden_trap": "Using standard RANK() causes tied individuals to push each other's percentiles higher or lower inconsistently.",
        "duckdb_advantage": "DuckDB's `EXCLUDE TIES` window frame syntax accurately handles identical duplicate metrics.",
        "setup_sql": """
            CREATE TABLE rep_sales (
                rep_id INT,
                sales_quota_achieved DECIMAL(5,2)
            );
            INSERT INTO rep_sales VALUES
                (1, 120.00),
                (2, 115.00),
                (3, 115.00), -- Tie
                (4, 95.00);
        """,
        "sql": """
            -- Compute cumulative sales sum excluding tied peers in current row calculation
            SELECT 
                rep_id,
                sales_quota_achieved,
                SUM(sales_quota_achieved) OVER (
                    ORDER BY sales_quota_achieved DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    EXCLUDE TIES
                ) AS cumulative_sales_exclusive_of_ties
            FROM rep_sales
            ORDER BY sales_quota_achieved DESC, rep_id;
        """
    },
    {
        "id": "Q12_microsecond_latency_jitter",
        "title": "Inter-Packet Network Arrival Jitter at Nanosecond Resolution",
        "domain": "Temporal & Time-Series",
        "human_context": "High-speed network telemetry measures packet arrival jitter (variance in inter-packet delay). Jitter spikes indicate network congestion or buffer bloat.",
        "hidden_trap": "Standard SQL datetime arithmetic truncates to milliseconds or seconds, losing high-frequency microsecond microbursts.",
        "duckdb_advantage": "DuckDB natively supports `epoch_ns` and TIMESTAMP with microsecond/nanosecond fidelity.",
        "setup_sql": """
            CREATE TABLE packet_stream (
                packet_id INT,
                captured_at TIMESTAMP
            );
            INSERT INTO packet_stream VALUES
                (1, '2026-03-01 12:00:00.000100'),
                (2, '2026-03-01 12:00:00.000150'), -- +50us
                (3, '2026-03-01 12:00:00.000300'), -- +150us (jitter spike)
                (4, '2026-03-01 12:00:00.000350');
        """,
        "sql": """
            -- Compute inter-packet arrival delta in microseconds and identify variance
            WITH deltas AS (
                SELECT 
                    packet_id,
                    captured_at,
                    date_diff('microsecond', 
                        LAG(captured_at) OVER (ORDER BY captured_at), 
                        captured_at
                    ) AS delta_microseconds
                FROM packet_stream
            )
            SELECT 
                packet_id,
                captured_at,
                delta_microseconds,
                -- Measure moving jitter variance over last 3 packets
                ROUND(STDDEV(delta_microseconds) OVER (
                    ORDER BY captured_at 
                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                ), 2) AS rolling_jitter_stddev
            FROM deltas
            ORDER BY captured_at;
        """
    },
    {
        "id": "Q13_order_book_snapshot_reconstruction",
        "title": "Point-in-Time Limit Order Book (LOB) State Reconstruction",
        "domain": "Temporal & Time-Series",
        "human_context": "Market microstructure researchers need to reconstruct the exact bids and asks available at an arbitrary point in time from an append-only event stream of place, cancel, and fill orders.",
        "hidden_trap": "Summing active orders without filtering out cancellations that occurred before the target time produces a phantom order book.",
        "duckdb_advantage": "DuckDB can evaluate event lifespans and aggregate active depth efficiently in a single scan.",
        "setup_sql": """
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
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q14_time_weighted_average_price_twap",
        "title": "Time-Weighted Average Price (TWAP) with Variable Interval Weights",
        "domain": "Temporal & Time-Series",
        "human_context": "TWAP measures the average price of an asset weighted by the duration of time that each price level was sustained, preventing brief price spikes from distorting valuation.",
        "hidden_trap": "Taking simple AVG(price) biases the result towards periods with frequent tick updates rather than sustained duration.",
        "duckdb_advantage": "DuckDB LEAD functions cleanly calculate elapsed durations between price revisions.",
        "setup_sql": """
            CREATE TABLE price_ticks (
                tick_time TIMESTAMP,
                symbol VARCHAR,
                price DOUBLE
            );
            INSERT INTO price_ticks VALUES
                ('2026-03-01 10:00:00', 'ETH', 3000.00), -- lasted 10 min
                ('2026-03-01 10:10:00', 'ETH', 3050.00), -- lasted 20 min
                ('2026-03-01 10:30:00', 'ETH', 3010.00), -- lasted 30 min
                ('2026-03-01 11:00:00', 'ETH', 3010.00); -- window end
        """,
        "sql": """
            -- Calculate 1-hour TWAP from 10:00 to 11:00
            WITH tick_durations AS (
                SELECT 
                    symbol,
                    tick_time,
                    price,
                    date_diff('second', tick_time, 
                        LEAD(tick_time, 1, TIMESTAMP '2026-03-01 11:00:00') OVER (PARTITION BY symbol ORDER BY tick_time)
                    ) AS duration_seconds
                FROM price_ticks
                WHERE tick_time < TIMESTAMP '2026-03-01 11:00:00'
            )
            SELECT 
                symbol,
                ROUND(SUM(price * duration_seconds) / SUM(duration_seconds), 2) AS twap_price,
                SUM(duration_seconds) AS total_duration_seconds
            FROM tick_durations
            GROUP BY symbol;
        """
    },
    {
        "id": "Q15_volume_weighted_average_price_vwap",
        "title": "Intraday Volume-Weighted Average Price (VWAP) Resetting Daily",
        "domain": "Temporal & Time-Series",
        "human_context": "VWAP provides institutional traders the definitive benchmark price weighted by traded volume, resetting to zero at the start of every trading day.",
        "hidden_trap": "Failing to partition by trading date mixes multi-day volume into the intraday numerator and denominator.",
        "duckdb_advantage": "DuckDB calculates cumulative sums in a single pass without subqueries.",
        "setup_sql": """
            CREATE TABLE market_trades (
                symbol VARCHAR,
                trade_time TIMESTAMP,
                price DOUBLE,
                volume INT
            );
            INSERT INTO market_trades VALUES
                ('AAPL', '2026-03-01 09:35:00', 180.00, 1000),
                ('AAPL', '2026-03-01 09:40:00', 181.00, 2000),
                ('AAPL', '2026-03-02 09:35:00', 182.00, 500); -- Next day reset
        """,
        "sql": """
            -- Intraday continuous VWAP calculation
            SELECT 
                symbol,
                trade_time,
                price,
                volume,
                ROUND(
                    SUM(price * volume) OVER (
                        PARTITION BY symbol, CAST(trade_time AS DATE)
                        ORDER BY trade_time
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) / 
                    SUM(volume) OVER (
                        PARTITION BY symbol, CAST(trade_time AS DATE)
                        ORDER BY trade_time
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ), 2
                ) AS intraday_vwap
            FROM market_trades
            ORDER BY symbol, trade_time;
        """
    },
    {
        "id": "Q16_sequential_funnel_precedence",
        "title": "Chronological Multi-Stage Conversion Funnel with Time Boundaries",
        "domain": "Temporal & Time-Series",
        "human_context": "In product funnels (Signup -> Verify -> Purchase), events must occur in exact chronological order, with each step completed within 24 hours of the previous.",
        "hidden_trap": "Models join events without checking timestamp ordering (e.g., verifying after purchase), artificially inflating funnel conversion.",
        "duckdb_advantage": "DuckDB QUALIFY and chained CTEs preserve strict chronological order with pushdown predicates.",
        "setup_sql": """
            CREATE TABLE user_actions (
                user_id INT,
                stage VARCHAR,
                action_time TIMESTAMP
            );
            INSERT INTO user_actions VALUES
                (1, 'signup',   '2026-03-01 10:00:00'),
                (1, 'verify',   '2026-03-01 11:00:00'),
                (1, 'purchase', '2026-03-01 15:00:00'),
                (2, 'signup',   '2026-03-01 10:00:00'),
                (2, 'purchase', '2026-03-01 10:30:00'); -- Skipped verify
        """,
        "sql": """
            -- Enforce Signup -> Verify -> Purchase chronological order
            WITH step1 AS (
                SELECT user_id, action_time AS signup_time
                FROM user_actions
                WHERE stage = 'signup'
            ),
            step2 AS (
                SELECT s1.user_id, s1.signup_time, MIN(a.action_time) AS verify_time
                FROM step1 s1
                JOIN user_actions a 
                  ON s1.user_id = a.user_id 
                 AND a.stage = 'verify'
                 AND a.action_time >= s1.signup_time
                 AND a.action_time <= s1.signup_time + INTERVAL '24 hours'
                GROUP BY s1.user_id, s1.signup_time
            ),
            step3 AS (
                SELECT s2.user_id, s2.signup_time, s2.verify_time, MIN(a.action_time) AS purchase_time
                FROM step2 s2
                JOIN user_actions a 
                  ON s2.user_id = a.user_id 
                 AND a.stage = 'purchase'
                 AND a.action_time >= s2.verify_time
                 AND a.action_time <= s2.verify_time + INTERVAL '24 hours'
                GROUP BY s2.user_id, s2.signup_time, s2.verify_time
            )
            SELECT 
                COUNT(s1.user_id) AS total_signups,
                COUNT(s2.user_id) AS verified_users,
                COUNT(s3.user_id) AS completed_purchasers,
                ROUND(COUNT(s3.user_id) * 100.0 / COUNT(s1.user_id), 1) AS end_to_end_conversion_pct
            FROM step1 s1
            LEFT JOIN step2 s2 ON s1.user_id = s2.user_id
            LEFT JOIN step3 s3 ON s1.user_id = s3.user_id;
        """
    },
    {
        "id": "Q17_retention_cohort_survival",
        "title": "Dynamic User Retention Cohort Matrix by Weekly Milestones",
        "domain": "Temporal & Time-Series",
        "human_context": "SaaS analytics track weekly retention curves (Day 0, Day 7, Day 14, Day 30) based on user signup week.",
        "hidden_trap": "Calculating retention without dynamic date grouping produces rigid, fragile queries requiring manual updates every week.",
        "duckdb_advantage": "DuckDB date_trunc and conditional aggregation build clean dynamic cohort tables.",
        "setup_sql": """
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
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q18_time_decay_user_affinity",
        "title": "Exponential Time-Decayed User Affinity Scoring",
        "domain": "Temporal & Time-Series",
        "human_context": "Recommendation systems score user interest where recent clicks count significantly more than clicks from 30 days ago, modeled via exponential decay: score * e^(-lambda * delta_days).",
        "hidden_trap": "Equal-weight counts overemphasize obsolete user interests from months ago.",
        "duckdb_advantage": "DuckDB vector math supports mathematical functions (`EXP`, `POW`) directly in aggregation pipelines.",
        "setup_sql": """
            CREATE TABLE item_clicks (
                user_id INT,
                category VARCHAR,
                click_time TIMESTAMP
            );
            INSERT INTO item_clicks VALUES
                (99, 'laptops', '2026-03-01 10:00:00'), -- Today
                (99, 'laptops', '2026-02-20 10:00:00'), -- 9 days ago
                (99, 'shoes',   '2026-01-01 10:00:00'); -- 60 days ago
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q19_intermittent_inactivity_anomaly",
        "title": "Customer Churn Anomaly Detection vs Historical Purchase Rhythm",
        "domain": "Temporal & Time-Series",
        "human_context": "A customer who normally buys every 3 days is at risk if they haven't bought in 10 days. But a customer who buys quarterly is not. Churn detection must be personalized to each user's cadence.",
        "hidden_trap": "Static 30-day churn thresholds misflag seasonal or low-frequency high-value customers.",
        "duckdb_advantage": "DuckDB window functions compute user-specific median purchase intervals.",
        "setup_sql": """
            CREATE TABLE orders_history (
                customer_id INT,
                order_date DATE
            );
            INSERT INTO orders_history VALUES
                (1, '2026-01-01'), (1, '2026-01-04'), (1, '2026-01-07'), -- Rhythm: 3 days
                (2, '2026-01-01'), (2, '2026-02-01'), (2, '2026-03-01'); -- Rhythm: 30 days
        """,
        "sql": """
            -- Calculate median inter-purchase days and compare against days elapsed since latest order
            WITH purchase_intervals AS (
                SELECT 
                    customer_id,
                    order_date,
                    order_date - LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS days_between
                FROM orders_history
            ),
            user_cadence AS (
                SELECT 
                    customer_id,
                    MAX(order_date) AS last_order_date,
                    MEDIAN(days_between) AS median_purchase_interval_days
                FROM purchase_intervals
                GROUP BY customer_id
            )
            SELECT 
                customer_id,
                last_order_date,
                median_purchase_interval_days,
                (DATE '2026-03-10' - last_order_date) AS days_since_last_order,
                CASE 
                    WHEN (DATE '2026-03-10' - last_order_date) > (2.5 * median_purchase_interval_days) 
                    THEN 'HIGH_CHURN_RISK' 
                    ELSE 'NORMAL' 
                END AS churn_risk_status
            FROM user_cadence
            ORDER BY customer_id;
        """
    },
    {
        "id": "Q20_interval_overlap_concurrency",
        "title": "Peak Concurrent Workforce Capacity via Interval Overlap Scan",
        "domain": "Temporal & Time-Series",
        "human_context": "Workforce managers must calculate maximum concurrent staffing levels from employee shift start and end times to ensure warehouse safety limits are never breached.",
        "hidden_trap": "Pairwise self-joins between overlapping shifts blow up to O(N^2) complexity.",
        "duckdb_advantage": "Transforming shifts into discrete (+1 start, -1 end) point events reduces peak concurrency calculation to a single O(N log N) streaming pass.",
        "setup_sql": """
            CREATE TABLE staff_shifts (
                shift_id INT,
                worker_id INT,
                start_time TIMESTAMP,
                end_time TIMESTAMP
            );
            INSERT INTO staff_shifts VALUES
                (1, 101, '2026-03-01 08:00:00', '2026-03-01 12:00:00'),
                (2, 102, '2026-03-01 09:00:00', '2026-03-01 13:00:00'),
                (3, 103, '2026-03-01 10:00:00', '2026-03-01 11:30:00');
        """,
        "sql": """
            -- Transform start/end intervals into delta events and compute peak concurrent staffing
            WITH shift_events AS (
                SELECT start_time AS event_time, 1 AS delta FROM staff_shifts
                UNION ALL
                SELECT end_time AS event_time, -1 AS delta FROM staff_shifts
            ),
            running_occupancy AS (
                SELECT 
                    event_time,
                    SUM(delta) OVER (ORDER BY event_time, delta DESC) AS concurrent_workers
                FROM shift_events
            )
            SELECT 
                MAX(concurrent_workers) AS peak_concurrent_workers
            FROM running_occupancy;
        """
    },
    {
        "id": "Q21_temporal_gap_detection",
        "title": "Continuous Asset Lease Unallocated Gap Discovery",
        "domain": "Temporal & Time-Series",
        "human_context": "Fleet managers track commercial vehicles to find idle 'unrented' gaps between back-to-back rental contracts for fleet utilization auditing.",
        "hidden_trap": "Comparing each row with LEAD without filtering where next_start > current_end misses adjacent non-overlapping bookings.",
        "duckdb_advantage": "DuckDB window functions compute discrete idle intervals in a single scan.",
        "setup_sql": """
            CREATE TABLE vehicle_leases (
                vehicle_id INT,
                lease_start DATE,
                lease_end DATE
            );
            INSERT INTO vehicle_leases VALUES
                (55, '2026-01-01', '2026-01-10'),
                (55, '2026-01-15', '2026-01-20'), -- 5 day gap (Jan 10 - Jan 15)
                (55, '2026-01-20', '2026-01-30'); -- contiguous
        """,
        "sql": """
            -- Identify idle intervals between vehicle leases
            WITH lease_boundaries AS (
                SELECT 
                    vehicle_id,
                    lease_end AS gap_start,
                    LEAD(lease_start) OVER (PARTITION BY vehicle_id ORDER BY lease_start) AS gap_end
                FROM vehicle_leases
            )
            SELECT 
                vehicle_id,
                gap_start,
                gap_end,
                (gap_end - gap_start) AS idle_days
            FROM lease_boundaries
            WHERE gap_end IS NOT NULL 
              AND gap_end > gap_start
            ORDER BY vehicle_id, gap_start;
        """
    },
    {
        "id": "Q22_linear_interpolation_missing_points",
        "title": "Bi-directional Linear Value Interpolation between Observations",
        "domain": "Temporal & Time-Series",
        "human_context": "When a sensor drops offline for 30 minutes, data scientists prefer linear interpolation between the last known reading and the next recovered reading rather than flat zero-filling.",
        "hidden_trap": "Requires simultaneous look-behind (LAG) and look-ahead (LEAD) across varying time distances.",
        "duckdb_advantage": "DuckDB calculates multi-point interpolation in a single query.",
        "setup_sql": """
            CREATE TABLE pressure_readings (
                ts TIMESTAMP,
                psi DOUBLE
            );
            INSERT INTO pressure_readings VALUES
                ('2026-03-01 10:00:00', 100.0),
                ('2026-03-01 10:01:00', NULL),
                ('2026-03-01 10:02:00', NULL),
                ('2026-03-01 10:03:00', 130.0);
        """,
        "sql": """
            -- Linearly interpolate missing PSI values based on preceding and following known points
            WITH bounds AS (
                SELECT 
                    ts,
                    psi,
                    LAST_VALUE(psi IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS prev_psi,
                    LAST_VALUE(ts IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS prev_ts,
                    FIRST_VALUE(psi IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS next_psi,
                    FIRST_VALUE(ts IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS next_ts
                FROM pressure_readings
            )
            SELECT 
                ts,
                psi AS raw_psi,
                CASE 
                    WHEN psi IS NOT NULL THEN psi
                    ELSE ROUND(
                        prev_psi + (next_psi - prev_psi) * 
                        (date_diff('second', prev_ts, ts) * 1.0 / date_diff('second', prev_ts, next_ts)), 2
                    )
                END AS interpolated_psi
            FROM bounds
            ORDER BY ts;
        """
    },
    {
        "id": "Q23_trimmed_mean_rolling_window",
        "title": "Outlier-Resistant Rolling Window (Trimmed Mean Aggregation)",
        "domain": "Temporal & Time-Series",
        "human_context": "Financial risk models compute a 7-day rolling average excluding the highest and lowest single observations in each 7-day window to eliminate transient flash crashes.",
        "hidden_trap": "Writing self-joins with sub-aggregations to filter min/max results in huge query execution trees.",
        "duckdb_advantage": "DuckDB window functions compute rolling sum, min, and max in parallel O(1) passes.",
        "setup_sql": """
            CREATE TABLE daily_settlement (
                trade_date DATE,
                settlement_amount DOUBLE
            );
            INSERT INTO daily_settlement VALUES
                ('2026-03-01', 50.0),
                ('2026-03-02', 52.0),
                ('2026-03-03', 500.0), -- Flash spike outlier
                ('2026-03-04', 51.0),
                ('2026-03-05', 49.0);
        """,
        "sql": """
            -- Calculate trimmed rolling mean excluding min and max values within a 5-day window
            WITH windowed_stats AS (
                SELECT 
                    trade_date,
                    settlement_amount,
                    COUNT(*) OVER w AS win_count,
                    SUM(settlement_amount) OVER w AS win_sum,
                    MIN(settlement_amount) OVER w AS win_min,
                    MAX(settlement_amount) OVER w AS win_max
                FROM daily_settlement
                WINDOW w AS (ORDER BY trade_date ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING)
            )
            SELECT 
                trade_date,
                settlement_amount,
                -- Subtract min and max from sum and divide by (count - 2)
                CASE 
                    WHEN win_count > 2 THEN ROUND((win_sum - win_min - win_max) / (win_count - 2), 2)
                    ELSE settlement_amount
                END AS trimmed_mean_5d
            FROM windowed_stats
            ORDER BY trade_date;
        """
    },
    {
        "id": "Q24_sargable_fiscal_partition_prune",
        "title": "SARGable Fiscal Year Date Range Partition Pruning",
        "domain": "Temporal & Time-Series",
        "human_context": "Data warehouses partition petabyte event tables by date. Wrapping date columns in functions (e.g. `WHERE strftime('%Y', event_time) = '2026'`) breaks partition pruning, forcing a full table scan.",
        "hidden_trap": "Non-SARGable functions force DuckDB/Snowflake to scan every Parquet row group.",
        "duckdb_advantage": "Direct boundary comparison (`>= '2026-01-01' AND < '2027-01-01'`) allows DuckDB to prune Parquet files via metadata statistics.",
        "setup_sql": """
            CREATE TABLE telemetry_partitions (
                event_id INT,
                event_timestamp TIMESTAMP,
                payload VARCHAR
            );
            INSERT INTO telemetry_partitions VALUES
                (1, '2025-12-31 23:59:59', 'old'),
                (2, '2026-01-01 00:00:00', 'target_start'),
                (3, '2026-06-15 12:00:00', 'target_mid'),
                (4, '2027-01-01 00:00:00', 'out_of_bounds');
        """,
        "sql": """
            -- Exact SARGable half-open date boundary pruning
            SELECT 
                event_id,
                event_timestamp,
                payload
            FROM telemetry_partitions
            WHERE event_timestamp >= TIMESTAMP '2026-01-01 00:00:00'
              AND event_timestamp <  TIMESTAMP '2027-01-01 00:00:00'
            ORDER BY event_timestamp;
        """
    },
    {
        "id": "Q25_multi_touch_marketing_attribution",
        "title": "Multi-Touch Marketing Attribution Comparison in a Single Pass",
        "domain": "Temporal & Time-Series",
        "human_context": "CMOs need to compare 3 attribution models (First-Touch, Last-Touch, and Uniform Linear) for touchpoints occurring within 30 days prior to conversion.",
        "hidden_trap": "Running three separate join queries triples warehouse compute costs and risks data inconsistency.",
        "duckdb_advantage": "DuckDB window functions compute First-Touch, Last-Touch, and touchpoint counts simultaneously in one query.",
        "setup_sql": """
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
        """,
        "sql": """
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
        """
    }
]
