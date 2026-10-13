#!/usr/bin/env bash
set -e

# ==============================================================================
# SQL Frontier Eval - Quick Verification Script
# Runs unit tests, ground-truth sanity check, and offline naive query evaluation.
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
echo ">>> STEP 1: Running Unit Test Suite (Tests harness, sandboxing, and profiler)..."
"${PYTEST}" tests/ -v

# Step 2: Golden Ground-Truth Sanity Test
echo ""
echo ">>> STEP 2: Verifying Golden Baseline (Ensures zero false negatives on ground truth)..."
"${PYTHON}" run_eval.py --test-gold

# Step 3: Offline Model Evaluation (Catches naive join fan-out)
echo ""
echo ">>> STEP 3: Running Offline Evaluation (Testing reference failure modes)..."
"${PYTHON}" run_eval.py --model offline --verbose

echo ""
echo "================================================================================"
echo "✔ ALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY"
echo "================================================================================"
