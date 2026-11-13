# SQL-Frontier-Eval: Benchmarking Frontier AI on Complex Analytical SQL

> **Evaluating semantic correctness, mathematical KPI integrity, physical execution plans, and indexing architecture across modern analytical engines (DuckDB & PostgreSQL).**  
> Built for the [micro1 Eval Hackathon](https://www.hackerrank.com/event/micro1-eval-hackathon) on HackerRank Engage.

[![CI](https://github.com/sethusrinivasan/sql-frontier-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/sethusrinivasan/sql-frontier-eval/actions/workflows/ci.yml)
[![Unit Tests](https://img.shields.io/badge/pytest-14%20passed-3fb950.svg?logo=pytest&logoColor=white)](tests/)
[![DuckDB Suite](https://img.shields.io/badge/DuckDB%20Suite-120%2F120%20(100%25)-3fb950.svg?logo=duckdb&logoColor=white)](results/eval_run_offline_1794210761.json)
[![PostgreSQL Suite](https://img.shields.io/badge/PostgreSQL%2018-120%2F120%20(100%25)-336791.svg?logo=postgresql&logoColor=white)](results/eval_run_postgres_offline_1794601660.json)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-sethusrinivasan.github.io%2Fsql--frontier--eval-1f6feb.svg?logo=github&logoColor=white)](https://sethusrinivasan.github.io/sql-frontier-eval/)
[![Data Volume: 108M+](https://img.shields.io/badge/Data%20Volume-108M%2B%20Records%20Tested-3fb950.svg?logo=duckdb&logoColor=white)](https://sethusrinivasan.github.io/sql-frontier-eval/)
[![Engine: DuckDB 2.0](https://img.shields.io/badge/Engine-DuckDB%202.0-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Engine: PostgreSQL 18.7](https://img.shields.io/badge/Engine-PostgreSQL%2018.7%20%2B%20pgvector-336791.svg?logo=postgresql&logoColor=white)](docker-compose.yml)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Claude Opus 4.6](https://img.shields.io/badge/Claude%20Opus%204.6-98.3%25%20(118%2F120)-D97757.svg?logo=anthropic&logoColor=white)](results/eval_run_agy_claude-opus-4-6-thinking_1794196279.json)
[![Gemini 3.8 Flash Medium](https://img.shields.io/badge/Gemini%203.8%20Flash%20Medium-96.7%25%20(116%2F120)-4285F4.svg?logo=google&logoColor=white)](results/eval_run_gemini-3.8-flash-medium_1794186799.json)
[![Gemini 3.8 Flash Low](https://img.shields.io/badge/Gemini%203.8%20Flash%20Low-95.8%25%20(115%2F120)-4285F4.svg?logo=google&logoColor=white)](results/eval_run_agy_gemini-3.8-flash-low_1794212683.json)
[![Claude Sonnet 4.6](https://img.shields.io/badge/Claude%20Sonnet%204.6-94.2%25%20(113%2F120)-D97757.svg?logo=anthropic&logoColor=white)](results/eval_run_agy_claude-sonnet-4-6_1794196223.json)
[![GPT-OSS 120B](https://img.shields.io/badge/GPT--OSS%20120B-90.8%25%20(109%2F120)-10A37F.svg?logo=openai&logoColor=white)](results/eval_run_agy_gpt-oss-120b-medium_1794210710.json)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 Motivation: Why Analytical SQL Evals Matter

Existing text-to-SQL benchmarks (e.g. Spider, BIRD) primarily test simple relational lookups and basic textbook joins. However, in enterprise analytics and modern data architectures (Snowflake, BigQuery, Databricks, DuckDB, PostgreSQL), data engineers face subtle and catastrophic failure modes from frontier LLMs:

1. **Silent Metric Corruption (The Chasm Trap)**: When calculating aggregates across multiple 1-to-many child tables (e.g. Orders joined to both Discounts and Shipments), LLMs generate multi-table joins before `GROUP BY`. This cross-multiplies records and silently inflates financial KPIs (e.g. **4x gross sales**) without triggering any SQL syntax errors.
2. **Computational Anti-Patterns & Physical Bottlenecks**: Frontier models frequently substitute window functions with quadratic triangular self-joins (`ON a.ts >= b.ts - 30`), triggering Cartesian row explosions that cause memory spills and crash analytical warehouse clusters.
3. **Subtle Logical Pitfalls**: Models routinely fail three-valued SQL logic (`NOT IN` on subqueries with `NULL`s), miss boundary conditions on temporal SCD Type 2 joins, or misconfigure window frame default bounds.
4. **Physical Database & Indexing Blindspot**: LLMs consistently recommend generic single-column B-Tree indexes that columnar OLAP engines (DuckDB) completely bypass, while failing to recommend Composite Covering Indexes (`INCLUDE`), HNSW vector indexes, GIN trigram indexes, or BRIN block-range indexes in relational engines (PostgreSQL).

**SQL-Frontier-Eval** provides an empirical, multi-database evaluation suite (evaluating **120 tasks across 108M+ records**) to expose where frontier models break down and guide the generation of optimal analytical queries and physical database artifacts.

---

## 🏆 Headline Multi-Model Benchmark Leaderboard (All 120 Tasks)

Evaluated across the full 120-task suite against **1,000,000+ records per table** across both **DuckDB 2.0** and **PostgreSQL 18.7**:

### ⚡ DuckDB 2.0 In-Memory Engine (Columnar OLAP)

| Model / Baseline | Pass Rate | Tasks Passed | Avg Model Latency | Engine Exec Latency (1M) | Primary Analytical Failure Modes |
|---|:---:|:---:|:---:|:---:|---|
| **Claude Opus 4.6 (Thinking)** | **98.3%** | **118 / 120** | 14.8s | **219.4 ms** | Zero failures on core traps; 2 deep recursive cycle boundary edge cases |
| **Gemini 3.8 Flash (Medium)** | **96.7%** | **116 / 120** | 12.4s | **224.1 ms** | 4 edge cases: sliding window trimmed mean, graph recursion guard, ASOF expiry edge |
| **Gemini 3.8 Flash (Low)** | **95.8%** | **115 / 120** | **4.6s** | **232.2 ms** | Full 120-task suite: 5 edge-case value/shape divergences (bitemporal limit, FX arbitrage) |
| **Claude Sonnet 4.6 (Thinking)** | **94.2%** | **113 / 120** | 9.1s | **228.6 ms** | 7 edge cases: strict funnel scalar join precedence, linear interpolation, market basket lift |
| **Gemini 3.8 Flash (High)** | **92.5%** | **111 / 120** | 38.6s | **236.4 ms** | 9 edge cases: reasoning timeouts on microsecond ASOF bounds & non-SARGable conversions |
| **GPT-OSS 120B (Medium)** | **90.8%** | **109 / 120** | 8.2s | **245.8 ms** | 11 edge cases: unbounded recursive CTE cycles without acyclic guards & quadratic non-equi joins |
| **Golden Ground Truth Baseline** | **100.0%** | **120 / 120** | N/A | **217.8 ms** | Ground Truth Baseline (0% False Negatives on 1M+ Records) |

### 🐘 PostgreSQL 18.7 + Extensions (Docker Compose)

| Model / Baseline | Pass Rate | Tasks Passed | Avg Model Latency | Engine Exec Latency (1M) | Primary Analytical Failure Modes |
|---|:---:|:---:|:---:|:---:|---|
| **Claude Opus 4.6 (Thinking)** | **96.7%** | **116 / 120** | 15.2s | **184.2 ms** | 4 edge cases: window frame default exclusions, strict funnel scalar join precedence |
| **Gemini 3.8 Flash (Medium)** | **95.0%** | **114 / 120** | 12.8s | **192.5 ms** | 6 edge cases: rolling distinct interval merge, recursive path string format normalization |
| **Gemini 3.8 Flash (Low)** | **93.3%** | **112 / 120** | **4.8s** | **198.7 ms** | 8 edge cases: bracket array syntax divergences, bitemporal point-in-time join precision |
| **Claude Sonnet 4.6 (Thinking)** | **91.7%** | **110 / 120** | 9.4s | **205.1 ms** | 10 edge cases: missing covering indexes causing nested loop degradation, strict funnel precedence |
| **Gemini 3.8 Flash (High)** | **90.0%** | **108 / 120** | 39.4s | **210.3 ms** | 12 edge cases: reasoning timeouts on multi-stage CTE graphs, nested loop timeouts |
| **GPT-OSS 120B (Medium)** | **86.7%** | **104 / 120** | 8.7s | **226.4 ms** | 16 edge cases: unindexed cross joins on skewed foreign keys, statement timeouts |
| **Golden Ground Truth Baseline** | **100.0%** | **120 / 120** | N/A | **178.6 ms** | Ground Truth Baseline on PostgreSQL 18.7 + pgvector (0% False Negatives) |

---

## 🌐 Live Interactive Benchmark Dashboard (GitHub Pages)

The full interactive reporting suite is deployed live at **[https://sethusrinivasan.github.io/sql-frontier-eval/](https://sethusrinivasan.github.io/sql-frontier-eval/)**, tested across **108,027,582 records across 148 tables**:

* 🎛️ **Interactive Database Engine Switcher**: Toggle dynamically between **⚡ DuckDB 2.0 In-Memory** and **🐘 PostgreSQL 18.7**. Switch views instantly to inspect engine-specific KPIs, multi-model leaderboards, latency breakdowns, and query execution plans.
* 📊 **Executive Benchmark Dashboard**: High-level KPI summary, multi-model leaderboard comparison, domain scorecards, real-time live search, domain filter pills, and query status matrix.
* 🔍 **120 Query Deep-Dive Pages** (also in [`reports/queries/`](reports/queries/)): Dedicated per-query reports detailing:
  - **What It Means**: Business scenario, analytical requirement, and semantic failure trap analysis.
  - **Graphical Execution Plans**: Physical operator trees with radiant flame highlights (`🔥 BOTTLENECK`) on nodes consuming $\ge 20\%$ cost or heavy latency.
  - **Physical Profiling & Operator Costs**: Millisecond-level operator attribution, memory peak volumes, and disk spill metrics.
  - **Colored & Formatted Queries**: Side-by-side candidate SQL vs golden reference vs setup DDL with syntax highlighting.
  - **Tabular Results**: Side-by-side actual vs expected outputs.

---

## 🔬 Empirical Query Execution Plan & Physical Indexing Analysis

For a comprehensive deep dive, see [`PHYSICAL_PLAN_OPTIMIZATION_AND_LLM_ANALYSIS.md`](PHYSICAL_PLAN_OPTIMIZATION_AND_LLM_ANALYSIS.md).

### 1. Cumulative Operator Runtime Distribution (DuckDB 2.0)
Across all 120 evaluated tasks, cumulative operator execution time totaled **43,894.6 ms**:

```text
Cumulative Physical Operator Time Breakdown:
────────────────────────────────────────────────────────────────────────
WINDOW                [████████████████              ] 30.0% (13.16s)
HASH_GROUP_BY         [██████████                    ] 19.5% (8.55s)
ORDER_BY              [████████                      ] 15.2% (6.66s)
PROJECTION            [█████                         ]  9.8% (4.31s)
ASOF_JOIN             [███                           ]  6.3% (2.76s)
TABLE_SCAN            [███                           ]  5.5% (2.41s)
HASH_JOIN             [██                            ]  4.5% (1.97s)
PIECEWISE_MERGE_JOIN  [██                            ]  4.2% (1.85s)
REMAINDER             [██                            ]  5.0% (2.22s)
────────────────────────────────────────────────────────────────────────
```

> [!IMPORTANT]
> **Key Insight**: Sequential table scans account for **only 5.5%** of analytical query runtime! Over **94.5%** of execution time is spent processing data in-memory: evaluating window functions, hashing group keys, sorting intermediate streams, and merging intervals.

### 2. The Indexing Paradox: Columnar OLAP vs. Row-Store PostgreSQL
* **In DuckDB (Columnar OLAP)**: Traditional secondary B-Tree/ART indexes do **not** optimize analytical operations (`ASOF JOIN`, `WINDOW`, `GROUP BY`, range filters). The query optimizer completely ignores ART indexes because SIMD vector scans over contiguous column chunks (2048 tuples per vector) and Min-Max Zone Maps process 1,000,000 records in **< 0.7 ms**. Pointer-based tree traversal destroys CPU cache locality.
  - *The Real OLAP Lever*: **Physical Ingestion Clustering (`ORDER BY` at DDL/ingestion)** aligns data with row groups, achieving a **1.86x speedup** on range scans by skipping unneeded row groups without reading pages.
* **In PostgreSQL 18+ (Relational + Extensions)**: Without indexes, PostgreSQL falls back to row-by-row `Seq Scan` and explosive `Nested Loop` joins ($O(N^2)$), causing 10x-50x latency regressions. However, generic single-column B-Trees are insufficient:
  - **Composite Covering Indexes (`INCLUDE`)**: Creating `CREATE INDEX ON table (filter_col, join_col) INCLUDE (payload_cols);` enables pure *Index-Only Scans* without touching heap pages.
  - **HNSW Vector Indexes**: `CREATE INDEX USING hnsw (embedding vector_cosine_ops)` yields **50x-100x speedup** on top-K approximate nearest neighbors compared to brute-force scans.
  - **GIN Trigram Indexes**: `USING gin (col gin_trgm_ops)` accelerates fuzzy string matching and regex.
  - **BRIN (Block Range Indexes)**: On append-only timestamp tables, BRIN provides block-skipping similar to DuckDB Zone Maps with < 1% the storage overhead of a B-Tree.

### 3. Why Frontier LLMs Failed to Recommend the Right Indices
1. **The "SELECT-Only" Prompt Scoping Blindspot**: Standard text-to-SQL benchmarks frame prompts as *"Write a SQL query that answers question X given schema Y"*, treating table DDL and index creation as immutable external constants. Unless explicitly given a dual mandate to design physical storage, models will never emit `CREATE INDEX` or `ORDER BY` DDL.
2. **OLTP Textbook Muscle Memory**: Pre-training corpora (GitHub, StackOverflow) are dominated by web application CRUD stacks (Django, Rails, MySQL, Postgres). Models reflexively advise: *"Put a B-Tree index on foreign keys"*, ignorant of columnar SIMD scanning or specialized access methods.
3. **Cardinality & Data Distribution Blindness**: LLMs generate queries in a statistical vacuum, unaware of table row counts (10 vs 1,000,000) or distinct value cardinality (NDV). In `task_072`, joining on non-selective `zip_code` produced **250 billion Cartesian string comparisons**, exhausting RAM.
4. **Absence of Cost-Based Execution Feedback**: Text-to-text generation lacks an iterative `EXPLAIN ANALYZE` feedback loop to observe operator bottlenecks, row-count estimation errors, or disk spills.

### 4. What Models Could Have Done Better to Optimize DB Artifact Setup
1. **Dual-Phase Prompting**: Formulate storage layout (clustering keys, partition boundaries, and indexes) *before* query formulation, equipped with table row counts and column NDV statistics.
2. **Automated `EXPLAIN (ANALYZE, FORMAT JSON)` Feedback Loop**: Profile execution trees, detect nodes consuming $> 20\%$ cost or spilling to disk, and iteratively refine indexes or rewrite query algebra.
3. **Engine-Aware Primitive In-Context Guidance**: Instruct models on target engine physical strengths (e.g., DuckDB native `ASOF JOIN`, `QUALIFY`, `vss` HNSW extension, and Zone Map pruning vs. PostgreSQL `pgvector`, `pg_trgm`, `btree_gist`, and Covering Indexes).

---

## 🐘 PostgreSQL 18+ Docker Compose Setup

SQL-Frontier-Eval includes a complete, production-grade Docker Compose setup for the latest **PostgreSQL 18** with pre-configured extensions:

### 1. Launching PostgreSQL via Docker Compose
Use the automated setup script or Docker Compose directly:

```bash
# Automated setup (builds container, configures extensions, verifies health)
./setup_postgres.sh

# Or start directly via Docker Compose
docker compose up -d --build
```

### 2. Pre-Configured Extensions
The container automatically builds and initializes the following extensions via [`docker/init.sql`](docker/init.sql):

| Extension | Version | Purpose in Analytical Benchmark |
|---|:---:|---|
| **`vector` (`pgvector`)** | `0.8.7` | Dense vector embeddings, cosine similarity (`<=>`), L2 distance (`<->`), inner product (`<#>`), HNSW indexing |
| **`pg_trgm`** | `1.6` | Trigram matching, fuzzy string similarity, GIN text search indexing |
| **`fuzzystrmatch`** | `1.2` | Levenshtein distance, Soundex, Metaphone phonetics |
| **`btree_gist`** | `1.8` | GiST indexing for B-tree data types, exclusion constraints, range overlap temporal joins |
| **`tablefunc`** | `1.0` | Dynamic crosstab pivot tables, connectby hierarchical traversals |
| **`ltree`** | `1.3` | Hierarchical label trees and path queries |
| **`hstore`** | `1.8` | Key-value document storage |
| **`intarray`** | `1.5` | Integer array indexing and high-performance operations |
| **`uuid-ossp`** | `1.1` | Native UUID generation |

### 3. PostgreSQL Analytical Compatibility Layer
[`docker/init.sql`](docker/init.sql) and [`harness/engine.py`](harness/engine.py) provide seamless analytical function parity:
* `array_cosine_similarity(a, b)`: Vector cosine similarity ($1.0 - \text{distance}$)
* `array_distance(a, b)`: Euclidean $L_2$ vector distance
* `array_inner_product(a, b)`: Maximum inner product search (MIPS)
* `date_diff(unit, start, end)`: Microsecond, second, minute, hour, day, and month interval calculation
* `round(double precision, integer)`: Precision rounding for floating-point KPI metrics
* `list(x)`: Dynamic array aggregation compatible with DuckDB's `list()`
* `median(x)`: Continuous median aggregate via `percentile_cont(0.5)`
* `range(n)` / `range(start, end)`: Set-returning series generation

---

## 🚀 Quick Start

### 1. Installation
Ensure Python 3.10+ and Docker are installed:

```bash
# Clone repository
git clone https://github.com/sethusrinivasan/sql-frontier-eval.git
cd sql-frontier-eval

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (DuckDB, Pandas, Pygments, Psycopg2, Tabulate, Pytest, SQLParse)
pip install -r requirements.txt
```

### 2. Verify Everything with One Script
Run the comprehensive verification suite (tests unit test suite across DuckDB and PostgreSQL, golden baselines, and reference trap detection):

```bash
./verify.sh
```

---

## 🧪 Running Evaluations

### 1. Sanity Verification (Ground Truth Baseline)
```bash
# Run golden verification on DuckDB 2.0 (120 tasks)
python run_eval.py --engine=duckdb --test-gold

# Run golden verification on PostgreSQL 18+ (Docker)
python run_eval.py --engine=postgres --test-gold --tasks="tasks/task_026*.json"
```

### 2. Live Evaluation Across All Frontier Models
Benchmark all 6 frontier models available in Antigravity context:

```bash
# Run all models on DuckDB
python run_all_models.py --engine=duckdb

# Run all models on PostgreSQL
python run_all_models.py --engine=postgres

# Run a specific model
python run_eval.py --model agy/gemini-3.8-flash-low --engine=duckdb
python run_eval.py --model agy/claude-opus-4-6-thinking --engine=postgres
```

Supported Frontier Models:
* `agy/claude-opus-4-6-thinking`: Claude Opus 4.6 (Extended Thinking)
* `agy/gemini-3.8-flash-medium`: Gemini 3.8 Flash (Medium Reasoning)
* `agy/gemini-3.8-flash-low`: Gemini 3.8 Flash (Low Latency Reasoning)
* `agy/claude-sonnet-4-6`: Claude Sonnet 4.6 (Thinking)
* `agy/gpt-oss-120b-medium`: GPT-OSS 120B (Medium)
* `agy/gemini-3.8-flash-high`: Gemini 3.8 Flash (High Reasoning)

### 3. Generating Static HTML Benchmark Reports
Generate or refresh the interactive static HTML reporting suite:

```bash
python generate_reports.py \
    --results results/eval_run_agy_gemini-3.8-flash-low_1794212683.json \
    --out-dir reports \
    --target-rows 1000000
```

---

## 🛠️ Running the Test Suite

```bash
pytest tests/ -v
```

All 14 unit tests verify DuckDB and PostgreSQL sandboxing, schema isolation, profile operator extraction, column matching, ordered row enforcement, and SQL block extraction.

---

## 📜 License
MIT License.
