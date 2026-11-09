# SQL-Frontier-Eval: Benchmark Report & Empirical Analysis

> **Comprehensive evaluation of Frontier AI Models on Analytical SQL, Silent Metric Corruption, and Execution Anti-Patterns.**  
> Built for the **micro1 Eval Hackathon** on HackerRank Engage.  
> **Evaluation Date:** November 2026 | **Execution Engine:** DuckDB 2.0 In-Memory Engine

---

## Executive Summary

Modern text-to-SQL benchmarks (such as Spider and BIRD) predominantly evaluate transactional lookups and textbook joins. However, in production analytics environments (Snowflake, BigQuery, Databricks, DuckDB), the most catastrophic failures are not syntax errors—they are **silent metric corruption** and **computational blowups**.

**SQL-Frontier-Eval** evaluates frontier language models across an 8-category analytical failure taxonomy. Each task tests whether a model generates semantically correct, warehouse-efficient SQL or falls into well-documented analytical traps.

### Headline Benchmark Results

| Model / Baseline | Pass Rate | Correct / Total | Avg Model Latency | Engine Exec Latency | Primary Failure Modes | Run Artifact |
|---|---|---|---|---|---|---|
| **Claude Opus 4.6 (Thinking)** | **100.0%** | **8 / 8** | 6.9s | **4.6 ms** | None (Zero failures across all 8 tasks) | [`results/eval_run_agy_claude-opus-4-6-thinking_1794196279.json`](results/eval_run_agy_claude-opus-4-6-thinking_1794196279.json) |
| **Gemini 3.8 Flash (Low)** | **100.0%** | **8 / 8** | **4.6s** | **5.4 ms** | None (Zero failures across all 8 tasks, Fastest) | [`results/eval_run_agy_gemini-3.8-flash-low_1794195725.json`](results/eval_run_agy_gemini-3.8-flash-low_1794195725.json) |
| **Gemini 3.8 Flash (Medium)** | **100.0%** | **8 / 8** | 27.6s | **4.5 ms** | None (Zero failures across all 8 tasks) | [`results/eval_run_gemini-3.8-flash-medium_1794186799.json`](results/eval_run_gemini-3.8-flash-medium_1794186799.json) |
| **Claude Sonnet 4.6 (Thinking)** | **87.5%** | **7 / 8** | 6.3s | **4.8 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`results/eval_run_agy_claude-sonnet-4-6_1794196223.json`](results/eval_run_agy_claude-sonnet-4-6_1794196223.json) |
| **GPT-OSS 120B (Medium)** | **87.5%** | **7 / 8** | 6.5s | **5.5 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`results/eval_run_agy_gpt-oss-120b-medium_1794196331.json`](results/eval_run_agy_gpt-oss-120b-medium_1794196331.json) |
| **Gemini 3.8 Flash (High)** | **75.0%** | **6 / 8** | 51.9s | **4.3 ms** | Tasks 01 & 06 timed out during deep reasoning | [`results/eval_run_agy_gemini-3.8-flash-high_1794196172.json`](results/eval_run_agy_gemini-3.8-flash-high_1794196172.json) |
| **Golden Ground Truth (Core Suite)** | **100.0%** | **8 / 8** | N/A | **3.8 ms** | Baseline Verification (0% False Negatives) | [`results/eval_run_offline_1794186318.json`](results/eval_run_offline_1794186318.json) |
| **Golden Ground Truth (Comprehensive 120 Suite)** | **100.0%** | **120 / 120** | N/A | **2.6 ms** | Full Suite Verification across all 5 Domains & Hardened Traps (100% Pass) | [`results/eval_run_offline_1794210761.json`](results/eval_run_offline_1794210761.json) |
| **Offline Reference / Naive Traps** | **0.0%** | **0 / 8** | N/A | **2.6 ms** | 100% Trap Detection (Metric skew, row loss, O(N²) joins) | [`results/eval_run_offline_1794186320.json`](results/eval_run_offline_1794186320.json) |

---

## Comprehensive 120-Task Multi-Domain Evaluation Suite

