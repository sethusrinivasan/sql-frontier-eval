# SQL-Frontier-Eval: Benchmarking Frontier AI on Complex Analytical SQL

> **Evaluating semantic correctness and execution efficiency on modern analytical engines.**  
> Built for the [micro1 Eval Hackathon](https://www.hackerrank.com/event/micro1-eval-hackathon) on HackerRank Engage.

---

## 📌 Motivation: Why Analytical SQL Evals Matter

Existing text-to-SQL benchmarks (e.g. Spider, BIRD) primarily test simple relational lookups and basic textbook joins. However, in enterprise analytics (Snowflake, BigQuery, Databricks, DuckDB), data engineers face subtle and catastrophic failure modes from frontier LLMs:

1. **Silent Metric Corruption (The Chasm Trap)**: When calculating aggregates across multiple 1-to-many child tables (e.g. Orders joined to both Discounts and Shipments), LLMs generate multi-table joins before `GROUP BY`. This cross-multiplies records and silently inflates financial KPIs (e.g. 4x gross sales) without triggering any SQL syntax errors.
2. **Computational Anti-Patterns**: Frontier models frequently substitute window functions with quadratic triangular self-joins (`ON a.ts >= b.ts - 30`), triggering Cartesian row explosions that cause memory spills and crash analytical warehouse clusters.
3. **Subtle Logical Pitfalls**: Models routinely fail three-valued SQL logic (`NOT IN` on subqueries with `NULL`s), miss boundary conditions on temporal SCD Type 2 joins, or misconfigure window frame default bounds.

**SQL-Frontier-Eval** provides a reproducible, deterministic evaluation suite to expose where frontier models (Claude 3.5 Sonnet, GPT-4o, Gemini Pro) break down and guide the generation of optimal analytical queries.

---

## 🏗️ Architecture & Hardened Features

```
sql-frontier-eval/
├── verify.sh             # One-step verification script (runs tests, gold check, offline eval)
├── run_eval.py           # Unified evaluation runner CLI
├── requirements.txt      # Minimal, pinned dependencies
├── conftest.py           # Pytest test path configuration
├── harness/
│   ├── engine.py         # SQLEvalEngine: In-memory DuckDB sandbox with JSON profiling
│   ├── grader.py         # SQLGrader: Semantic value equivalence & operator anti-pattern checks
│   └── llm.py            # OpenRouterClient: Prompt framing & regex SQL extraction
├── tasks/
│   └── task_01_fanout.json # E-Commerce Chasm Trap challenge definition
├── tests/
│   ├── test_harness.py   # 8 unit tests for engine isolation, grading, sorting, and profiler
│   └── test_llm.py       # 4 unit tests for regex SQL parsing
└── results/              # Timestamped run artifacts and metrics
```

### Key Hardening Highlights
* **Zero Flakiness Row Sorting**: Relational SQL outputs without `ORDER BY` are unordered multisets. `SQLGrader` sorts both candidate and golden DataFrames deterministically before value assertion, preventing false failures caused by parallel worker row permutations.
* **Decimal & Floating Tolerance**: DuckDB `DECIMAL` types are coerced to `float64` so numerical tolerance (`atol=1e-3, rtol=1e-3`) applies reliably.
* **Deep Execution Profiling**: Toggles `PRAGMA enable_profiling = 'json'` in DuckDB and traverses the operator tree to measure intermediate cardinalities, CPU time, and automatically flag anti-patterns (`CROSS_PRODUCT`, `BLOCKWISE_NL_JOIN`).
* **Pinpointed Diagnostics & Walkthroughs**: On evaluation failure, the harness automatically generates a comprehensive walkthrough featuring:
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

### Offline Mode (Testing Local Reference Query)
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
[Candidate Query (Tested)]
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

### Live Evaluation via OpenRouter
Benchmark frontier models live using OpenRouter:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."

# Evaluate Claude 3.5 Sonnet
python run_eval.py --model "anthropic/claude-3.5-sonnet" --verbose

# Evaluate GPT-4o
python run_eval.py --model "openai/gpt-4o" --verbose

# Evaluate Gemini 2.0 Flash
python run_eval.py --model "google/gemini-2.0-flash-001" --verbose
```

Evaluation runs automatically save structured JSON reports in `results/eval_run_<model>_<timestamp>.json`.

---

## 📊 Analytical Failure Taxonomy

| ID | Task Category | Real-World Scenario | Frontier Model Limitation |
|---|---|---|---|
| **01** | **Chasm Trap / Fan-Out** | Orders + Discounts + Shipments aggregation | Joins 1:N tables before `GROUP BY`, multiplying sums |
| **02** | **Sessionization (Gaps & Islands)** | Clickstream event logs with 30-min timeout | Misuses `LAG()` or generates quadratic recursive CTEs |
| **03** | **SCD Type 2 Point-in-Time Joins** | Historical currency conversion as-of transaction | Misses open-ended `NULL` bounds or boundary equality |
| **04** | **Three-Valued Logic in Anti-Joins** | Un-churned customer cohort extraction | Uses `NOT IN` with subquery nulls, returning 0 rows |
| **05** | **Window Frame Default Bounds** | Cumulative balance with duplicate timestamps | Uses default `RANGE` instead of `ROWS BETWEEN ...` |
| **06** | **Strict Funnel Precedence** | Multi-stage user onboarding conversion | Loses chronological ordering between sequential steps |
| **07** | **Quadratic Self-Joins** | Rolling 30-day moving averages | Substitutes window scans with O(N²) triangular self-joins |
| **08** | **Non-SARGable Partition Pruning** | Event table date filtering | Wraps partition columns in scalar string functions |

---

## 🛠️ Running the Test Suite

```bash
pytest tests/ -v
```
All 12 unit tests verify engine sandboxing, profile extraction, column matching, deterministic sorting, and SQL extraction.

---

## 📜 License
MIT License.
