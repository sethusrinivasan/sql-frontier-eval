import pytest
import pandas as pd
from decimal import Decimal
from harness.engine import SQLEvalEngine
from harness.grader import SQLGrader

def test_engine_isolation():
    engine = SQLEvalEngine()
    engine.load_seed_data("CREATE TABLE t1 (id INT, val VARCHAR); INSERT INTO t1 VALUES (1, 'test');")
    df1, err1, _ = engine.execute_query("SELECT * FROM t1;")
    assert err1 is None
    assert len(df1) == 1

    # Reset sandbox should erase t1
    engine.reset_sandbox()
    df2, err2, _ = engine.execute_query("SELECT * FROM t1;")
    assert err2 is not None
    assert "t1 does not exist" in err2 or "Table with name t1 does not exist" in err2

def test_engine_profiling_and_operators():
    engine = SQLEvalEngine()
    engine.load_seed_data("CREATE TABLE items AS SELECT range AS id FROM range(20);")
    profile, err = engine.profile_query("SELECT count(*) FROM items;")
    assert err is None
    assert profile is not None

    operators = engine.extract_operators(profile)
    op_types = [op["type"] for op in operators]
    assert "TABLE_SCAN" in op_types or "PERFECT_HASH_GROUP_BY" in op_types or "PROJECTION" in op_types

def test_engine_detect_cross_product():
    engine = SQLEvalEngine()
    engine.load_seed_data("""
        CREATE TABLE a AS SELECT range AS x FROM range(5);
        CREATE TABLE b AS SELECT range AS y FROM range(5);
    """)
    profile, err = engine.profile_query("SELECT * FROM a CROSS JOIN b;")
    assert err is None
    anti_patterns = engine.detect_anti_patterns(profile)
    assert any("CROSS_PRODUCT" in p for p in anti_patterns)

def test_grader_unordered_row_matching():
    # Candidate returned rows in different order, but ordered=False
    gold_df = pd.DataFrame({"id": [1, 2, 3], "val": ["apple", "banana", "cherry"]})
    cand_df = pd.DataFrame({"id": [3, 1, 2], "val": ["cherry", "apple", "banana"]})

    res = SQLGrader.grade(candidate_df=cand_df, golden_df=gold_df, ordered=False)
    assert res["passed"] is True
    assert res["verdict"] == "PASS"

def test_grader_ordered_row_enforcement():
    gold_df = pd.DataFrame({"id": [1, 2, 3], "val": ["apple", "banana", "cherry"]})
    cand_df = pd.DataFrame({"id": [3, 1, 2], "val": ["cherry", "apple", "banana"]})

    res = SQLGrader.grade(candidate_df=cand_df, golden_df=gold_df, ordered=True)
    assert res["passed"] is False
    assert res["verdict"] == "VALUE_MISMATCH"

def test_grader_decimal_vs_float_tolerance():
    gold_df = pd.DataFrame({"total": [Decimal("100.00"), Decimal("250.50")]})
    cand_df = pd.DataFrame({"total": [100.0001, 250.4999]})

    res = SQLGrader.grade(candidate_df=cand_df, golden_df=gold_df, ordered=False)
    assert res["passed"] is True
    assert res["verdict"] == "PASS"

def test_grader_column_mismatch_diagnostics():
    gold_df = pd.DataFrame({"merchant_id": [1], "total_gross_sales": [100.0]})
    cand_df = pd.DataFrame({"merchant_id": [1], "gross_sales": [100.0]})

    res = SQLGrader.grade(candidate_df=cand_df, golden_df=gold_df)
    assert res["passed"] is False
    assert res["verdict"] == "COLUMN_MISMATCH"
    assert "missing_columns" in res["diagnostics"]
    assert "total_gross_sales" in res["diagnostics"]["missing_columns"]

def test_grader_first_mismatch_diff():
    gold_df = pd.DataFrame({"merchant_id": [1], "total_gross_sales": [100.0]})
    cand_df = pd.DataFrame({"merchant_id": [1], "total_gross_sales": [400.0]})

    res = SQLGrader.grade(candidate_df=cand_df, golden_df=gold_df)
    assert res["passed"] is False
    assert res["verdict"] == "VALUE_MISMATCH"
    diff = res["diagnostics"]
    assert diff["column"] == "total_gross_sales"
    assert diff["expected"] == 100.0
    assert diff["actual"] == 400.0
    assert diff["difference"] == 300.0


def test_postgres_engine_isolation_and_execution():
    try:
        engine = SQLEvalEngine(engine_type="postgres")
    except Exception as e:
        pytest.skip(f"PostgreSQL container not reachable: {e}")

    engine.load_seed_data("CREATE TABLE pg_t1 (id INT, val VARCHAR); INSERT INTO pg_t1 VALUES (1, 'pg_test');")
    df1, err1, _ = engine.execute_query("SELECT * FROM pg_t1;")
    assert err1 is None
    assert len(df1) == 1
    assert df1.iloc[0]["val"] == "pg_test"

    # Reset sandbox should cleanly drop eval_sandbox schema
    engine.reset_sandbox()
    df2, err2, _ = engine.execute_query("SELECT * FROM pg_t1;")
    assert err2 is not None
    assert "pg_t1" in err2

def test_postgres_engine_profiling_and_operators():
    try:
        engine = SQLEvalEngine(engine_type="postgres")
    except Exception as e:
        pytest.skip(f"PostgreSQL container not reachable: {e}")

    engine.load_seed_data("CREATE TABLE pg_items (id INT); INSERT INTO pg_items SELECT generate_series(1, 20);")
    profile, err = engine.profile_query("SELECT count(*) FROM pg_items;")
    assert err is None
    assert profile is not None

    operators = engine.extract_operators(profile)
    op_types = [op["type"] for op in operators]
    assert any("SCAN" in op or "AGGREGATE" in op for op in op_types)