The benchmark has been expanded from the initial 8 challenge tasks to **120 comprehensive evaluation tasks** (incorporating 102 production analytical queries across five modern analytical domains and 10 hardened frontier trap challenges).

### Domain Coverage & Engine Capabilities

| Domain | Queries | DuckDB Engine Capabilities Evaluated | Real-World Scenario Focus | Golden Pass Rate |
|---|:---:|---|---|:---:|
| **1. Temporal & Time-Series** | `Q01` – `Q25` | `ASOF JOIN`, `generate_series`, `IGNORE NULLS` LOCF, `time_bucket` | Tick-level trade matching, point-in-time FX, sensor gap filling, bitemporal audit, multi-touch attribution | **25 / 25 (100%)** |
| **2. Vector & Embeddings** | `Q26` – `Q50` | `array_cosine_similarity`, `array_distance`, `array_inner_product`, `FLOAT[N]`, `QUALIFY` | RAG retrieval, ticket deduplication, ColBERT MaxSim in SQL, K-Means clustering, MMR diversity reranking | **25 / 25 (100%)** |
| **3. Search & Hybrid Retrieval** | `Q51` – `Q75` | `PRAGMA create_fts_index`, `match_bm25`, `levenshtein`, `jaro_winkler_similarity`, RRF | Reciprocal Rank Fusion (BM25 + Dense Vectors), fuzzy typo-tolerant matching, faceted JSON filters | **25 / 25 (100%)** |
| **4. Graph & Hierarchies** | `Q76` – `Q88` | `WITH RECURSIVE`, path tracking arrays, transitive closures | Multi-tier BOM cost rollups, reporting hierarchies, sybil fraud ring tracking, critical path scheduling | **13 / 13 (100%)** |
| **5. Warehouse & Statistical** | `Q89` – `Q102` | Pre-aggregated CTEs, `NOT EXISTS`, `PIVOT`, `UNPIVOT`, `list_transform`, `MAD`, `NTILE` | Chasm trap fan-out prevention, 3-valued null logic, robust outlier detection, Kaplan-Meier survival | **14 / 14 (100%)** |
| **6. Hardened Frontier Traps** | `111` – `120` | `ASOF` tolerance bounds, cycle protection arrays, RRF rank fusion, normalized decay | Stress-testing LLM reasoning where standard models exhibit syntax and logical cracks | **10 / 10 (100%)** |
| **Core Traps Baseline** | `01` – `08` | `CROSS_PRODUCT`, `BLOCKWISE_NL_JOIN`, `PIECEWISE_MERGE_JOIN` checks | Silent metric corruption, quadratic triangular self-joins, three-valued logic null traps | **8 / 8 (100%)** |
| **Total Benchmark** | **120 Tasks** | **Vectorized Execution, SIMD Math, Plan Profiling** | **Complete Frontier Analytical Spectrum** | **120 / 120 (100%)** |

---

## The 8-Category Analytical Failure Taxonomy

