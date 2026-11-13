#!/usr/bin/env bash
set -e

# ==============================================================================
# SQL Frontier Eval - Quick Verification Script
# Runs unit tests, ground-truth sanity check across DuckDB and PostgreSQL,
# and offline naive query evaluation.
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

# Resolve python and pytest binaries (prefer local .venv if present)
if [ -d ".venv/bin" ]; then
    PYTHON=".venv/bin/python"
    PYTEST=".venv/bin/pytest"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
    PYTEST="pytest"
else
    echo "[ERROR] Python interpreter not found."
    exit 1
fi

echo "================================================================================"
echo "SQL FRONTIER EVAL: VERIFICATION SUITE"
echo "Environment: ${PYTHON}"
echo "================================================================================"

# Step 1: Unit Tests
echo ""
echo ">>> STEP 1: Running Unit Test Suite (Tests harness, DuckDB & Postgres sandboxing, and profiler)..."
"${PYTEST}" tests/ -v

# Step 2: DuckDB Golden Ground-Truth Sanity Test
echo ""
echo ">>> STEP 2: Verifying DuckDB Golden Baseline (Ensures zero false negatives on ground truth)..."
"${PYTHON}" run_eval.py --engine=duckdb --test-gold --tasks="tasks/task_001*.json"

# Step 3: PostgreSQL Golden Ground-Truth Sanity Test
echo ""
echo ">>> STEP 3: Verifying PostgreSQL 18+ Golden Baseline..."
if docker compose ps postgres | grep -q "Up"; then
    "${PYTHON}" run_eval.py --engine=postgres --test-gold --tasks="tasks/task_026*.json"
else
    echo "    [NOTE] PostgreSQL container not running; run ./setup_postgres.sh to launch."
fi

# Step 4: Offline Model Evaluation (Catches naive join fan-out)
echo ""
echo ">>> STEP 4: Running Offline Evaluation (Testing reference failure modes)..."
"${PYTHON}" run_eval.py --model offline --tasks="tasks/task_001*.json"

echo ""
echo "================================================================================"
echo "✔ ALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY"
echo "================================================================================"
