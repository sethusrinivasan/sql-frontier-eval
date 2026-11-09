# SQL-Frontier-Eval: Benchmarking Frontier AI on Complex Analytical SQL

> **Evaluating semantic correctness, mathematical KPI integrity, and plan efficiency on modern analytical engines.**  
> Built for the [micro1 Eval Hackathon](https://www.hackerrank.com/event/micro1-eval-hackathon) on HackerRank Engage.

[![Verification Suite](https://img.shields.io/badge/verification-12%20passed-3fb950.svg)](verify.sh)
[![Gemini 3.8 Flash](https://img.shields.io/badge/Gemini%203.8%20Flash%20(Medium)-100%25%20(8%2F8)-success.svg)](results/eval_run_gemini-3.8-flash-medium_1794186799.json)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 Motivation: Why Analytical SQL Evals Matter

Existing text-to-SQL benchmarks (e.g. Spider, BIRD) primarily test simple relational lookups and basic textbook joins. However, in enterprise analytics (Snowflake, BigQuery, Databricks, DuckDB), data engineers face subtle and catastrophic failure modes from frontier LLMs:

1. **Silent Metric Corruption (The Chasm Trap)**: When calculating aggregates across multiple 1-to-many child tables (e.g. Orders joined to both Discounts and Shipments), LLMs generate multi-table joins before `GROUP BY`. This cross-multiplies records and silently inflates financial KPIs (e.g. **4x gross sales**) without triggering any SQL syntax errors.
2. **Computational Anti-Patterns**: Frontier models frequently substitute window functions with quadratic triangular self-joins (`ON a.ts >= b.ts - 30`), triggering Cartesian row explosions that cause memory spills and crash analytical warehouse clusters.
3. **Subtle Logical Pitfalls**: Models routinely fail three-valued SQL logic (`NOT IN` on subqueries with `NULL`s), miss boundary conditions on temporal SCD Type 2 joins, or misconfigure window frame default bounds.

**SQL-Frontier-Eval** provides a reproducible, deterministic evaluation suite to expose where frontier models break down and guide the generation of optimal analytical queries.

---

## 🏆 Headline Benchmark Results

Evaluated across the 8-category failure taxonomy using DuckDB 2.0:

| Model / Evaluated Target | Pass Rate | Tasks Passed | Avg Generation Latency | Engine Exec Latency | Primary Failure Modes | Run Artifact Link |
|---|:---:|:---:|:---:|:---:|---|:---:|
| **Gemini 3.8 Flash (Medium)** | **100.0%** | **8 / 8** | 27.6s | **4.5 ms** | None (Zero failures across all 8 tasks) | [`eval_run_gemini-3.8-flash-medium_1794186799.json`](results/eval_run_gemini-3.8-flash-medium_1794186799.json) |
| **Claude Sonnet 4.6 (Thinking)** | **87.5%** | **7 / 8** | 6.8s | **4.8 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`eval_run_claude-sonnet-4-6_1794187183.json`](results/eval_run_claude-sonnet-4-6_1794187183.json) |
| **GPT-OSS 120B (Medium)** | **87.5%** | **7 / 8** | 5.5s | **5.5 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`eval_run_gpt-oss-120b-medium_1794187234.json`](results/eval_run_gpt-oss-120b-medium_1794187234.json) |
| **Gemini 3.8 Flash (Low)** | **87.5%** | **7 / 8** | **4.2s** | **5.4 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`eval_run_gemini-3.8-flash-low_1794186841.json`](results/eval_run_gemini-3.8-flash-low_1794186841.json) |
| **Golden Ground Truth** | **100.0%** | **8 / 8** | N/A | **3.8 ms** | Baseline Verification (0% False Negatives) | [`eval_run_offline_1794186318.json`](results/eval_run_offline_1794186318.json) |
| **Offline Reference / Naive** | **0.0%** | **0 / 8** | N/A | **2.6 ms** | 100% Trap Detection (Metric skew, row loss, O(N²) joins) | [`eval_run_offline_1794186320.json`](results/eval_run_offline_1794186320.json) |

📖 **For in-depth analysis and charts, read the full [Benchmark Report](BENCHMARK_REPORT.md).**  
🎥 **For video presentation and slides, see the [Video Walkthrough Script](VIDEO_WALKTHROUGH_SCRIPT.md) and [Interactive Slides](walkthrough_presentation.html).**  
📋 **For the official hackathon submission summary, see [Submission Summary](SUBMISSION_SUMMARY.md).**

---

## 📊 The 8-Category Analytical Failure Taxonomy

| ID | Task Definition | Category | Real-World Scenario | Frontier Model Limitation Detected |
|:---:|---|---|---|---|
| **01** | [`task_01_fanout.json`](tasks/task_01_fanout.json) | **Chasm Trap / Fan-Out** | Orders + Discounts + Shipments aggregation | Joins 1:N tables before `GROUP BY`, multiplying sums 4x |
| **02** | [`task_02_sessionization.json`](tasks/task_02_sessionization.json) | **Sessionization (Gaps & Islands)** | Clickstream event logs with 30-min timeout | Misuses `ROW_NUMBER()` instead of cumulative step flags |
| **03** | [`task_03_scd2_join.json`](tasks/task_03_scd2_join.json) | **SCD Type 2 Point-in-Time Joins** | Historical currency conversion as-of transaction | Misses open-ended `NULL` bounds (`valid_to IS NULL`), dropping active rows |
| **04** | [`task_04_three_valued_logic.json`](tasks/task_04_three_valued_logic.json) | **Three-Valued Logic in Anti-Joins** | Un-churned customer cohort extraction | Uses `NOT IN` with subquery NULLs, returning 0 rows |
| **05** | [`task_05_window_frame_bounds.json`](tasks/task_05_window_frame_bounds.json) | **Window Frame Default Bounds** | Cumulative balance with duplicate timestamps | Uses default `RANGE` instead of `ROWS BETWEEN ...`, bunching peer rows |
| **06** | [`task_06_funnel_precedence.json`](tasks/task_06_funnel_precedence.json) | **Strict Funnel Precedence** | Multi-stage user onboarding conversion | Loses chronological ordering between sequential steps |
| **07** | [`task_07_quadratic_self_join.json`](tasks/task_07_quadratic_self_join.json) | **Quadratic Self-Joins** | Rolling 7-day moving revenue | Substitutes window scans with O(N²) triangular self-joins |
| **08** | [`task_08_sargable_pruning.json`](tasks/task_08_sargable_pruning.json) | **Non-SARGable Partition Pruning** | Event table date filtering | `BETWEEN` date boundary leaks into next month; wraps date in string functions |

---

## 🏗️ Architecture & Hardened Features

```
sql-frontier-eval/
├── verify.sh                     # 1-Step verification script (Unit tests + Gold + Offline)
├── run_eval.py                   # Unified CLI benchmark runner
├── requirements.txt              # Pinned dependencies (DuckDB, Pandas, PyArrow, etc.)
├── conftest.py                   # Pytest test path configuration
├── BENCHMARK_REPORT.md           # Comprehensive publication report & empirical insights
├── SUBMISSION_SUMMARY.md         # Official hackathon form submission text
├── VIDEO_WALKTHROUGH_SCRIPT.md   # 4.5-minute video walkthrough teleprompter script
├── walkthrough_presentation.html # Interactive HTML presentation slide deck
├── harness/
│   ├── engine.py                 # SQLEvalEngine: In-memory DuckDB sandbox with JSON profiling
│   ├── grader.py                 # SQLGrader: Semantic value equivalence & operator checks
│   └── llm.py                    # Multi-provider client (Antigravity CLI + OpenRouter)
├── tasks/                        # 8 Challenge definitions with setup, golden, and naive SQL
│   ├── task_01_fanout.json
│   ├── task_02_sessionization.json
│   ├── task_03_scd2_join.json
│   ├── task_04_three_valued_logic.json
│   ├── task_05_window_frame_bounds.json
│   ├── task_06_funnel_precedence.json
│   ├── task_07_quadratic_self_join.json
│   └── task_08_sargable_pruning.json
├── tests/
│   ├── test_harness.py           # 8 Unit tests for engine sandboxing, sorting, profiling
│   └── test_llm.py               # 4 Unit tests for SQL regex block parsing
└── results/                      # Persisted JSON benchmark runs
    ├── eval_run_gemini-3.8-flash-medium_1794186799.json
    ├── eval_run_gemini-3.8-flash-low_1794186841.json
    ├── eval_run_offline_1794186318.json
    └── eval_run_offline_1794186320.json
```

### Key Hardening Highlights
* **Zero-Flakiness Row Sorting**: Relational SQL outputs without `ORDER BY` are unordered multisets. `SQLGrader` sorts both candidate and golden DataFrames deterministically before value assertion, preventing false failures caused by parallel worker row permutations.
* **Decimal & Floating Tolerance**: DuckDB `DECIMAL` types are coerced to `float64` so numerical tolerance (`atol=1e-3, rtol=1e-3`) applies reliably.
* **Deep Physical Plan Profiling**: Traverses DuckDB's `EXPLAIN (FORMAT JSON)` operator tree to measure intermediate cardinalities and automatically flag anti-patterns (`CROSS_PRODUCT`, `BLOCKWISE_NL_JOIN`, `PIECEWISE_MERGE_JOIN`).
* **Automated Walkthrough Diagnostics**: On evaluation failure, the harness automatically generates a comprehensive terminal walkthrough featuring:
  - **Beautified SQL**: Candidate and golden queries formatted with uppercase keywords and clean CTE/join indentation via `sqlparse`.
  - **Tabular Comparison**: Actual vs. expected output side-by-side in readable ASCII grid tables.
  - **Root Cause Discrepancy**: Exact cell divergence, arithmetic delta, inflation multiplier, and analytical failure explanation.

---

## 🚀 Quick Start

### 1. Prerequisites & Installation
Ensure you have Python 3.10+ installed.

```bash
# Clone and navigate to repository
git clone https://github.com/sql-frontier-eval.git
cd sql-frontier-eval

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. One-Step Verification
Run the verification suite to execute unit tests, verify ground-truth baselines, and test offline failure detection:

```bash
./verify.sh
```

---

## 🧪 Running Evaluations

### Sanity Verification (Ground Truth Baseline)
Validates that all golden queries pass 100% with zero false negatives:
```bash
python run_eval.py --test-gold
```

### Offline Mode (Testing Local Reference Queries)
Evaluates candidate queries stored in task files without requiring an API key:
```bash
python run_eval.py --model offline
```

When an eval fails, a detailed walkthrough is automatically printed:
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
  |    |   merchant_id | merchant_name    |   total_gross_sales |   total_discount_amount |
  +====+===============+==================+=====================+=========================+
  |  0 |             1 | Acme Electronics |                 100 |                      15 |
  +----+---------------+------------------+---------------------+-------------------------+

3. FAILURE ANALYSIS & ROOT CAUSE
• Value Discrepancy: 'total_gross_sales' at Row 0 expected 100.0, got 400.0 (+300.00 / 4.0x inflation).
• Root Cause: Joining two 1:N child tables before grouping created a 2 * 2 = 4x Cartesian fan-out.
==========================================================================================
```

### Live Evaluation via Gemini (Antigravity CLI)
Benchmark frontier models live in authenticated environments:

```bash
# Evaluate Gemini 3.8 Flash with Medium Reasoning (100% Score)
python run_eval.py --model gemini-3.8-flash-medium

# Evaluate Gemini 3.8 Flash with Low Reasoning (Fast 4s Inference)
python run_eval.py --model gemini-3.8-flash-low

# Evaluate Gemini 3.8 Flash with High Reasoning
python run_eval.py --model gemini-3.8-flash-high
```

### Live Evaluation via OpenRouter
Benchmark frontier models across providers using OpenRouter:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."

# Evaluate Claude 3.5 Sonnet
python run_eval.py --model "anthropic/claude-3.5-sonnet" --verbose

# Evaluate GPT-4o
python run_eval.py --model "openai/gpt-4o" --verbose

# Evaluate Gemini 2.0 Flash
python run_eval.py --model "google/gemini-2.0-flash-001" --verbose
```

All evaluation runs automatically persist structured JSON reports in `results/eval_run_<model>_<timestamp>.json`.

---

## 🛠️ Running the Test Suite

```bash
pytest tests/ -v
```
All 12 unit tests verify engine sandboxing, profile extraction, column matching, deterministic sorting, and SQL block extraction.

---

## 🤝 AI-Assisted Development Acknowledgement

In compliance with hackathon submission guidelines, we transparently disclose and acknowledge the use of **AI-assisted development**:
* **Pair Programming Partner**: Developed with the assistance of **Google Antigravity (AGY)** agentic AI pair programming system powered by Gemini 3.8 Flash.
* **Human-in-the-Loop Oversight**: Benchmark design, analytical failure taxonomy curation, test fixture definitions, execution profiling rules, and mathematical verification were directed and validated by human analytical engineering review.

---

## 📜 License
MIT License.