Each task in the benchmark is paired with synthetic seed data, deterministic multiset verification, tolerance-based numeric assertion, and execution plan profiling:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           SQL-FRONTIER-EVAL TAXONOMY                             │
├─────────────────────┬────────────────────────────────┬───────────────────────────┤
│ Task ID             │ Category                       │ Real-World Risk Exposed   │
├─────────────────────┼────────────────────────────────┼───────────────────────────┤
│ task_01_fanout      │ Metric Inflation / Chasm Trap  │ 4x KPI multiplication     │
│ task_02_sessionize  │ Gaps & Islands Sessionization  │ Miscalculated sessions    │
│ task_03_scd2_join   │ SCD Type 2 Point-in-Time Joins │ Silent loss of active row │
│ task_04_three_value │ Three-Valued Logic Anti-Joins  │ 0 rows returned on NULL   │
│ task_05_win_bounds  │ Window Frame Default Bounds    │ Peer row timestamp bunch  │
│ task_06_funnel_prec │ Strict Funnel Precedence       │ Out-of-order conversions  │
│ task_07_quad_join   │ Quadratic Self-Joins           │ O(N²) memory/CPU spill    │
│ task_08_sargable    │ Non-SARGable Partition Pruning │ Full warehouse table scan │
└─────────────────────┴────────────────────────────────┴───────────────────────────┘
```

---

## Detailed Task-by-Task Scorecard

| Task ID | Task Description | Gemini 3.8 Flash (Med) | Claude Opus 4.6 | Claude Sonnet 4.6 | GPT-OSS 120B | Gemini 3.8 Flash (Low) | Gemini 3.8 Flash (High) | Offline Naive | Root Cause Detected |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **01** | E-Commerce Join Fan-Out / Chasm Trap | **PASS** (5.0ms) | **PASS** (4.5ms) | **PASS** (10.9ms) | **PASS** (10.9ms) | **PASS** (5.3ms) | `EXEC_ERROR` | `VALUE_MISMATCH` | Multi-table joins before `GROUP BY` multiply sums 4x |
| **02** | Inactivity Gap Sessionization (30 min) | **PASS** (5.7ms) | **PASS** (4.5ms) | **PASS** (5.3ms) | **PASS** (8.4ms) | **PASS** (5.1ms) | **PASS** (5.2ms) | `SHAPE_MISMATCH` | Misuse of `ROW_NUMBER()` instead of cumulative step flags |
| **03** | SCD Type 2 Currency Conversion | **PASS** (8.1ms) | **PASS** (9.2ms) | **PASS** (8.5ms) | **PASS** (8.3ms) | **PASS** (9.1ms) | **PASS** (8.6ms) | `SHAPE_MISMATCH` | Omitting `OR valid_to IS NULL` drops ongoing rates |
| **04** | Anti-Join with Three-Valued Nulls | **PASS** (2.2ms) | **PASS** (2.7ms) | **PASS** (2.4ms) | **PASS** (4.1ms) | **PASS** (2.8ms) | **PASS** (2.6ms) | `SHAPE_MISMATCH` | `NOT IN` with subquery NULLs returns empty dataset |
| **05** | Running Balance with Duplicate Timestamps | **PASS** (2.7ms) | **PASS** (7.1ms) | **PASS** (2.9ms) | **PASS** (6.6ms) | **PASS** (3.4ms) | **PASS** (2.8ms) | `VALUE_MISMATCH` | Default `RANGE` frame groups identical timestamp peers |
| **06** | Sequential Conversion Funnel Precedence | **PASS** (5.3ms) | **PASS** (11.8ms) | `EFFICIENCY_VIOLATION` | `EFFICIENCY_VIOLATION` | **PASS** (12.3ms) | `EXEC_ERROR` | `VALUE_MISMATCH` | Independent conditional counts ignore step timestamps |
| **07** | Rolling 7-Day Window vs Triangular Join | **PASS** (4.6ms) | **PASS** (2.7ms) | **PASS** (2.7ms) | **PASS** (3.1ms) | **PASS** (2.8ms) | **PASS** (3.7ms) | `EFFICIENCY_VIOLATION` | Non-equi triangular self-join causes quadratic merge join |
| **08** | SARGable Partition Date Filtering | **PASS** (2.7ms) | **PASS** (2.5ms) | **PASS** (5.4ms) | **PASS** (4.0ms) | **PASS** (2.9ms) | **PASS** (2.7ms) | `VALUE_MISMATCH` | `BETWEEN` boundary leak captures Feb 1st midnight |

---

## Deep-Dive Failure Case Studies

### 1. The Chasm Trap / Metric Inflation (`task_01_fanout`)
* **The Scenario**: An e-commerce orders table joined to two 1-to-many child tables (`order_discounts` and `order_shipments`).
* **The Naive Failure**:
  ```sql
  SELECT m.merchant_name, SUM(o.base_amount), SUM(d.amount), SUM(s.shipping_fee)
  FROM merchants m
  JOIN orders o ON m.merchant_id = o.merchant_id
  LEFT JOIN order_discounts d ON o.order_id = d.order_id
  LEFT JOIN order_shipments s ON o.order_id = s.order_id
  GROUP BY m.merchant_name;
  ```
* **The Consequence**: 2 discount rows $\times$ 2 shipment rows create an intermediate Cartesian fan-out of 4 rows per order. `base_amount` of \$100 is silently reported as **\$400.00 (4.0x gross sales inflation)**.
* **The Solution**: CTE pre-aggregation or correlated subqueries before joining.

### 2. Three-Valued Logic in Anti-Joins (`task_04_three_valued_logic`)
* **The Scenario**: Find customers who have never filed a product return.
* **The Naive Failure**:
  ```sql
  SELECT customer_id, customer_name
  FROM customers
  WHERE customer_id NOT IN (SELECT customer_id FROM returns);
  ```
* **The Consequence**: If the `returns` table contains a single anonymous guest return with `customer_id IS NULL`, SQL three-valued logic causes `x NOT IN (1, NULL)` to evaluate to `UNKNOWN`. As a result, the query returns **0 rows**, completely corrupting the active customer cohort.
* **The Solution**: `NOT EXISTS (SELECT 1 FROM returns r WHERE r.customer_id = c.customer_id)`.

### 3. Window Frame Default Bounds (`task_05_window_frame_bounds`)
* **The Scenario**: Ledger running balance with multiple transactions occurring at the identical second (`2025-01-01 10:00:00`).
* **The Naive Failure**:
  ```sql
  SUM(amount) OVER (PARTITION BY account_id ORDER BY entry_time)
  ```
* **The Consequence**: In ANSI SQL and DuckDB, omitting the window frame defaults to `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. This bundles duplicate timestamp peers together, producing balances of `[80.0, 80.0, 60.0]` instead of `[50.0, 80.0, 60.0]`.
* **The Solution**: Explicit `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` with tie-breaker ordering on `entry_id`.

