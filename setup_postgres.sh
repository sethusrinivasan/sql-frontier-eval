#!/usr/bin/env bash
set -e

# ==============================================================================
# SQL Frontier Eval - PostgreSQL Docker Compose Setup Script
# Builds and launches the latest PostgreSQL 18 container with pgvector, pg_trgm,
# fuzzystrmatch, btree_gist, and analytical compatibility extensions.
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

echo "================================================================================"
echo "SQL FRONTIER EVAL: POSTGRESQL 18 DOCKER COMPOSE INITIALIZATION"
echo "================================================================================"

# Verify Docker and Docker Compose availability
if ! command -v docker &> /dev/null; then
    echo "[ERROR] 'docker' binary not found. Please install Docker."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "[ERROR] 'docker compose' is not available."
    exit 1
fi

echo ">>> Building and starting PostgreSQL 18 container..."
docker compose up -d --build

echo ">>> Waiting for PostgreSQL service to become healthy..."
RETRIES=30
until docker compose ps postgres | grep -q "healthy" || [ $RETRIES -eq 0 ]; do
    echo "    Waiting for postgres container healthcheck... ($RETRIES left)"
    sleep 2
    RETRIES=$((RETRIES - 1))
done

if [ $RETRIES -eq 0 ]; then
    echo "[WARNING] Healthcheck timed out. Inspecting container logs:"
    docker compose logs postgres
    exit 1
fi

echo ">>> Verifying PostgreSQL extensions..."
docker compose exec postgres psql -U postgres -d sql_frontier_eval -c "
SELECT extname, extversion FROM pg_extension ORDER BY extname;
"

echo ""
echo "================================================================================"
echo "✔ PostgreSQL 18.7 instance is healthy and ready for benchmark evaluations!"
echo "Connection String: postgresql://postgres:postgrespassword@localhost:5432/sql_frontier_eval"
echo "================================================================================"
