FROM postgres:latest

# Install latest pgvector and contrib extensions for PostgreSQL 18
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-18-pgvector \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*