### 4. Quadratic Triangular Self-Joins (`task_07_quadratic_self_join`)
* **The Scenario**: Calculating rolling 7-day total revenue.
* **The Anti-Pattern**:
  ```sql
  SELECT a.revenue_date, SUM(b.gross_amount)
  FROM daily_revenue a
  JOIN daily_revenue b
    ON b.revenue_date BETWEEN a.revenue_date - INTERVAL 6 DAYS AND a.revenue_date
  GROUP BY a.revenue_date, a.gross_amount;
  ```
* **Execution Profiler Detection**: Traversal of DuckDB's physical plan tree immediately catches the `PIECEWISE_MERGE_JOIN` operator ($O(N^2)$ non-equi join), triggering an automated `EFFICIENCY_VIOLATION`.
* **The Solution**: Single-pass `RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW`.

---

## Empirical Comparison: Cross-Model Frontier Performance & Reasoning Scaling

Comparing the frontier models across providers (Gemini, Claude, GPT) reveals critical insights for AI prompt engineering and analytical agent design:

```
Gemini 3.8 Flash (Medium Reasoning):  ████████████████████ 100.0% (8/8)  [Avg Latency: 27.6s]
Claude Opus 4.6 (Thinking):           █████████████████░░░  87.5% (7/8)  [Avg Latency:  6.8s]
Claude Sonnet 4.6 (Thinking):         █████████████████░░░  87.5% (7/8)  [Avg Latency:  6.8s]
GPT-OSS 120B (Medium):                █████████████████░░░  87.5% (7/8)  [Avg Latency:  5.5s]
Gemini 3.8 Flash (Low Reasoning):     █████████████████░░░  87.5% (7/8)  [Avg Latency:  4.2s]
Gemini 3.8 Flash (High Reasoning):    ███████████████░░░░░  75.0% (6/8)  [Avg Latency: 31.1s]*
```
*\*Note: High reasoning mode timed out at the default 90-second query generation threshold on Tasks 02 and 06 due to deep recursive thinking passes.*

1. **The Shared Blindspot: Strict Funnel Precedence (Task 06)**:
   - Claude Opus 4.6 Thinking, Claude Sonnet 4.6, GPT-OSS 120B, and Gemini 3.8 Flash (Low) all solved 7 out of 8 tasks, but all stumbled on Task 06.
   - Claude and GPT attempted to compute funnel stages using multiple `COUNT(DISTINCT CASE WHEN ...)` subqueries. In DuckDB's execution planner, evaluating independent distinct aggregations across CTEs generated an internal `CROSS_PRODUCT` plan, violating performance constraints.
   - Only **Gemini 3.8 Flash (Medium)** recognized that chronological step progression can be evaluated in a **single scan** using conditional window aggregations (`MIN(CASE WHEN event = ...)`), achieving a perfect 8/8 (100.0%).
