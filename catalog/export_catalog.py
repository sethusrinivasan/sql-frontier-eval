import json
import os
import duckdb
from catalog.queries_temporal import TEMPORAL_QUERIES
from catalog.queries_vector import VECTOR_QUERIES
from catalog.queries_search import SEARCH_QUERIES
from catalog.queries_graph import GRAPH_QUERIES
from catalog.queries_warehouse import WAREHOUSE_QUERIES

ALL_QUERIES = TEMPORAL_QUERIES + VECTOR_QUERIES + SEARCH_QUERIES + GRAPH_QUERIES + WAREHOUSE_QUERIES
print(f"Total queries to export: {len(ALL_QUERIES)}")

os.makedirs("catalog/queries", exist_ok=True)

# 1. Export consolidated JSON
with open("catalog/analytical_queries_100.json", "w") as f:
    json.dump(ALL_QUERIES, f, indent=2)

# 2. Export individual annotated .sql files
for q in ALL_QUERIES:
    filename = f"catalog/queries/{q['id']}.sql"
    content = f"""/*
 ==============================================================================
 Query ID:         {q['id']}
 Title:            {q['title']}
 Domain:           {q['domain']}
 ------------------------------------------------------------------------------
 Human Context:
 {q['human_context']}

 The Hidden Trap:
 {q['hidden_trap']}

 The DuckDB Advantage:
 {q['duckdb_advantage']}
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
{q['setup_sql'].strip()}

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
{q['sql'].strip()}
"""
    with open(filename, "w") as f:
        f.write(content)

print(f"Exported {len(ALL_QUERIES)} queries to catalog/queries/ and catalog/analytical_queries_100.json")
