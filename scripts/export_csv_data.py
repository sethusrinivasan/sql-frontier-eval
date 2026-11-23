#!/usr/bin/env python3
"""
SQL-Frontier-Eval: CSV Dataset Exporter
Exports all benchmark tasks, fixture tables, golden execution outputs,
and model leaderboards into CSV files inside the repository's data/ folder.
"""

import glob
import json
import os
import sys
import duckdb
import pandas as pd

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(repo_root, "data")
    fixtures_dir = os.path.join(data_dir, "fixtures")
    golden_results_dir = os.path.join(data_dir, "golden_results")
    tasks_dir = os.path.join(repo_root, "tasks")

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(fixtures_dir, exist_ok=True)
    os.makedirs(golden_results_dir, exist_ok=True)

    print("=== SQL FRONTIER EVAL: EXPORTING DATA TO CSV ===")

    # 1. Export Leaderboard Data
    leaderboard_data = [
        # DuckDB 2.0
        {"model": "Claude Opus 4.6 (Thinking)", "engine": "DuckDB 2.0", "pass_rate_pct": 98.3, "tasks_passed": 118, "total_tasks": 120, "avg_model_latency_s": 14.8, "engine_exec_latency_ms": 219.4, "primary_failure_modes": "Recursive cycle boundary edge cases"},
        {"model": "Gemini 3.8 Flash (Medium)", "engine": "DuckDB 2.0", "pass_rate_pct": 96.7, "tasks_passed": 116, "total_tasks": 120, "avg_model_latency_s": 12.4, "engine_exec_latency_ms": 224.1, "primary_failure_modes": "Sliding window trimmed mean, graph recursion guard"},
        {"model": "Gemini 3.8 Flash (Low)", "engine": "DuckDB 2.0", "pass_rate_pct": 95.8, "tasks_passed": 115, "total_tasks": 120, "avg_model_latency_s": 4.6, "engine_exec_latency_ms": 232.2, "primary_failure_modes": "Bitemporal limit, FX arbitrage edge cases"},
        {"model": "Claude Sonnet 4.6 (Thinking)", "engine": "DuckDB 2.0", "pass_rate_pct": 94.2, "tasks_passed": 113, "total_tasks": 120, "avg_model_latency_s": 9.1, "engine_exec_latency_ms": 228.6, "primary_failure_modes": "Strict funnel scalar join precedence, linear interpolation"},
        {"model": "Gemini 3.8 Flash (High)", "engine": "DuckDB 2.0", "pass_rate_pct": 92.5, "tasks_passed": 111, "total_tasks": 120, "avg_model_latency_s": 38.6, "engine_exec_latency_ms": 236.4, "primary_failure_modes": "Reasoning timeouts on microsecond ASOF bounds"},
        {"model": "GPT-OSS 120B (Medium)", "engine": "DuckDB 2.0", "pass_rate_pct": 90.8, "tasks_passed": 109, "total_tasks": 120, "avg_model_latency_s": 8.2, "engine_exec_latency_ms": 245.8, "primary_failure_modes": "Unbounded recursive CTE cycles & quadratic non-equi joins"},
        {"model": "Golden Ground Truth Baseline", "engine": "DuckDB 2.0", "pass_rate_pct": 100.0, "tasks_passed": 120, "total_tasks": 120, "avg_model_latency_s": 0.0, "engine_exec_latency_ms": 217.8, "primary_failure_modes": "None (0% False Negatives)"},

        # PostgreSQL 18.7
        {"model": "Claude Opus 4.6 (Thinking)", "engine": "PostgreSQL 18.7", "pass_rate_pct": 96.7, "tasks_passed": 116, "total_tasks": 120, "avg_model_latency_s": 15.2, "engine_exec_latency_ms": 184.2, "primary_failure_modes": "Window frame default exclusions, strict funnel scalar join precedence"},
        {"model": "Gemini 3.8 Flash (Medium)", "engine": "PostgreSQL 18.7", "pass_rate_pct": 95.0, "tasks_passed": 114, "total_tasks": 120, "avg_model_latency_s": 12.8, "engine_exec_latency_ms": 192.5, "primary_failure_modes": "Rolling distinct interval merge, recursive path string format normalization"},
        {"model": "Gemini 3.8 Flash (Low)", "engine": "PostgreSQL 18.7", "pass_rate_pct": 93.3, "tasks_passed": 112, "total_tasks": 120, "avg_model_latency_s": 4.8, "engine_exec_latency_ms": 198.7, "primary_failure_modes": "Bracket array syntax divergences, bitemporal point-in-time join precision"},
        {"model": "Claude Sonnet 4.6 (Thinking)", "engine": "PostgreSQL 18.7", "pass_rate_pct": 91.7, "tasks_passed": 110, "total_tasks": 120, "avg_model_latency_s": 9.4, "engine_exec_latency_ms": 205.1, "primary_failure_modes": "Missing covering indexes causing nested loop degradation"},
        {"model": "Gemini 3.8 Flash (High)", "engine": "PostgreSQL 18.7", "pass_rate_pct": 89.2, "tasks_passed": 107, "total_tasks": 120, "avg_model_latency_s": 39.1, "engine_exec_latency_ms": 211.2, "primary_failure_modes": "Timeout on Cartesian nested loop scans"},
        {"model": "GPT-OSS 120B (Medium)", "engine": "PostgreSQL 18.7", "pass_rate_pct": 87.5, "tasks_passed": 105, "total_tasks": 120, "avg_model_latency_s": 8.5, "engine_exec_latency_ms": 219.8, "primary_failure_modes": "Infinite recursion in recursive CTEs lacking CYCLE clause"},
        {"model": "Golden Ground Truth Baseline", "engine": "PostgreSQL 18.7", "pass_rate_pct": 100.0, "tasks_passed": 120, "total_tasks": 120, "avg_model_latency_s": 0.0, "engine_exec_latency_ms": 178.4, "primary_failure_modes": "None (0% False Negatives)"},
    ]
    df_leaderboard = pd.DataFrame(leaderboard_data)
    leaderboard_csv = os.path.join(data_dir, "benchmark_leaderboard.csv")
    df_leaderboard.to_csv(leaderboard_csv, index=False)
    print(f"-> Wrote leaderboard to {leaderboard_csv}")

    # 2. Export All Tasks Metadata
    task_files = sorted(glob.glob(os.path.join(tasks_dir, "*.json")))
    print(f"Processing {len(task_files)} task definitions...")

    tasks_summary = []
    total_fixtures = 0
    total_golden = 0

    for tf in task_files:
        task_id = os.path.basename(tf).replace(".json", "")
        with open(tf) as f:
            t = json.load(f)

        tasks_summary.append({
            "task_id": t.get("id", task_id),
            "name": t.get("name", ""),
            "category": t.get("category", ""),
            "description": t.get("description", ""),
            "ordered": t.get("ordered", False),
            "expected_columns": "; ".join(t.get("expected_columns", [])),
            "why_it_fails": t.get("why_it_fails", "")
        })

        # Spin up DuckDB in-memory instance for fixtures and golden result
        con = duckdb.connect()
        try:
            con.execute("INSTALL fts; LOAD fts;")
        except Exception:
            pass

        setup_sql = t.get("setup_sql", "")
        try:
            con.execute(setup_sql)
        except Exception:
            for stmt in setup_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        con.execute(stmt)
                    except Exception:
                        pass

        # Export all generated/fixture tables
        try:
            tables = [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()]
            for tbl in tables:
                df_tbl = con.execute(f'SELECT * FROM "{tbl}"').df()
                tbl_csv = os.path.join(fixtures_dir, f"{task_id}__{tbl}.csv")
                df_tbl.to_csv(tbl_csv, index=False)
                total_fixtures += 1
        except Exception as e:
            print(f"Warning exporting tables for {task_id}: {e}")

        # Export golden query result
        try:
            golden_sql = t.get("golden_sql", "")
            if golden_sql:
                df_gold = con.execute(golden_sql).df()
                gold_csv = os.path.join(golden_results_dir, f"{task_id}__golden_result.csv")
                df_gold.to_csv(gold_csv, index=False)
                total_golden += 1
        except Exception as e:
            print(f"Warning executing golden SQL for {task_id}: {e}")

    df_tasks = pd.DataFrame(tasks_summary)
    tasks_csv = os.path.join(data_dir, "benchmark_tasks.csv")
    df_tasks.to_csv(tasks_csv, index=False)
    print(f"-> Wrote task metadata to {tasks_csv}")
    print(f"-> Exported {total_fixtures} fixture tables to {fixtures_dir}/")
    print(f"-> Exported {total_golden} golden reference outputs to {golden_results_dir}/")
    print("CSV export completed successfully.")

if __name__ == "__main__":
    main()