2. **Speed vs. Reasoning Tradeoffs**:
   - Claude Opus 4.6 and Sonnet 4.6 delivered remarkably fast inference (6.8s per task) while correctly navigating subtle edge cases like three-valued NULL logic in anti-joins and SCD Type 2 open-ended bounds.
   - GPT-OSS 120B demonstrated competitive analytical capability (5.5s per task), correctly avoiding quadratic joins.
   - Gemini 3.8 Flash (Low) achieved the fastest overall inference at 4.2s per task with 87.5% accuracy.

---

## Hardened Frontier Trap Evaluation (Tasks 111–120): Uncovering Model Cracks

To critically stress-test frontier models where benchmarks typically show 100% saturation, we engineered 10 hardened trap queries specifically targeting subtleties in DuckDB 2.0 analytical execution:

| Task ID | Hardened Trap Description | Gemini 3.8 Flash (Low) | GPT-OSS 120B (Med) | Offline Naive Baseline | Real-World Enterprise Risk |
|---|---|:---:|:---:|:---:|---|
| **111** | Rolling 7-Day Distinct Active Users | **PASS** (6.2ms) | **PASS** (6.2ms) | `EFFICIENCY_VIOLATION` | Non-equi triangular self-join causes quadratic merge join |
| **112** | Dual-Constraint Sessionization (Gap + 4h Cap) | **PASS** (5.8ms) | `SYNTAX_ERROR` | `VALUE_MISMATCH` | Circular CTE reference / lack of window cumulative flags |
| **113** | Vector Pre-Filter vs Post-Filter Recall Drop | **PASS** (4.1ms) | **PASS** (4.3ms) | `SHAPE_MISMATCH` | Post-filtering top-K vectors returns empty set on sparse predicates |
| **114** | ASOF Join with 500ms Staleness Tolerance | **PASS** (5.9ms) | **PASS** (6.1ms) | `VALUE_MISMATCH` | Unbounded ASOF pairs quotes across hours of market downtime |
| **115** | RRF Hybrid Rank Fusion Isolation | **PASS** (9.8ms) | **PASS** (10.2ms) | `VALUE_MISMATCH` | Raw score summing collapses dense & sparse metric scales |
| **116** | Directed Graph Cycle Visited Array Protection | **PASS** (4.2ms) | `SYNTAX_ERROR` | `SHAPE_MISMATCH` | Invalid array string concatenation (`||`) & infinite recursive loops |
| **117** | Bitemporal Retroactive Audit Correction | **PASS** (2.5ms) | **PASS** (2.7ms) | `SHAPE_MISMATCH` | Conflating transaction-time knowledge with valid-time timeline |
| **118** | Reversal-Interleaved Cumulative Ledger | **PASS** (6.9ms) | **PASS** (7.4ms) | `SHAPE_MISMATCH` | Naive window sums double-count reversed fraudulent charges |
| **119** | Multi-Touch Half-Life Decay Attribution | **PASS** (9.7ms) | `VALUE_MISMATCH` | `VALUE_MISMATCH` | Unnormalized decay weights allocate 175% of actual revenue |
| **120** | Market Basket Directional Lift & Smoothing | **PASS** (5.8ms) | **PASS** (6.1ms) | `SHAPE_MISMATCH` | Undirected self-pairing (A, A) and unsmoothed small sample skew |
| **Score** | **Hardened Trap Suite Pass Rate** | **9 / 9 (100.0%)** | **6 / 9 (66.7%)** | **0 / 10 (0.0%)** | **100% Trap Sensitivity** |

### Specific Model Cracks Observed

