import json
import os
import sys
import time
import duckdb
import pandas as pd
from harness.grader import SQLGrader
from harness.llm import AgyClient

# Select 5 representative flagship tasks from the 5 expanded domains
SAMPLE_IDS = [
    "Q01_asof_trade_quote_matching",          # Domain 1: Temporal ASOF JOIN
    "Q26_cosine_similarity_top_k",            # Domain 2: Vector Cosine Similarity
    "Q52_reciprocal_rank_fusion_rrf",         # Domain 3: RRF Hybrid Retrieval
    "Q76_bill_of_materials_recursive_rollup", # Domain 4: Graph BOM Recursive CTE
    "Q94_median_absolute_deviation_mad"       # Domain 5: Warehouse MAD Outlier Detection
]

with open("catalog/analytical_queries_100.json") as f:
    catalog = json.load(f)

selected_tasks = [q for q in catalog if q["id"] in SAMPLE_IDS]
print(f"Loaded {len(selected_tasks)} flagship expanded tasks for frontier model evaluation.")

def run_sample_eval_for_model(model_name: str):
    print(f"\n=======================================================")
    print(f"EVALUATING MODEL: {model_name} on Expanded Frontier Patterns")
    print(f"=======================================================")
    client = AgyClient()
    grader = SQLGrader()
    
    passed = 0
    total = len(selected_tasks)
    
    for task in selected_tasks:
        print(f"\n[Task] {task['title']} ({task['id']})")
        print(f"  Domain: {task['domain']}")
        
        # Golden execution
        con = duckdb.connect()
        try:
            con.execute("INSTALL fts; LOAD fts;")
        except Exception:
            pass
        con.execute(task["setup_sql"])
        gold_df = con.execute(task["sql"]).df()
        
        # Prompt model
        prompt = f"""Solve this analytical SQL task for DuckDB:
{task['human_context']}

Setup SQL:
{task['setup_sql']}

Write a single valid DuckDB SQL query that solves this requirement."""
        
        sql, err, meta = client.generate_sql(prompt, task["setup_sql"], model=model_name)
        if err or not sql:
            print(f"  ❌ Generation Error: {err}")
            continue
            
        # Execute model SQL
        cand_con = duckdb.connect()
        try:
            cand_con.execute("INSTALL fts; LOAD fts;")
        except Exception:
            pass
        cand_con.execute(task["setup_sql"])
        try:
            cand_df = cand_con.execute(sql).df()
            grade = grader.compare_dataframes(cand_df, gold_df, ordered=False)
            if grade["verdict"] == "PASS":
                print(f"  ✅ VERDICT: PASSED ({meta.get('latency_ms', 0):.1f}ms)")
                passed += 1
            else:
                print(f"  ❌ VERDICT: FAILED - {grade.get('reason')}")
        except Exception as e:
            print(f"  ❌ Execution Error: {e}")
            
    print(f"\nScore for {model_name}: {passed}/{total} Passed ({passed/total*100:.1f}%)")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.8-flash-low"
    run_sample_eval_for_model(target)
