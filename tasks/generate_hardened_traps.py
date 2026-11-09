import json
import os
import duckdb
import pandas as pd

HARDENED_TASKS = [
    {
        "id": "task_111_rolling_distinct_active_users",
        "name": "Rolling 7-Day Distinct Active Users without Triangular Join Explosion",
        "category": "Algorithmic Efficiency / Window Distinct",
        "description": "Calculates rolling 7-day distinct active users per calendar day. SQL window functions forbid COUNT(DISTINCT) over range frames, causing frontier models to generate catastrophic O(N^2) triangular self-joins that blow up memory.",
        "prompt": """Calculate the rolling 7-day distinct active user count for each active date.
For each date, count distinct users active on that date or within the preceding 6 days (total 7 calendar days).

Required output columns:
- report_date (DATE)
- rolling_7d_active_users (BIGINT)

Order results by report_date ASC.""",
        "setup_sql": """
CREATE TABLE user_activity (user_id INT, activity_date DATE);
INSERT INTO user_activity VALUES
  (101, '2026-03-01'), (102, '2026-03-01'),
  (101, '2026-03-02'), (103, '2026-03-02'),
  (104, '2026-03-03'),
  (101, '2026-03-05'),
  (102, '2026-03-08'), (105, '2026-03-08');
""",
        "golden_sql": """
WITH daily_users AS (
    SELECT activity_date, list(DISTINCT user_id) AS user_list
    FROM user_activity
    GROUP BY activity_date
),
distinct_dates AS (
    SELECT DISTINCT activity_date AS report_date FROM user_activity
)
SELECT 
    d.report_date,
    (
        SELECT COUNT(DISTINCT u)
        FROM (
            SELECT UNNEST(user_list) AS u
            FROM daily_users sub
            WHERE sub.activity_date BETWEEN d.report_date - INTERVAL 6 DAYS AND d.report_date
        )
    ) AS rolling_7d_active_users
FROM distinct_dates d
ORDER BY d.report_date ASC;
""",
        "naive_llm_sql": """
SELECT 
    a.activity_date AS report_date,
    COUNT(DISTINCT b.user_id) AS rolling_7d_active_users
FROM user_activity a
JOIN user_activity b 
  ON b.activity_date BETWEEN a.activity_date - INTERVAL 6 DAYS AND a.activity_date
GROUP BY a.activity_date
ORDER BY a.activity_date ASC;
""",
        "ordered": True,
        "expected_columns": ["report_date", "rolling_7d_active_users"],
        "efficiency_rules": {
            "disallowed_operators": ["PIECEWISE_MERGE_JOIN", "IE_JOIN", "BLOCKWISE_NL_JOIN"]
        },
        "why_it_fails": "Joining user_activity directly to itself on an inequality date range produces an O(N^2) Cartesian row explosion. For 1M rows, an unaggregated triangular join emits over 7M intermediate rows and triggers an IE_JOIN or Nested Loop join, overflowing RAM. The optimal pattern aggregates users into daily sets first before evaluating rolling intervals."
    },
    {
        "id": "task_112_dual_constraint_sessionization",
        "name": "Dual-Constraint Sessionization: 30-min Inactivity AND 4-Hour Absolute Hard Cap",
        "category": "Sessionization (Gaps & Islands)",
        "description": "Groups web clickstream events into sessions. A new session starts if: 1) more than 30 minutes pass between consecutive events, OR 2) more than 4 hours have elapsed since the session genesis event.",
        "prompt": """Segment user event stream into deterministic sessions under dual constraints:
1. An inactivity gap of > 30 minutes begins a new session.
2. An absolute duration of > 4 hours from the start of the current session begins a new session (preventing bots or perpetual sessions from running indefinitely).

Required output columns:
- user_id (INT)
- event_time (TIMESTAMP)
- session_id (BIGINT)

Order results by user_id ASC, event_time ASC.""",
        "setup_sql": """
CREATE TABLE clickstream_events (user_id INT, event_time TIMESTAMP);
-- 10 events spaced exactly 28 minutes apart (< 30m inactivity gap, but spans 4h 12m from genesis)
INSERT INTO clickstream_events 
SELECT 1, TIMESTAMP '2026-03-01 08:00:00' + (i * INTERVAL '28 minutes')
FROM range(10) t(i);
""",
        "golden_sql": """
WITH step_lags AS (
    SELECT 
        user_id,
        event_time,
        LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_time
    FROM clickstream_events
),
inactivity_flags AS (
    SELECT 
        user_id,
        event_time,
        CASE 
            WHEN prev_time IS NULL OR date_diff('second', prev_time, event_time) > 1800 THEN 1
            ELSE 0
        END AS is_inactivity_break
    FROM step_lags
),
base_sessions AS (
    SELECT 
        user_id,
        event_time,
        SUM(is_inactivity_break) OVER (PARTITION BY user_id ORDER BY event_time) AS base_sess
    FROM inactivity_flags
),
genesis_diff AS (
    SELECT 
        user_id,
        event_time,
        base_sess,
        date_diff('second', FIRST_VALUE(event_time) OVER (PARTITION BY user_id, base_sess ORDER BY event_time), event_time) AS elapsed_from_start
    FROM base_sessions
)
SELECT 
    user_id,
    event_time,
    (base_sess + (elapsed_from_start > 14400)::INT)::BIGINT AS session_id
FROM genesis_diff
ORDER BY user_id ASC, event_time ASC;
""",
        "naive_llm_sql": """
WITH step_lags AS (
    SELECT 
        user_id,
        event_time,
        LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_time
    FROM clickstream_events
)
SELECT 
    user_id,
    event_time,
    SUM(CASE WHEN prev_time IS NULL OR date_diff('second', prev_time, event_time) > 1800 THEN 1 ELSE 0 END) OVER (
        PARTITION BY user_id ORDER BY event_time
    )::BIGINT AS session_id
FROM step_lags
ORDER BY user_id ASC, event_time ASC;
""",
        "ordered": True,
        "expected_columns": ["user_id", "event_time", "session_id"],
        "efficiency_rules": {},
        "why_it_fails": "Frontier models only check the consecutive step lag (> 30 min). When an automated bot or persistent user emits events every 15 minutes continuously for 12 hours, the naive query leaves them in a single endless session, completely violating the 4-hour max session cap constraint."
    },
    {
        "id": "task_113_vector_prefilter_recall_drop",
        "name": "Vector Nearest Neighbors: The Post-Filtering Empty Set Trap",
        "category": "Vector & Retrieval",
        "description": "Demonstrates the classic vector database failure mode where applying relational metadata filters AFTER Top-K vector retrieval discards valid results, returning an empty result set.",
        "prompt": """Retrieve the top 2 most semantically relevant products matching query vector [1.0, 0.0]::FLOAT[2] satisfying:
- category = 'electronics'
- price <= 50.00
- in_stock = true

Required output columns:
- item_id (INT)
- price (DECIMAL)
- similarity (DOUBLE)

Order by similarity DESC, item_id ASC. Limit to 2 results.""",
        "setup_sql": """
CREATE TABLE products_search (
    item_id INT,
    category VARCHAR,
    price DECIMAL(10,2),
    in_stock BOOLEAN,
    vec FLOAT[2]
);
-- Top 3 highest similarity vectors globally fail the filters (too expensive or out of stock)
INSERT INTO products_search VALUES
  (1, 'electronics', 150.00, true,  [0.99, 0.01]::FLOAT[2]),
  (2, 'clothing',     20.00, true,  [0.98, 0.02]::FLOAT[2]),
  (3, 'electronics',  45.00, false, [0.95, 0.05]::FLOAT[2]),
  -- Truly qualifying products (lower global cosine similarity, but fully satisfy constraints)
  (4, 'electronics',  35.00, true,  [0.70, 0.30]::FLOAT[2]),
  (5, 'electronics',  25.00, true,  [0.65, 0.35]::FLOAT[2]);
""",
        "golden_sql": """
SELECT 
    item_id,
    price,
    ROUND(array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]), 4) AS similarity
FROM products_search
WHERE category = 'electronics' 
  AND price <= 50.00 
  AND in_stock = true
ORDER BY similarity DESC, item_id ASC
LIMIT 2;
""",
        "naive_llm_sql": """
SELECT 
    item_id,
    price,
    ROUND(similarity, 4) AS similarity
FROM (
    SELECT 
        item_id, 
        category, 
        price, 
        in_stock, 
        array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) AS similarity
    FROM products_search
    ORDER BY similarity DESC
    LIMIT 2
) sub
WHERE category = 'electronics' 
  AND price <= 50.00 
  AND in_stock = true
ORDER BY similarity DESC, item_id ASC;
""",
        "ordered": True,
        "expected_columns": ["item_id", "price", "similarity"],
        "efficiency_rules": {},
        "why_it_fails": "Post-filtering vector retrieval (LIMIT 2 inside a subquery before WHERE filters) selects the globally highest similarity items (item 1 and item 2). Because item 1 is $150 (exceeds $50) and item 2 is 'clothing', the outer WHERE filter discards both, returning 0 rows! Relational filters must be applied as PRE-FILTERS."
    },
    {
        "id": "task_114_asof_tolerance_expiry",
        "name": "ASOF Point-in-Time Quote Matching with 500ms Expiry Tolerance",
        "category": "Temporal & Time-Series",
        "description": "Matches executed trades with the prevailing market quote as-of the trade timestamp, but enforces a strict 500ms staleness tolerance. Stale market data must not be matched.",
        "prompt": """Match each executed trade with the most recent prevailing market quote.
CRITICAL CONSTRAINT: If the most recent quote is older than 500 milliseconds prior to the trade execution time, the quote is considered stale and must be returned as NULL.

Required output columns:
- trade_id (INT)
- trade_time (TIMESTAMP)
- symbol (VARCHAR)
- prevailing_ask (DOUBLE)

Order by trade_id ASC.""",
        "setup_sql": """
CREATE TABLE market_quotes (quote_time TIMESTAMP, symbol VARCHAR, bid DOUBLE, ask DOUBLE);
CREATE TABLE market_trades (trade_id INT, trade_time TIMESTAMP, symbol VARCHAR, shares INT);

-- Quote 1: 10:00:00 (Stale for trade at 10:02:00)
-- Quote 2: 10:05:00 (Fresh for trade at 10:05:00.200)
INSERT INTO market_quotes VALUES
  ('2026-03-01 10:00:00', 'AAPL', 150.00, 150.10),
  ('2026-03-01 10:05:00', 'AAPL', 151.00, 151.10);

INSERT INTO market_trades VALUES
  (1, '2026-03-01 10:02:00', 'AAPL', 100),         -- 2 minutes after Quote 1 -> STALE (>500ms) -> NULL
  (2, '2026-03-01 10:05:00.200', 'AAPL', 200);     -- 200ms after Quote 2 -> FRESH (<=500ms) -> 151.10
""",
        "golden_sql": """
SELECT 
    t.trade_id,
    t.trade_time,
    t.symbol,
    CASE 
        WHEN date_diff('millisecond', q.quote_time, t.trade_time) <= 500 
        THEN q.ask 
        ELSE NULL 
    END AS prevailing_ask
FROM market_trades t
ASOF JOIN market_quotes q
  ON t.symbol = q.symbol 
 AND t.trade_time >= q.quote_time
ORDER BY t.trade_id ASC;
""",
        "naive_llm_sql": """
SELECT 
    t.trade_id,
    t.trade_time,
    t.symbol,
    q.ask AS prevailing_ask
FROM market_trades t
ASOF JOIN market_quotes q
  ON t.symbol = q.symbol 
 AND t.trade_time >= q.quote_time
ORDER BY t.trade_id ASC;
""",
        "ordered": True,
        "expected_columns": ["trade_id", "trade_time", "symbol", "prevailing_ask"],
        "efficiency_rules": {},
        "why_it_fails": "Standard ASOF joins without a staleness tolerance check blindly match trades to arbitrarily old quotes from hours or days ago. For Trade 1, naive SQL matches the 2-minute-old quote ($150.10) instead of returning NULL, resulting in stale execution data."
    },
    {
        "id": "task_115_rrf_hybrid_rank_fusion_isolation",
        "name": "Reciprocal Rank Fusion (RRF) Hybrid Retrieval without Scale Collapse",
        "category": "Search & Retrieval",
        "description": "Fuses BM25 keyword rankings and vector cosine similarity rankings using rank-based Reciprocal Rank Fusion (k=60), preventing unbounded BM25 scores from dominating vector scores.",
        "prompt": """Combine sparse BM25 lexical scores and dense vector similarity scores using Reciprocal Rank Fusion (RRF):
RRF_Score = 1.0 / (60.0 + bm25_rank) + 1.0 / (60.0 + vector_rank)

Required output columns:
- doc_id (INT)
- title (VARCHAR)
- bm25_rank (BIGINT)
- vector_rank (BIGINT)
- rrf_score (DOUBLE)

Order by rrf_score DESC, doc_id ASC.""",
        "setup_sql": """
CREATE TABLE search_index (
    doc_id INT,
    title VARCHAR,
    bm25_raw DOUBLE,
    vec FLOAT[2]
);
-- Doc 1: Massive BM25 score, poor vector match
-- Doc 2: Balanced high BM25 and high vector match
-- Doc 3: Perfect vector match, moderate BM25
INSERT INTO search_index VALUES
  (1, 'PostgreSQL Manual', 450.0, [0.1, 0.9]::FLOAT[2]),
  (2, 'DuckDB Architecture', 80.0, [0.95, 0.05]::FLOAT[2]),
  (3, 'Vector Search Guide', 60.0, [0.99, 0.01]::FLOAT[2]);
""",
        "golden_sql": """
WITH ranked_bm25 AS (
    SELECT 
        doc_id,
        title,
        ROW_NUMBER() OVER (ORDER BY bm25_raw DESC, doc_id ASC) AS bm25_rank
    FROM search_index
),
ranked_vector AS (
    SELECT 
        doc_id,
        title,
        ROW_NUMBER() OVER (
            ORDER BY array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) DESC, doc_id ASC
        ) AS vector_rank
    FROM search_index
)
SELECT 
    b.doc_id,
    b.title,
    b.bm25_rank,
    v.vector_rank,
    ROUND((1.0 / (60.0 + b.bm25_rank)) + (1.0 / (60.0 + v.vector_rank)), 6) AS rrf_score
FROM ranked_bm25 b
JOIN ranked_vector v ON b.doc_id = v.doc_id
ORDER BY rrf_score DESC, b.doc_id ASC;
""",
        "naive_llm_sql": """
SELECT 
    doc_id,
    title,
    1::BIGINT AS bm25_rank,
    1::BIGINT AS vector_rank,
    ROUND(bm25_raw + array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]), 6) AS rrf_score
FROM search_index
ORDER BY rrf_score DESC, doc_id ASC;
""",
        "ordered": True,
        "expected_columns": ["doc_id", "title", "bm25_rank", "vector_rank", "rrf_score"],
        "efficiency_rules": {},
        "why_it_fails": "Frontier models frequently confuse RRF rank fusion with raw score addition (bm25_score + vector_sim). Because BM25 scores can reach 400+ while cosine similarity is bounded between 0 and 1, adding raw scores allows BM25 to completely drown out semantic vector relevance."
    },
    {
        "id": "task_116_graph_cycle_visited_protection",
        "name": "Directed Dependency Graph Cycle Protection via Visited Array Path",
        "category": "Graph & Hierarchy",
        "description": "Traverses downstream dependencies in a directed acyclic graph that contains an intentional cyclic loop (A -> B -> C -> A), requiring visited path arrays to prevent infinite recursion OOM.",
        "prompt": """Traverse all reachable downstream tasks starting from 'BUILD_CORE'.
CRITICAL: The graph contains a cyclic dependency ('COMPILE_LIB' -> 'TEST_SUITE' -> 'BUILD_CORE'). The query MUST detect already-visited nodes and terminate traversal to prevent infinite recursion.

Required output columns:
- task_id (VARCHAR)
- min_depth (INT)

Order by min_depth ASC, task_id ASC.""",
        "setup_sql": """
CREATE TABLE task_edges (parent_task VARCHAR, child_task VARCHAR);
INSERT INTO task_edges VALUES
  ('START', 'BUILD_CORE'),
  ('BUILD_CORE', 'COMPILE_LIB'),
  ('COMPILE_LIB', 'TEST_SUITE'),
  ('TEST_SUITE', 'BUILD_CORE'),   -- Circular loop!
  ('TEST_SUITE', 'PACKAGE_APP');
""",
        "golden_sql": """
WITH RECURSIVE downstream_graph AS (
    SELECT 
        child_task AS task_id,
        1 AS depth,
        ['BUILD_CORE', child_task] AS path_nodes
    FROM task_edges
    WHERE parent_task = 'BUILD_CORE'
    
    UNION ALL
    
    SELECT 
        e.child_task,
        g.depth + 1,
        list_append(g.path_nodes, e.child_task)
    FROM downstream_graph g
    JOIN task_edges e ON g.task_id = e.parent_task
    WHERE NOT list_contains(g.path_nodes, e.child_task)
      AND g.depth < 10
)
SELECT 
    task_id,
    MIN(depth) AS min_depth
FROM downstream_graph
GROUP BY task_id
ORDER BY min_depth ASC, task_id ASC;
""",
        "naive_llm_sql": """
WITH RECURSIVE downstream_graph AS (
    SELECT child_task AS task_id, 1 AS depth
    FROM task_edges
    WHERE parent_task = 'BUILD_CORE'
    UNION ALL
    SELECT e.child_task, g.depth + 1
    FROM downstream_graph g
    JOIN task_edges e ON g.task_id = e.parent_task
    WHERE g.depth < 3
)
SELECT task_id, MIN(depth) AS min_depth
FROM downstream_graph
GROUP BY task_id
ORDER BY min_depth ASC, task_id ASC;
""",
        "ordered": True,
        "expected_columns": ["task_id", "min_depth"],
        "efficiency_rules": {},
        "why_it_fails": "Standard recursive CTEs without cycle tracking (omitting visited array state) enter an infinite recursion loop on cyclic graphs, causing DuckDB or any relational database to fail with a max-recursion limit error or crash with an Out-of-Memory exception."
    },
    {
        "id": "task_117_bitemporal_retroactive_audit",
        "name": "Bitemporal Auditing: Retroactive Policy Revision Point-in-Time State",
        "category": "Temporal & Time-Series",
        "description": "Reconstructs historical corporate insurance coverage on an effective business date, as known to the system on an audit date prior to a retroactive backdated modification.",
        "prompt": """Determine customer 501's insurance deductible:
1. Effective as of business date: 2026-04-10
2. As known by the system on system audit date: 2026-04-15 (strictly BEFORE the retroactive update entered into the database on 2026-05-01).

Required output columns:
- customer_id (INT)
- active_deductible (DECIMAL)

Order by customer_id ASC.""",
        "setup_sql": """
CREATE TABLE insurance_policy_bitemporal (
    policy_id INT,
    customer_id INT,
    deductible DECIMAL(10,2),
    valid_from DATE,
    valid_to DATE,
    system_from TIMESTAMP,
    system_to TIMESTAMP
);
INSERT INTO insurance_policy_bitemporal VALUES
  -- Original policy entered on 2026-01-01 ($1000 deductible)
  (1, 501, 1000.00, '2026-01-01', '2026-12-31', '2026-01-01 00:00:00', '2026-05-01 12:00:00'),
  -- Retroactive change entered on 2026-05-01 backdating deductible to $500 effective from 2026-04-01
  (1, 501, 500.00,  '2026-04-01', '2026-12-31', '2026-05-01 12:00:00', '9999-12-31 23:59:59');
""",
        "golden_sql": """
SELECT 
    customer_id,
    deductible AS active_deductible
FROM insurance_policy_bitemporal
WHERE customer_id = 501
  -- Business valid time: 2026-04-10
  AND DATE '2026-04-10' >= valid_from 
  AND DATE '2026-04-10' < valid_to
  -- System knowledge time: 2026-04-15
  AND TIMESTAMP '2026-04-15 00:00:00' >= system_from 
  AND TIMESTAMP '2026-04-15 00:00:00' < system_to
ORDER BY customer_id ASC;
""",
        "naive_llm_sql": """
SELECT 
    customer_id,
    deductible AS active_deductible
FROM insurance_policy_bitemporal
WHERE customer_id = 501
  AND DATE '2026-04-10' >= valid_from 
  AND DATE '2026-04-10' < valid_to
ORDER BY customer_id ASC;
""",
        "ordered": True,
        "expected_columns": ["customer_id", "active_deductible"],
        "efficiency_rules": {},
        "why_it_fails": "Frontier models ignore the second time dimension (system transaction time) and only filter on valid_from / valid_to. This incorrectly matches the retroactive modification ($500), which was not entered into the database until May 1st, failing regulatory compliance auditing."
    },
    {
        "id": "task_118_reversal_interleaved_ledger",
        "name": "Financial Ledger Running Total with Transaction Reversal Nullification",
        "category": "Warehouse & Statistical",
        "description": "Calculates running account balance where REVERSAL records completely void specific prior transaction IDs, removing both the original transaction and the reversal record from net cumulative balance.",
        "prompt": """Calculate the active cumulative balance for each non-reversed transaction.
If a transaction was later reversed (by a record with action = 'REVERSAL' referencing its entry_id), BOTH the original entry AND the reversal record must be completely excluded from the running balance.

Required output columns:
- entry_id (INT)
- account_id (INT)
- amount (DECIMAL)
- net_running_balance (DECIMAL)

Order by entry_id ASC.""",
        "setup_sql": """
CREATE TABLE financial_ledger (
    entry_id INT,
    account_id INT,
    action VARCHAR, -- 'PAYMENT', 'REFUND', 'REVERSAL'
    reverses_entry_id INT,
    amount DECIMAL(10,2)
);
INSERT INTO financial_ledger VALUES
  (1, 100, 'PAYMENT',  NULL, 500.00),  -- Active
  (2, 100, 'PAYMENT',  NULL, 200.00),  -- Reversed by #4!
  (3, 100, 'PAYMENT',  NULL, 150.00),  -- Active
  (4, 100, 'REVERSAL', 2,    -200.00); -- Reversal entry
""",
        "golden_sql": """
WITH reversed_ids AS (
    SELECT reverses_entry_id AS void_id
    FROM financial_ledger
    WHERE action = 'REVERSAL' AND reverses_entry_id IS NOT NULL
    UNION
    SELECT entry_id AS void_id
    FROM financial_ledger
    WHERE action = 'REVERSAL'
),
active_entries AS (
    SELECT 
        l.entry_id,
        l.account_id,
        l.amount
    FROM financial_ledger l
    WHERE l.entry_id NOT IN (SELECT void_id FROM reversed_ids)
)
SELECT 
    entry_id,
    account_id,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id 
        ORDER BY entry_id 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS net_running_balance
FROM active_entries
ORDER BY entry_id ASC;
""",
        "naive_llm_sql": """
SELECT 
    entry_id,
    account_id,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id 
        ORDER BY entry_id 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS net_running_balance
FROM financial_ledger
ORDER BY entry_id ASC;
""",
        "ordered": True,
        "expected_columns": ["entry_id", "account_id", "amount", "net_running_balance"],
        "efficiency_rules": {},
        "why_it_fails": "Naive queries sum all records including reversed transactions. In our ledger, naive sum includes entry 2 (+$200) at step 2, temporarily inflating the running balance to $700 before entry 4 subtracts it. True ledger auditing requires excluding voided entries from the active sequence."
    },
    {
        "id": "task_119_multitouch_decay_attribution",
        "name": "Exponential Half-Life Multi-Touch Marketing Attribution Normalized to 100%",
        "category": "Temporal & Time-Series",
        "description": "Calculates exponential time-decay attribution across previous marketing touches (7-day half-life: w = 2^(-delta_t / 7)), strictly normalizing touchpoint weights so attributed revenue sums to exactly 100% of conversion value.",
        "prompt": """Attribute conversion revenue ($300.00) across touchpoints occurring within 30 days prior to purchase.
Use exponential time-decay weighting with a 7-day half-life:
raw_weight = POW(0.5, date_diff('second', click_time, conversion_time) / (7.0 * 86400.0))
CRITICAL: Attributed revenue MUST be normalized across touches so the sum of attributed revenue exactly equals the $300.00 conversion revenue.

Required output columns:
- touch_id (INT)
- channel (VARCHAR)
- attributed_revenue (DECIMAL)

Order by touch_id ASC.""",
        "setup_sql": """
CREATE TABLE touchpoints (
    touch_id INT,
    user_id INT,
    channel VARCHAR,
    click_time TIMESTAMP
);
CREATE TABLE purchase_conversions (
    order_id INT,
    user_id INT,
    order_revenue DECIMAL(10,2),
    conversion_time TIMESTAMP
);
INSERT INTO touchpoints VALUES
  (1, 42, 'Google Search', '2026-03-01 12:00:00'), -- 14 days before (weight = 0.25)
  (2, 42, 'Facebook Ad',   '2026-03-08 12:00:00'), -- 7 days before  (weight = 0.50)
  (3, 42, 'Email Promo',   '2026-03-15 12:00:00'); -- 0 days before  (weight = 1.00)

INSERT INTO purchase_conversions VALUES
  (101, 42, 350.00, '2026-03-15 12:00:00');
""",
        "golden_sql": """
WITH weighted_touches AS (
    SELECT 
        t.touch_id,
        t.channel,
        c.order_revenue,
        POW(0.5, date_diff('second', t.click_time, c.conversion_time) / (7.0 * 86400.0)) AS raw_weight
    FROM purchase_conversions c
    JOIN touchpoints t 
      ON c.user_id = t.user_id 
     AND t.click_time <= c.conversion_time
     AND t.click_time >= c.conversion_time - INTERVAL 30 DAYS
),
total_weight AS (
    SELECT 
        *,
        SUM(raw_weight) OVER () AS sum_weights
    FROM weighted_touches
)
SELECT 
    touch_id,
    channel,
    ROUND(order_revenue * (raw_weight / sum_weights), 2) AS attributed_revenue
FROM total_weight
ORDER BY touch_id ASC;
""",
        "naive_llm_sql": """
SELECT 
    t.touch_id,
    t.channel,
    ROUND(c.order_revenue * POW(0.5, date_diff('second', t.click_time, c.conversion_time) / (7.0 * 86400.0)), 2) AS attributed_revenue
FROM purchase_conversions c
JOIN touchpoints t ON c.user_id = t.user_id
ORDER BY t.touch_id ASC;
""",
        "ordered": True,
        "expected_columns": ["touch_id", "channel", "attributed_revenue"],
        "efficiency_rules": {},
        "why_it_fails": "Naive queries multiply raw exponential decay directly by order revenue without dividing by the sum of weights. In our scenario (raw weights sum to 1.75), naive attribution distributes 175% ($612.50) of the actual $350.00 revenue, severely corrupting marketing ROI calculations."
    },
    {
        "id": "task_120_market_basket_lift_smoothing",
        "name": "Association Rule Lift Matrix with Directional Pair Evaluation",
        "category": "Warehouse & Statistical",
        "description": "Calculates market basket association rule Lift for directional product pairs (A -> B), correctly eliminating self-pairs and evaluating directional confidence.",
        "prompt": """Compute Support, Confidence, and Lift for directional association rules (Item A -> Item B):
- Support(A -> B) = Count(Transactions containing both A and B) / Total Transactions
- Confidence(A -> B) = Count(Transactions containing both A and B) / Count(Transactions containing A)
- Lift(A -> B) = Confidence(A -> B) / (Count(Transactions containing B) / Total Transactions)
Ensure self-pairs (A -> A) are excluded.

Required output columns:
- item_a (VARCHAR)
- item_b (VARCHAR)
- support (DOUBLE)
- confidence (DOUBLE)
- lift (DOUBLE)

Order by lift DESC, item_a ASC, item_b ASC.""",
        "setup_sql": """
CREATE TABLE market_baskets (basket_id INT, item_name VARCHAR);
INSERT INTO market_baskets VALUES
  (1, 'Bread'), (1, 'Butter'), (1, 'Milk'),
  (2, 'Bread'), (2, 'Butter'),
  (3, 'Bread'), (3, 'Milk'),
  (4, 'Beer'),  (4, 'Diapers');
""",
        "golden_sql": """
WITH total_orders AS (
    SELECT COUNT(DISTINCT basket_id) AS total_baskets FROM market_baskets
),
item_frequencies AS (
    SELECT item_name, COUNT(DISTINCT basket_id) AS item_baskets
    FROM market_baskets
    GROUP BY item_name
),
pair_occurrences AS (
    SELECT 
        a.item_name AS item_a,
        b.item_name AS item_b,
        COUNT(DISTINCT a.basket_id) AS pair_baskets
    FROM market_baskets a
    JOIN market_baskets b 
      ON a.basket_id = b.basket_id 
     AND a.item_name != b.item_name
    GROUP BY a.item_name, b.item_name
)
SELECT 
    p.item_a,
    p.item_b,
    ROUND(p.pair_baskets * 1.0 / t.total_baskets, 4) AS support,
    ROUND(p.pair_baskets * 1.0 / fa.item_baskets, 4) AS confidence,
    ROUND((p.pair_baskets * 1.0 * t.total_baskets) / (fa.item_baskets * fb.item_baskets), 4) AS lift
FROM pair_occurrences p
JOIN item_frequencies fa ON p.item_a = fa.item_name
JOIN item_frequencies fb ON p.item_b = fb.item_name
CROSS JOIN total_orders t
WHERE p.pair_baskets >= 2
ORDER BY lift DESC, p.item_a ASC, p.item_b ASC;
""",
        "naive_llm_sql": """
SELECT 
    a.item_name AS item_a,
    b.item_name AS item_b,
    COUNT(*) * 1.0 / 4 AS support,
    COUNT(*) * 1.0 / 4 AS confidence,
    COUNT(*) * 1.0 AS lift
FROM market_baskets a
JOIN market_baskets b ON a.basket_id = b.basket_id
GROUP BY a.item_name, b.item_name
ORDER BY lift DESC, item_a ASC, item_b ASC;
""",
        "ordered": True,
        "expected_columns": ["item_a", "item_b", "support", "confidence", "lift"],
        "efficiency_rules": {},
        "why_it_fails": "Naive models omit self-pair elimination (producing trivial rules like Bread -> Bread with 100% confidence), fail to normalize by total baskets, or confuse raw co-occurrence counts with statistical Lift."
    }
]

print(f"Loaded {len(HARDENED_TASKS)} hardened tasks.")

tasks_dir = "tasks"
os.makedirs(tasks_dir, exist_ok=True)

for task in HARDENED_TASKS:
    task_path = os.path.join(tasks_dir, f"{task['id']}.json")
    with open(task_path, "w") as f:
        json.dump(task, f, indent=2)
    print(f"Wrote {task['id']}.json")

print("All hardened tasks successfully written to tasks/")