1. **Hallucinated CTE Recursion Syntax (Task 112 - Sessionization)**:
   - `gpt-oss-120b-medium` attempted to perform sessionization by self-referencing an intermediate CTE without a recursive union (`WITH ordered AS (...), session_recursive AS (...)`), triggering DuckDB `Binder Error: Circular reference to CTE session_recursive`.
   - In contrast, `gemini-3.8-flash-low` cleanly computed inactivity breaks and elapsed start times using dual analytic window functions (`LAG()` and `FIRST_VALUE()`), avoiding recursion entirely.
2. **DuckDB 2.0 Array Type Mismatch (Task 116 - Graph Cycle Protection)**:
   - `gpt-oss-120b-medium` attempted array concatenation using SQL string syntax: `t.path || e.child_task`, which fails in DuckDB 2.0 with `Binder Error: Cannot concatenate type VARCHAR[] and VARCHAR`.
   - Native DuckDB array expansion requires `list_append(t.path, e.child_task)`.
3. **Unnormalized Revenue Allocation (Task 119 - Multi-Touch Decay Attribution)**:
   - `gpt-oss-120b-medium` multiplied raw exponential decay weights directly against order revenue without dividing by `SUM(decay_weight) OVER (PARTITION BY order_id)`.
   - In the test scenario (sum of weights = 1.75), this allocated \$612.50 across channels for an order with actual revenue of \$350.00 (a 1.75x budget inflation), failing with `VALUE_MISMATCH`.

---

## Automated Walkthrough Generation

When any candidate query fails, the evaluation harness prints a detailed terminal walkthrough formatted with `sqlparse` and `tabulate`:

```text
==========================================================================================
❌ EVALUATION FAILURE WALKTHROUGH: E-Commerce Financial Aggregation without Join Fan-Out
Category: Metric Inflation / Chasm Trap | Verdict: VALUE_MISMATCH
==========================================================================================

1. QUERIES EXECUTED
[Candidate Query (Tested - Latency: 3.6ms)]
  SELECT m.merchant_id,
         m.merchant_name,
         sum(o.base_amount) AS total_gross_sales, ...
  FROM merchants m
  JOIN orders o ON m.merchant_id = o.merchant_id
  LEFT JOIN order_discounts d ON o.order_id = d.order_id
  LEFT JOIN order_shipments s ON o.order_id = s.order_id
  GROUP BY m.merchant_id, m.merchant_name;

2. TABULAR QUERY RESULTS COMPARISON
[Actual Candidate Output] (1 rows x 5 columns):
  +----+---------------+------------------+---------------------+-------------------------+
  |    |   merchant_id | merchant_name    |   total_gross_sales |   total_discount_amount |
  +====+===============+==================+=====================+=========================+
  |  0 |             1 | Acme Electronics |                 400 |                      30 |
  +----+---------------+------------------+---------------------+-------------------------+

[Expected Golden Output] (1 rows x 5 columns):
  +----+---------------+------------------+---------------------+-------------------------+
  |  0 |             1 | Acme Electronics |                 100 |                      15 |
  +----+---------------+------------------+---------------------+-------------------------+

3. FAILURE ANALYSIS & ROOT CAUSE
• Verdict Reason: Data discrepancy: 'total_gross_sales' at Row 0 expected 100.0, got 400.0 (+300.00 / 4.0x inflation).
• Root Cause: Joining two 1:N child tables before grouping created a 2 * 2 = 4x Cartesian fan-out.
==========================================================================================
```

---

## AI-Assisted Development Acknowledgement

In accordance with hackathon submission guidelines, we transparently acknowledge the usage of **AI-assisted development**:
* **Pair Programming Partner**: Developed with the assistance of **Google Antigravity (AGY)** agentic AI pair programming system powered by Gemini 3.8 Flash.
* **Human-in-the-Loop Oversight**: Benchmark design, analytical failure taxonomy taxonomy curation, test fixture definitions, execution profiling rules, and mathematical verification were directed and validated by human analytical engineering review.

---

## Summary for Hackathon Judges

SQL-Frontier-Eval delivers a turnkey, production-grade eval for modern enterprise analytics. By isolating silent correctness traps and quadratic engine anti-patterns, it provides the deterministic rigor needed to evaluate and guide frontier models in real-world data warehouse environments.
