# SQL-Frontier-Eval: Benchmarking Frontier AI on Complex Analytical SQL

> **Evaluating semantic correctness, mathematical KPI integrity, and plan efficiency on modern analytical engines.**  
> Built for the [micro1 Eval Hackathon](https://www.hackerrank.com/event/micro1-eval-hackathon) on HackerRank Engage.

[![CI](https://github.com/sethusrinivasan/sql-frontier-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/sethusrinivasan/sql-frontier-eval/actions/workflows/ci.yml)
[![Unit Tests](https://img.shields.io/badge/pytest-12%20passed-3fb950.svg?logo=pytest&logoColor=white)](tests/)
[![Golden Baseline](https://img.shields.io/badge/golden%20suite-120%2F120%20(100%25)-3fb950.svg?logo=duckdb&logoColor=white)](results/eval_run_offline_1794210761.json)
[![Zero-LLM CI](https://img.shields.io/badge/CI%20Dependency-Zero%20LLM%20Required-success.svg?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![Engine: DuckDB 2.0](https://img.shields.io/badge/Engine-DuckDB%202.0-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Hackathon: micro1](https://img.shields.io/badge/micro1-Eval%20Hackathon-FF5722.svg?logo=hackerrank&logoColor=white)](https://www.hackerrank.com/event/micro1-eval-hackathon)
[![Gemini 3.8 Flash](https://img.shields.io/badge/Gemini%203.8%20Flash-100%25%20(8%2F8)-4285F4.svg?logo=google&logoColor=white)](results/eval_run_gemini-3.8-flash-medium_1794186799.json)
[![Claude Opus 4.6](https://img.shields.io/badge/Claude%20Opus%204.6-100%25%20(8%2F8)-D97757.svg?logo=anthropic&logoColor=white)](results/eval_run_agy_claude-opus-4-6-thinking_1794196279.json)
[![GPT-OSS 120B](https://img.shields.io/badge/GPT--OSS%20120B-87.5%25%20(7%2F8)-10A37F.svg?logo=openai&logoColor=white)](results/eval_run_agy_gpt-oss-120b-medium_1794196331.json)
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
| **Claude Opus 4.6 (Thinking)** | **100.0%** | **8 / 8** | 6.9s | **4.6 ms** | None (Zero failures across all 8 tasks) | [`eval_run_agy_claude-opus-4-6-thinking_1794196279.json`](results/eval_run_agy_claude-opus-4-6-thinking_1794196279.json) |
| **Gemini 3.8 Flash (Low)** | **100.0%** | **8 / 8** | **4.6s** | **5.4 ms** | None (Zero failures across all 8 tasks, Fastest) | [`eval_run_agy_gemini-3.8-flash-low_1794195725.json`](results/eval_run_agy_gemini-3.8-flash-low_1794195725.json) |
| **Gemini 3.8 Flash (Medium)** | **100.0%** | **8 / 8** | 27.6s | **4.5 ms** | None (Zero failures across all 8 tasks) | [`eval_run_gemini-3.8-flash-medium_1794186799.json`](results/eval_run_gemini-3.8-flash-medium_1794186799.json) |
| **Claude Sonnet 4.6 (Thinking)** | **87.5%** | **7 / 8** | 6.3s | **4.8 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`eval_run_agy_claude-sonnet-4-6_1794196223.json`](results/eval_run_agy_claude-sonnet-4-6_1794196223.json) |
| **GPT-OSS 120B (Medium)** | **87.5%** | **7 / 8** | 6.5s | **5.5 ms** | Strict Funnel Precedence (`CROSS_PRODUCT` scalar join) | [`eval_run_agy_gpt-oss-120b-medium_1794196331.json`](results/eval_run_agy_gpt-oss-120b-medium_1794196331.json) |
| **Gemini 3.8 Flash (High)** | **75.0%** | **6 / 8** | 51.9s | **4.3 ms** | Tasks 01 & 06 timed out during deep reasoning | [`eval_run_agy_gemini-3.8-flash-high_1794196172.json`](results/eval_run_agy_gemini-3.8-flash-high_1794196172.json) |
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

## 🌐 Comprehensive 120-Task & 5-Domain Evaluation Suite

In addition to the 8 core failure-mode traps, SQL-Frontier-Eval includes **102 modern analytical tasks** across five frontier analytical domains plus **10 hardened frontier trap challenges**:

| Domain | Queries | DuckDB Engine Capabilities Evaluated | Real-World Scenario Focus |
|---|:---:|---|---|
| **1. Temporal & Time-Series** | `Q01` – `Q25` | `ASOF JOIN`, `generate_series`, `IGNORE NULLS` LOCF, `time_bucket` | Tick-level trade matching, point-in-time FX, sensor gap filling, bitemporal audit, multi-touch attribution |
| **2. Vector & Embeddings** | `Q26` – `Q50` | `array_cosine_similarity`, `array_distance`, `array_inner_product`, `FLOAT[N]`, `QUALIFY` | RAG retrieval, ticket deduplication, ColBERT MaxSim in SQL, K-Means clustering, MMR diversity reranking |
| **3. Search & Hybrid Retrieval** | `Q51` – `Q75` | `PRAGMA create_fts_index`, `match_bm25`, `levenshtein`, `jaro_winkler_similarity`, RRF | Reciprocal Rank Fusion (BM25 + Dense Vectors), fuzzy typo-tolerant matching, faceted JSON filters |
| **4. Graph & Hierarchies** | `Q76` – `Q88` | `WITH RECURSIVE`, path tracking arrays, transitive closures | Multi-tier BOM cost rollups, reporting hierarchies, sybil fraud ring tracking, critical path scheduling |
| **5. Warehouse & Statistical** | `Q89` – `Q102` | Pre-aggregated CTEs, `NOT EXISTS`, `PIVOT`, `UNPIVOT`, `list_transform`, `MAD`, `NTILE` | Chasm trap fan-out prevention, 3-valued null logic, robust outlier detection, Kaplan-Meier survival |
| **6. Hardened Frontier Traps** | `111` – `120` | `ASOF` tolerance, array cycle guards, RRF rank fusion, normalized decay | Exposing hallucinated recursive syntax, array type errors, and revenue over-allocation |

* **Full Golden Ground-Truth Baseline:** **120 / 120 Passed (100.0%)** ([`eval_run_offline_1794210761.json`](results/eval_run_offline_1794210761.json)).
* **Hardened Trap Model Cracks:** GPT-OSS 120B passed 6/9 (66.7%), stumbling on circular CTE recursion (Task 112), array concat operator (Task 116), and unnormalized decay attribution (Task 119). Gemini 3.8 Flash achieved 9/9 (100.0%).
* **Detailed Catalog Manifest:** [`catalog/analytical_queries_100.json`](catalog/analytical_queries_100.json) and [`catalog/queries/`](catalog/queries/).
* **Automated CI/CD:** GitHub Actions workflow runs the 120-task golden suite, unit tests, and offline naive trap assertions with zero LLM requirements.

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
├── sql_frontier_eval_walkthrough.mp4 # Full 1080p narrated video walkthrough with burned-in CC (3m 53s)
├── video/                        # Video generation assets, slide scenes & SRT captions
│   ├── build_video.py            # Automated video compilation pipeline
│   └── walkthrough_captions.srt  # Synchronized closed-caption subtitles
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
    ├── eval_run_gemini-3.8-flash-medium_1794186799.json  # 8/8 Passed (100.0%)
    ├── eval_run_claude-opus-4-6-thinking_1794187547.json # 7/8 Passed (87.5%)
    ├── eval_run_claude-sonnet-4-6_1794187183.json        # 7/8 Passed (87.5%)
    ├── eval_run_gpt-oss-120b-medium_1794187234.json      # 7/8 Passed (87.5%)
    ├── eval_run_gemini-3.8-flash-low_1794186841.json     # 7/8 Passed (87.5%)
    ├── eval_run_gemini-3.8-flash-high_1794187896.json    # 6/8 Passed (75.0%)
    ├── eval_run_offline_1794186318.json                  # Golden Ground Truth (100.0%)
    └── eval_run_offline_1794186320.json                  # Naive Trap Baseline (0.0%)
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

### Live Evaluation via Frontier CLI (Antigravity Models)
Benchmark frontier models directly in authenticated environments:

```bash
# Evaluate Gemini 3.8 Flash with Medium Reasoning (100% Score)
python run_eval.py --model gemini-3.8-flash-medium

# Evaluate Claude Opus 4.6 Thinking (87.5% Score)
python run_eval.py --model claude-opus-4-6-thinking

# Evaluate Claude Sonnet 4.6 Thinking (87.5% Score)
python run_eval.py --model claude-sonnet-4-6

# Evaluate GPT-OSS 120B Medium (87.5% Score)
python run_eval.py --model gpt-oss-120b-medium

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
