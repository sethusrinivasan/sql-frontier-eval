# micro1 Eval Hackathon: Official Submission Summary

### Project Title
**SQL-Frontier-Eval: Benchmarking Frontier AI on Complex Analytical SQL, Silent Metric Corruption, and Execution Anti-Patterns**

---

### 1. Short Description: What Was Built (2-3 paragraphs)

**SQL-Frontier-Eval** is an open-source, deterministic evaluation benchmark designed to test frontier language models on complex analytical SQL in modern columnar data warehouses (DuckDB, Snowflake, BigQuery, Databricks). While existing text-to-SQL benchmarks (e.g. Spider, BIRD) focus on simple relational lookups and textbook joins, SQL-Frontier-Eval exposes the most dangerous failure modes encountered in enterprise analytics: **silent metric corruption** and **computational blowups**.

The benchmark implements an **8-category analytical failure taxonomy** that spans:
1. Multi-table join fan-out / Chasm Traps (inflating financial KPIs 4x without syntax errors),
2. Inactivity gap sessionization (Gaps & Islands problems),
3. SCD Type 2 point-in-time joins with open-ended NULL bounds,
4. Three-valued logic anti-joins (`NOT IN` null traps silently returning 0 rows),
5. Window frame default bounds (omitted frames bundling duplicate timestamp peers together),
6. Strict multi-stage onboarding funnel precedence,
7. Quadratic triangular self-joins triggering $O(N^2)$ memory spills, and
8. Non-SARGable date predicate wrapping defeating columnar partition pruning.

Built on an isolated in-memory **DuckDB 2.0 engine**, the harness enforces **zero-flakiness multiset row sorting**, floating-point tolerance, and **physical execution plan profiling** (traversing EXPLAIN JSON operator trees to catch disallowed operators like `CROSS_PRODUCT` and `PIECEWISE_MERGE_JOIN`). When any evaluation fails, the harness automatically generates a comprehensive diagnostic walkthrough featuring beautified SQL queries, ASCII comparison tables, arithmetic delta calculation, and root-cause failure analysis.

---

### 2. What It Shows About Frontier Model Limitations

1. **Silent Correctness vs. Syntax Errors**: Frontier models achieve near-perfect syntax validity, but regularly fail domain-level semantic invariants. In our offline reference evaluations, naive queries passed execution without syntax warnings while silently multiplying gross revenues by 400% or dropping active customer segments to zero rows.
2. **Cross-Frontier Model Divergence (Gemini, Claude, GPT)**:
   - **Claude Opus 4.6 (Thinking)** achieved a perfect **8/8 (100.0%)** (avg 6.9s/task), resolving funnel precedence cleanly without generating Cartesian cross products.
   - **Gemini 3.8 Flash (Low Reasoning)** achieved a perfect **8/8 (100.0%)** as the fastest evaluated model (avg 4.6s/task, sub-5ms DuckDB execution).
   - **Gemini 3.8 Flash (Medium Reasoning)** scored a perfect **8/8 (100.0%)**, properly synthesizing CTE pre-aggregations, `NOT EXISTS` anti-joins, and single-scan conditional flags for funnel analysis.
   - **Claude Sonnet 4.6 (Thinking)** and **GPT-OSS 120B (Medium)** scored **7/8 (87.5%)**, failing Task 06 (Strict Funnel Precedence) due to multiple `COUNT(DISTINCT ...)` aggregations that DuckDB compiled into an internal `CROSS_PRODUCT`.
   - **Gemini 3.8 Flash (High Reasoning)** scored **6/8 (75.0%)**, suffering timeouts during extended deliberation on complex window frames.
   - **Comprehensive 120-Task Baseline**: The benchmark spans 120 tasks (10 core failure traps, 100 master analytical queries across 5 modern domains, and 10 hardened frontier trap challenges) with **100% (120/120) Ground Truth Verification**. Hardened stress-testing exposed distinct model cracks in GPT-OSS 120B (66.7% pass rate: circular CTE recursion syntax, array type binder errors, and unnormalized decay revenue over-allocation).
   - **Zero-LLM CI/CD Automation**: Complete automated testing runs via GitHub Actions without requiring external LLM API access.
3. **Execution Plan Anti-Patterns**: Without deep warehouse optimization constraints, frontier models frequently substitute linear window range frames with quadratic triangular self-joins (`ON b.ts BETWEEN a.ts - INTERVAL 6 DAYS AND a.ts`), causing query planners to fall back to $O(N^2)$ merge joins or Cartesian cross products.

---

### 3. Submission Artifacts Checklist

* **Code Repository & ZIP Archive**: Lightweight source package (`sql-frontier-eval-submission.zip`, <1 MB).
* **Automated 1-Step Verification**: Run `./verify.sh` to execute 12 unit tests, 100% golden baseline checks, and offline failure detection in under 5 seconds.
* **Live Model Benchmarks**: Integrates directly with frontier models across providers (`gemini-3.8-flash-high/medium/low`, `claude-opus-4-6-thinking`, `claude-sonnet-4-6`, `gpt-oss-120b-medium`) and OpenRouter.
* **Persistent Benchmark Results**: Timestamped JSON run artifacts stored in [`results/`](results/) and summarized in [`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md).
* **Video Walkthrough & Storyboard**:
  - Full 1080p Narrated Video Walkthrough with Burned-In Closed Captions: [`sql_frontier_eval_walkthrough.mp4`](sql_frontier_eval_walkthrough.mp4) (3m 53s, 6.92 MB, ready for YouTube, Google Drive, or Loom upload).
  - Synchronized Subtitle File: [`video/walkthrough_captions.srt`](video/walkthrough_captions.srt).
  - Timed Presentation Teleprompter Script: [`VIDEO_WALKTHROUGH_SCRIPT.md`](VIDEO_WALKTHROUGH_SCRIPT.md).
  - Interactive HTML Slide Deck: [`walkthrough_presentation.html`](walkthrough_presentation.html).
* **AI-Assisted Development Acknowledgement**: Transparently disclosed in documentation as developed in partnership with Google Antigravity (AGY) powered by Gemini 3.8 Flash.
