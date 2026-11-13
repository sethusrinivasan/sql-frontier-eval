#!/usr/bin/env python3
"""
Comprehensive 120-Task Evaluation Runner across All Frontier LLMs in Antigravity Context.
Supports both DuckDB (In-Memory Columnar OLAP) and PostgreSQL 18+ (Relational, Vector & FTS).
Streams real-time progress, records latencies, verdicts, and persists timestamped scorecards.
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from tabulate import tabulate

MODELS = [
    "claude-opus-4-6-thinking",
    "gemini-3.8-flash-medium",
    "gemini-3.8-flash-low",
    "claude-sonnet-4-6",
    "gpt-oss-120b-medium",
    "gemini-3.8-flash-high"
]

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-Model 120-Task Frontier Benchmark Runner")
    parser.add_argument(
        "--engine",
        type=str,
        default="duckdb",
        choices=["duckdb", "postgres"],
        help="Database engine to evaluate: 'duckdb' (default) or 'postgres'"
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="tasks/*.json",
        help="Glob pattern matching tasks to evaluate (default: tasks/*.json)"
    )
    parser.add_argument(
        "--models",
        type=str,
        default=None,
        help="Comma-separated subset of models to run (e.g. 'gemini-3.8-flash-low,claude-sonnet-4-6')"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    selected_models = [m.strip() for m in args.models.split(",")] if args.models else MODELS

    print("=" * 80)
    print("SQL FRONTIER EVAL: COMPREHENSIVE 120-TASK FRONTIER MODEL BENCHMARK")
    print(f"Target Database Engine: {args.engine.upper()} ({'DuckDB 2.0 In-Memory' if args.engine == 'duckdb' else 'PostgreSQL 18+ via Docker Compose'})")
    print(f"Target Models ({len(selected_models)}): {', '.join(selected_models)}")
    print(f"Task Pattern: {args.tasks}")
    print(f"Started At: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    summary_rows = []

    for model in selected_models:
        print(f"\n" + "#" * 80)
        print(f"### RUNNING EVALUATION: agy/{model} on {args.engine.upper()}")
        print(f"#" * 80)

        cmd = [
            sys.executable,
            "-u",
            "run_eval.py",
            f"--model=agy/{model}",
            f"--engine={args.engine}",
            f"--tasks={args.tasks}",
            "--save-results"
        ]

        t0 = time.time()
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        final_score = "N/A"
        artifact_path = "N/A"

        for line in iter(proc.stdout.readline, ""):
            line_str = line.rstrip()
            if not line_str:
                continue

            # Stream task announcements and verdicts
            if line_str.startswith("[Task]") or "Verdict:" in line_str or "Generation finished" in line_str:
                print("  " + line_str)
                sys.stdout.flush()

            if "Final Score:" in line_str:
                final_score = line_str.replace("Final Score:", "").strip()
                print("\n  >>> " + line_str)
            if "Saved run artifact to" in line_str:
                artifact_path = line_str.replace("[Results Persisted] Saved run artifact to", "").strip()
                print("  >>> " + line_str)

        proc.stdout.close()
        proc.wait()
        elapsed = time.time() - t0

        summary_rows.append([
            f"agy/{model}",
            args.engine.upper(),
            final_score,
            f"{elapsed:.1f}s",
            artifact_path
        ])

        print(f"\n✔ Completed agy/{model} on {args.engine.upper()} in {elapsed:.1f}s (Exit Code: {proc.returncode})")

    print("\n" + "=" * 90)
    print(f"ALL 120-SUITE MODEL EVALUATIONS COMPLETED ({args.engine.upper()})")
    print("=" * 90)
    print(tabulate(
        summary_rows,
        headers=["Model", "Engine", "Final Score", "Total Elapsed", "Run Artifact"],
        tablefmt="grid"
    ))

if __name__ == "__main__":
    main()
