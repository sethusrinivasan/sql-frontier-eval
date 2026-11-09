#!/usr/bin/env python3
"""
Comprehensive 120-Task Evaluation Runner across Frontier LLMs.
Streams real-time progress, records latencies, verdicts, and persists timestamped scorecards.
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from tabulate import tabulate

MODELS = [
    "gemini-3.8-flash-low",
    "gpt-oss-120b-medium",
    "claude-sonnet-4-6",
    "claude-opus-4-6-thinking"
]

def main():
    print("=" * 80)
    print("SQL FRONTIER EVAL: COMPREHENSIVE 120-TASK FRONTIER MODEL BENCHMARK")
    print(f"Target Models: {', '.join(MODELS)}")
    print(f"Total Tasks per Model: 120 (Temporal, Vector, Search, Graph, Warehouse, Hardened Traps)")
    print(f"Started At: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    summary_rows = []

    for model in MODELS:
        print(f"\n" + "#" * 80)
        print(f"### RUNNING EVALUATION: agy/{model}")
        print(f"#" * 80)

        cmd = [
            sys.executable,
            "-u",
            "run_eval.py",
            f"--model=agy/{model}",
            "--tasks=tasks/*.json",
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
        passed_count = 0
        total_count = 120

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
            final_score,
            f"{elapsed:.1f}s",
            artifact_path
        ])

        print(f"\n✔ Completed agy/{model} in {elapsed:.1f}s (Exit Code: {proc.returncode})")

    print("\n" + "=" * 90)
    print("ALL 120-SUITE MODEL EVALUATIONS COMPLETED")
    print("=" * 90)
    print(tabulate(
        summary_rows,
        headers=["Model", "Final Score", "Total Elapsed", "Run Artifact"],
        tablefmt="grid"
    ))

if __name__ == "__main__":
    main()
