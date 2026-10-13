import argparse
import glob
import json
import os
import sys
import textwrap
import time
from datetime import datetime, timezone
from tabulate import tabulate
from typing import Dict, Any, List, Optional
import pandas as pd
import sqlparse

from harness.engine import SQLEvalEngine
from harness.grader import SQLGrader
from harness.llm import OpenRouterClient

def beautify_sql(query: str) -> str:
    """
    Formats and beautifies SQL queries with uppercase keywords and clean indentation.
    """
    if not query or not query.strip():
        return "<No query provided>"
    try:
        return sqlparse.format(
            query.strip(),
            reindent=True,
            keyword_case="upper",
            identifier_case="lower"
        )
    except Exception:
        return query.strip()

def render_tabular_df(df: Optional[pd.DataFrame], max_rows: int = 15) -> str:
    """
    Renders a pandas DataFrame as a human-readable ASCII table.
    """
    if df is None:
        return "  [No Data Returned / Execution Failed]"
    if df.empty:
        return "  [Empty Result Set: 0 rows]"

    display_df = df.head(max_rows)
    table_str = tabulate(display_df, headers="keys", tablefmt="grid", showindex=True)
    lines = ["  " + line for line in table_str.splitlines()]
    result = "\n".join(lines)
    if len(df) > max_rows:
        result += f"\n  ... (showing first {max_rows} of {len(df)} total rows)"
    return result

def print_failure_walkthrough(
    task: Dict[str, Any],
    candidate_sql: str,
    golden_sql: str,
    cand_df: Optional[pd.DataFrame],
    golden_df: Optional[pd.DataFrame],
    grade_result: Dict[str, Any],
    cand_time_ms: float,
    gold_time_ms: float
):
    """
    Prints an in-depth, human-readable walkthrough when an eval task fails:
    1. Beautified queries (Candidate vs Golden)
    2. Tabular results comparison (Actual vs Expected)
    3. Failure analysis with exact cell divergence and domain explanation.
    """
    task_id = task.get("id", "unknown")
    task_name = task.get("name", task_id)
    category = task.get("category", "General")
    verdict = grade_result.get("verdict", "FAILED")
    reason = grade_result.get("reason", "Unknown failure")
    diagnostics = grade_result.get("diagnostics", {})

    print("\n" + "=" * 90)
    print(f"❌ EVALUATION FAILURE WALKTHROUGH: {task_name} ({task_id})")
    print(f"Category: {category}")
    print(f"Verdict:  {verdict}")
    print("=" * 90)

    # 1. Beautified Queries
    print("\n" + "-" * 90)
    print("1. QUERIES EXECUTED")
    print("-" * 90)
    print(f"[Candidate Query (Tested - Latency: {cand_time_ms:.1f}ms)]")
    cand_formatted = beautify_sql(candidate_sql)
    for line in cand_formatted.splitlines():
        print(f"  {line}")

    print(f"\n[Golden Reference Query (Ground Truth - Latency: {gold_time_ms:.1f}ms)]")
    gold_formatted = beautify_sql(golden_sql)
    for line in gold_formatted.splitlines():
        print(f"  {line}")

    # 2. Tabular Query Results Comparison
    print("\n" + "-" * 90)
    print("2. TABULAR QUERY RESULTS COMPARISON")
    print("-" * 90)

    cand_shape_str = f"({cand_df.shape[0]} rows x {cand_df.shape[1]} columns)" if cand_df is not None else "(No DataFrame)"
    gold_shape_str = f"({golden_df.shape[0]} rows x {golden_df.shape[1]} columns)" if golden_df is not None else "(No DataFrame)"

    print(f"[Actual Candidate Output] {cand_shape_str}:")
    print(render_tabular_df(cand_df))

    print(f"\n[Expected Golden Output] {gold_shape_str}:")
    print(render_tabular_df(golden_df))

    # 3. Why Comparison Failed & Root Cause
    print("\n" + "-" * 90)
    print("3. FAILURE ANALYSIS & ROOT CAUSE")
    print("-" * 90)
    print(f"• Verdict Reason: {reason}")

    # Specific diagnostic breakdown
    if verdict == "VALUE_MISMATCH" and "column" in diagnostics:
        col = diagnostics.get("column")
        row_idx = diagnostics.get("row_index")
        expected = diagnostics.get("expected")
        actual = diagnostics.get("actual")
        diff = diagnostics.get("difference")
        print(f"• Value Discrepancy Breakdown:")
        print(f"  - Diverged Column:  '{col}' at Row index {row_idx}")
        print(f"  - Expected Ground:   {expected}")
        print(f"  - Actual Returned:   {actual}")
        if diff is not None and isinstance(expected, (int, float)) and expected != 0:
            mult = actual / expected
            print(f"  - Arithmetic Delta:  {diff:+.2f} ({mult:.1f}x inflation / skew)")

    elif verdict == "SHAPE_MISMATCH":
        exp_s = diagnostics.get("expected_shape")
        act_s = diagnostics.get("actual_shape")
        print(f"• Shape Discrepancy: Expected shape {exp_s}, but candidate produced {act_s}.")
        if act_s and exp_s and act_s[0] > exp_s[0]:
            print(f"  - Row count inflation: {act_s[0]} rows vs {exp_s[0]} rows (likely Cartesian explosion or fan-out).")

    elif verdict == "COLUMN_MISMATCH":
        missing = diagnostics.get("missing_columns", [])
        unexpected = diagnostics.get("unexpected_columns", [])
        if missing:
            print(f"• Missing Expected Columns:   {missing}")
        if unexpected:
            print(f"• Unexpected Returned Columns: {unexpected}")

    elif verdict == "EFFICIENCY_VIOLATION":
        anti_patterns = diagnostics.get("anti_patterns", [])
        for ap in anti_patterns:
            print(f"• Anti-Pattern Detected: {ap}")

    elif verdict == "SYNTAX_OR_EXECUTION_ERROR":
        err_msg = diagnostics.get("error", reason)
        print(f"• Syntax / Engine Error: {err_msg}")

    # Domain explanation from task definition if present
    why_it_fails = task.get("why_it_fails") or task.get("description")
    if why_it_fails:
        print(f"\n• Analytical Explanation (Why Frontier Models Fail):")
        for line in textwrap.wrap(why_it_fails, width=86):
            print(f"  {line}")

    print("=" * 90 + "\n")

