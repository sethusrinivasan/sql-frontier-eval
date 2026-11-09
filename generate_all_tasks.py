import json
import os
import duckdb

with open("catalog/analytical_queries_100.json") as f:
    queries = json.load(f)

print(f"Loaded {len(queries)} queries.")

tasks_dir = "tasks/expanded"
os.makedirs(tasks_dir, exist_ok=True)

con = duckdb.connect()
try:
    con.execute("INSTALL fts; LOAD fts;")
except Exception:
    pass

generated_count = 0
for idx, q in enumerate(queries, 1):
    task_id = f"task_{idx:03d}_{q['id']}"
    
    # Run query to get columns and verify
    test_con = duckdb.connect()
    try:
        test_con.execute("INSTALL fts; LOAD fts;")
    except Exception:
        pass
    test_con.execute(q["setup_sql"])
    df = test_con.execute(q["sql"]).df()
    expected_cols = list(df.columns)
    
    is_ordered = "order by" in q["sql"].lower()
    
    prompt = f"""{q['human_context']}

Execute the required analytical SQL calculation in DuckDB.
Expected output columns: {', '.join(expected_cols)}.
{'Results should be ordered as specified.' if is_ordered else 'Row order does not matter.'}"""

    task_obj = {
        "id": task_id,
        "name": q["title"],
        "category": q["domain"],
        "description": q["human_context"],
        "prompt": prompt,
        "setup_sql": q["setup_sql"].strip(),
        "golden_sql": q["sql"].strip(),
        "ordered": is_ordered,
        "expected_columns": expected_cols,
        "why_it_fails": q["hidden_trap"]
    }
    
    task_path = os.path.join(tasks_dir, f"{task_id}.json")
    with open(task_path, "w") as tf:
        json.dump(task_obj, tf, indent=2)
    generated_count += 1

print(f"Successfully generated {generated_count} task JSON files in {tasks_dir}/")
