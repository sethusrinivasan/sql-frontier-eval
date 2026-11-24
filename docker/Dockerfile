FROM postgres:19

# Install latest pgvector and contrib extensions for PostgreSQL 19
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-19-pgvector \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*
