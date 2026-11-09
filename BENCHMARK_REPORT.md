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
| **Gemini 3.8 Flash (Medium)** | **100.0%** | **8 / 8** | 27.6s | **4.5 ms** | None (Zero failures across all 8 tasks) | [`results/eval_run_gemini-3.8-flash-medium_1794186799.json`](results/eval_run_gemini-3.8-flash-medium_1794186799.json) |
| **Claude Opus 4.6 (Thinking)** | **87.5%** | **7 / 8** | 6.8s | **5.3 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`results/eval_run_claude-opus-4-6-thinking_1794187547.json`](results/eval_run_claude-opus-4-6-thinking_1794187547.json) |
| **Claude Sonnet 4.6 (Thinking)** | **87.5%** | **7 / 8** | 6.8s | **4.8 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`results/eval_run_claude-sonnet-4-6_1794187183.json`](results/eval_run_claude-sonnet-4-6_1794187183.json) |
| **GPT-OSS 120B (Medium)** | **87.5%** | **7 / 8** | 5.5s | **5.5 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`results/eval_run_gpt-oss-120b-medium_1794187234.json`](results/eval_run_gpt-oss-120b-medium_1794187234.json) |
| **Gemini 3.8 Flash (Low)** | **87.5%** | **7 / 8** | **4.2s** | **5.4 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`results/eval_run_gemini-3.8-flash-low_1794186841.json`](results/eval_run_gemini-3.8-flash-low_1794186841.json) |
| **Gemini 3.8 Flash (High)** | **75.0%** | **6 / 8** | 31.1s | **4.3 ms** | Tasks 02 & 06 timed out at 90s reasoning limit | [`results/eval_run_gemini-3.8-flash-high_1794187896.json`](results/eval_run_gemini-3.8-flash-high_1794187896.json) |
| **Golden Ground Truth** | **100.0%** | **8 / 8** | N/A | **3.8 ms** | Baseline Verification (0% False Negatives) | [`results/eval_run_offline_1794186318.json`](results/eval_run_offline_1794186318.json) |
| **Offline Reference / Naive** | **0.0%** | **0 / 8** | N/A | **2.6 ms** | 100% Trap Detection (Metric skew, row loss, O(N²) joins) | [`results/eval_run_offline_1794186320.json`](results/eval_run_offline_1794186320.json) |

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
| **01** | E-Commerce Join Fan-Out / Chasm Trap | **PASS** (5.0ms) | **PASS** (4.5ms) | **PASS** (10.9ms) | **PASS** (10.9ms) | **PASS** (5.3ms) | **PASS** (5.5ms) | `VALUE_MISMATCH` | Multi-table joins before `GROUP BY` multiply sums 4x |
| **02** | Inactivity Gap Sessionization (30 min) | **PASS** (5.7ms) | **PASS** (4.5ms) | **PASS** (5.3ms) | **PASS** (8.4ms) | **PASS** (4.6ms) | `TIMEOUT` (>90s) | `SHAPE_MISMATCH` | Misuse of `ROW_NUMBER()` instead of cumulative step flags |
| **03** | SCD Type 2 Currency Conversion | **PASS** (8.1ms) | **PASS** (9.2ms) | **PASS** (8.5ms) | **PASS** (8.3ms) | **PASS** (14.4ms) | **PASS** (8.6ms) | `SHAPE_MISMATCH` | Omitting `OR valid_to IS NULL` drops ongoing rates |
| **04** | Anti-Join with Three-Valued Nulls | **PASS** (2.2ms) | **PASS** (2.7ms) | **PASS** (2.4ms) | **PASS** (4.1ms) | **PASS** (2.6ms) | **PASS** (2.6ms) | `SHAPE_MISMATCH` | `NOT IN` with subquery NULLs returns empty dataset |
| **05** | Running Balance with Duplicate Timestamps | **PASS** (2.7ms) | **PASS** (7.1ms) | **PASS** (2.9ms) | **PASS** (6.6ms) | **PASS** (3.1ms) | **PASS** (2.8ms) | `VALUE_MISMATCH` | Default `RANGE` frame groups identical timestamp peers |
| **06** | Sequential Conversion Funnel Precedence | **PASS** (5.3ms) | `EFFICIENCY_VIOLATION` | `EFFICIENCY_VIOLATION` | `EFFICIENCY_VIOLATION` | `EFFICIENCY_VIOLATION` | `TIMEOUT` (>90s) | `VALUE_MISMATCH` | Independent conditional counts ignore step timestamps |
| **07** | Rolling 7-Day Window vs Triangular Join | **PASS** (4.6ms) | **PASS** (2.7ms) | **PASS** (2.7ms) | **PASS** (3.1ms) | **PASS** (4.6ms) | **PASS** (3.7ms) | `EFFICIENCY_VIOLATION` | Non-equi triangular self-join causes quadratic merge join |
| **08** | SARGable Partition Date Filtering | **PASS** (2.7ms) | **PASS** (2.5ms) | **PASS** (5.4ms) | **PASS** (4.0ms) | **PASS** (3.5ms) | **PASS** (2.7ms) | `VALUE_MISMATCH` | `BETWEEN` boundary leak captures Feb 1st midnight |

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