def parse_args():
    parser = argparse.ArgumentParser(description="SQL Frontier Eval Harness for Analytical Queries")
    parser.add_argument(
        "--model",
        type=str,
        default="offline",
        help="OpenRouter model identifier (e.g. 'anthropic/claude-3.5-sonnet', 'openai/gpt-4o', 'google/gemini-2.0-flash-001') or 'offline'"
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="tasks/*.json",
        help="Glob pattern or path to task definitions (default: 'tasks/*.json')"
    )
    parser.add_argument(
        "--test-gold",
        action="store_true",
        help="Run evaluation against the golden query itself to ensure zero false failures"
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        default=True,
        help="Persist structured results to results/ directory (default: True)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose execution details, plans, and diff diagnostics"
    )
    return parser.parse_args()

def run_evaluation(args) -> Dict[str, Any]:
    engine = SQLEvalEngine()
    task_files = sorted(glob.glob(args.tasks))

    if not task_files:
        print(f"[ERROR] No task files found matching pattern: {args.tasks}")
        sys.exit(1)

    # Initialize OpenRouter client if not in offline mode
    llm_client = None
    if args.model != "offline" and not args.test_gold:
        llm_client = OpenRouterClient()
        if not llm_client.api_key:
            print("[WARNING] OPENROUTER_API_KEY environment variable is not set. Switching to offline mode.")
            args.model = "offline"

    print("=" * 80)
    print(f"SQL FRONTIER EVALUATION RUNNER")
    print(f"Target Model: {args.model} {'(TESTING GOLDEN BASELINE)' if args.test_gold else ''}")
    print(f"Tasks Discovered: {len(task_files)}")
    print(f"Execution Engine: DuckDB in-memory (threads=4)")
    print("=" * 80)

    task_results = []
    table_rows = []

    for task_path in task_files:
        with open(task_path, "r") as f:
            task = json.load(f)

        task_id = task.get("id", os.path.basename(task_path))
        task_name = task.get("name", task_id)
        category = task.get("category", "General")
        ordered = task.get("ordered", False)
        disallowed_ops = task.get("efficiency_rules", {}).get("disallowed_operators", ["CROSS_PRODUCT", "BLOCKWISE_NL_JOIN"])

        print(f"\n[Task] {task_name} ({task_id})")
        print(f"  Category: {category}")

        # 1. Fresh sandbox & load fixture
        engine.reset_sandbox()
        setup_err = engine.load_seed_data(task["setup_sql"])
        if setup_err:
            print(f"  [ERROR] Setup SQL failed: {setup_err}")
            continue

        # 2. Run golden query for ground truth
        golden_df, gold_err, gold_time_ms = engine.execute_query(task["golden_sql"])
        if gold_err:
            print(f"  [ERROR] Golden Query failed: {gold_err}")
            continue

        # 3. Determine Candidate SQL
        candidate_sql = ""
        cand_exec_err = None
        llm_meta = {}

        if args.test_gold:
            candidate_sql = task["golden_sql"]
            print("  Candidate: Golden query (sanity verification)")
        elif args.model == "offline":
            candidate_sql = task.get("naive_llm_sql", task["golden_sql"])
            print("  Candidate: Local naive/reference query (offline mode)")
        else:
            print(f"  Generating SQL via OpenRouter ({args.model})...")
            gen_sql, gen_err, llm_meta = llm_client.generate_sql(
                task_prompt=task["prompt"],
                setup_sql=task["setup_sql"],
                model=args.model
            )
            if gen_err:
                print(f"  [ERROR] Generation failed: {gen_err}")
                candidate_sql = ""
                cand_exec_err = gen_err
            else:
                candidate_sql = gen_sql
                print(f"  Generation finished in {llm_meta.get('latency_ms', 0):.1f}ms ({llm_meta.get('total_tokens', 0)} tokens)")

        # 4. Execute Candidate Query
        cand_df = None
        cand_err = cand_exec_err
        cand_time_ms = 0.0
        cand_profile = None

        if candidate_sql and not cand_exec_err:
            cand_df, cand_err, cand_time_ms = engine.execute_query(candidate_sql)
            if cand_df is not None:
                cand_profile, _ = engine.profile_query(candidate_sql)

        # 5. Grade Candidate Output
        grade_result = SQLGrader.grade(
            candidate_df=cand_df,
            golden_df=golden_df,
            profile_tree=cand_profile,
            ordered=ordered,
            disallowed_ops=disallowed_ops,
            exec_error=cand_err
        )

        status = "PASSED" if grade_result["passed"] else "FAILED"
        verdict = grade_result["verdict"]
        reason = grade_result["reason"]

        print(f"  Verdict: {status} ({verdict})")

        # 6. Detailed Walkthrough on Failure
        if not grade_result["passed"]:
            print_failure_walkthrough(
                task=task,
                candidate_sql=candidate_sql,
                golden_sql=task["golden_sql"],
                cand_df=cand_df,
                golden_df=golden_df,
                grade_result=grade_result,
                cand_time_ms=cand_time_ms,
                gold_time_ms=gold_time_ms
            )

        table_rows.append([
            task_id,
            category,
            verdict,
            f"{cand_time_ms:.1f}ms",
            reason[:60] + ("..." if len(reason) > 60 else "")
        ])

        task_results.append({
            "task_id": task_id,
            "name": task_name,
            "category": category,
            "verdict": verdict,
            "passed": grade_result["passed"],
            "reason": reason,
            "candidate_sql": candidate_sql,
            "golden_sql": task["golden_sql"],
            "execution_time_ms": cand_time_ms,
            "golden_time_ms": gold_time_ms,
            "diagnostics": grade_result.get("diagnostics", {}),
            "llm_metadata": llm_meta
        })

    # Summary Display
    print("\n" + "=" * 90)
    print("EVAL HARNESS SUMMARY REPORT")
    print("=" * 90)
    print(tabulate(
        table_rows,
        headers=["Task ID", "Category", "Verdict", "Latency", "Notes"],
        tablefmt="grid"
    ))

    total = len(task_results)
    passed_count = sum(1 for r in task_results if r["passed"])
    pass_rate = (passed_count / total * 100) if total > 0 else 0.0

    print(f"\nFinal Score: {passed_count}/{total} Passed ({pass_rate:.1f}%)")

    # Persist Results Artifact
    run_summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "is_golden_test": args.test_gold,
        "total_tasks": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate_pct": pass_rate,
        "tasks": task_results
    }

    if args.save_results:
        os.makedirs("results", exist_ok=True)
        safe_model = args.model.replace("/", "_").replace(":", "_")
        filename = f"results/eval_run_{safe_model}_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(run_summary, f, indent=2)
        print(f"[Results Persisted] Saved run artifact to {filename}")

    return run_summary

if __name__ == "__main__":
    cli_args = parse_args()
    run_evaluation(cli_args)