import duckdb
import pandas as pd
import json
import os
import re
import time
import threading
from typing import Optional, Tuple, Dict, Any, List

try:
    import psycopg2
    from psycopg2 import sql as pgsql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


def adapt_to_postgres(sql: str) -> str:
    """
    Adapts DuckDB-centric benchmark queries and DDL to PostgreSQL syntax:
    1. Converts square-bracket numeric array literals: [1.0, 2.0] -> ARRAY[1.0, 2.0]
    2. Enforces quoted intervals: INTERVAL 30 MINUTE -> INTERVAL '30 MINUTE'
    3. Adapts fixed-size vector types: FLOAT[N] -> FLOAT[]
    4. Strips DuckDB engine pragma/extension commands (INSTALL, LOAD, PRAGMA)
    """
    if not sql:
        return ""
    # Strip DuckDB pragmas and install/load statements
    res = re.sub(r"INSTALL\s+\w+;\s*LOAD\s+\w+;?", "", sql, flags=re.IGNORECASE)
    res = re.sub(r"PRAGMA\s+[^;]+;?", "", res, flags=re.IGNORECASE)
    # Convert square-bracket numeric/float arrays to ARRAY[...]
    res = re.sub(r"(?<![A-Za-z0-9_])\[\s*([0-9\.\,\s\-]+)\s*\]", r"ARRAY[\1]", res)
    # Enforce quoted interval strings: INTERVAL 30 SECOND -> INTERVAL '30 SECOND'
    res = re.sub(r"INTERVAL\s+(\d+)\s+([A-Za-z]+)", r"INTERVAL '\1 \2'", res, flags=re.IGNORECASE)
    # Adapt FLOAT[D] in DDL to standard array type FLOAT[]
    res = re.sub(r"FLOAT\[\d+\]", "FLOAT[]", res, flags=re.IGNORECASE)
    return res


class SQLEvalEngine:
    """
    Unified analytical SQL execution sandbox supporting:
    - DuckDB (In-Memory Columnar OLAP engine)
    - PostgreSQL 18+ (Relational, Vector with pgvector, Full-Text & Analytical Extensions)
    Provides query execution, statement timeout watchdog, physical execution plan profiling,
    operator tree decomposition, and anti-pattern detection.
    """
    def __init__(
        self,
        engine_type: str = "duckdb",
        threads: int = 4,
        pg_conn_params: Optional[Dict[str, Any]] = None
    ):
        self.engine_type = engine_type.lower()
        self.threads = threads
        self.con: Optional[duckdb.DuckDBPyConnection] = None
        self.pg_conn: Optional[Any] = None
        self.pg_conn_params = pg_conn_params or {
            "dbname": os.environ.get("PGDATABASE", "sql_frontier_eval"),
            "user": os.environ.get("PGUSER", "postgres"),
            "password": os.environ.get("PGPASSWORD", "postgrespassword"),
            "host": os.environ.get("PGHOST", "127.0.0.1"),
            "port": int(os.environ.get("PGPORT", "5432")),
        }
        self.reset_sandbox()

    def reset_sandbox(self):
        """
        Reinitializes a clean database environment to prevent cross-task data leakage.
        - For DuckDB: recreates an isolated in-memory catalog (:memory:).
        - For PostgreSQL: recreates and sets search_path to an isolated 'eval_sandbox' schema.
        """
        if self.engine_type == "postgres":
            if not PSYCOPG2_AVAILABLE:
                raise RuntimeError("psycopg2 is required for PostgreSQL execution. Install via pip install psycopg2-binary.")
            if self.pg_conn is None or getattr(self.pg_conn, "closed", True):
                self.pg_conn = psycopg2.connect(**self.pg_conn_params)
                self.pg_conn.autocommit = True
            with self.pg_conn.cursor() as cur:
                cur.execute("DROP SCHEMA IF EXISTS eval_sandbox CASCADE; CREATE SCHEMA eval_sandbox; SET search_path TO eval_sandbox, public;")
        else:
            if self.con is not None:
                try:
                    self.con.close()
                except Exception:
                    pass
            self.con = duckdb.connect(database=":memory:")
            self.con.execute(f"PRAGMA threads={self.threads};")
            self.con.execute("SET max_memory = '2GB';")
            try:
                self.con.execute("INSTALL fts; LOAD fts;")
            except Exception:
                pass

    def load_seed_data(self, setup_sql: str) -> Optional[str]:
        """
        Executes setup DDL and populates synthetic fixture data.
        Returns an error string if setup fails, or None on success.
        """
        try:
            if self.engine_type == "postgres":
                adapted_sql = adapt_to_postgres(setup_sql)
                with self.pg_conn.cursor() as cur:
                    cur.execute(adapted_sql)
            else:
                self.con.execute(setup_sql)
            return None
        except Exception as e:
            return str(e)

    def execute_query(self, query: str, timeout_sec: float = 15.0) -> Tuple[Optional[pd.DataFrame], Optional[str], float]:
        """
        Executes an analytical SQL query with memory ceiling and statement timeout guard.
        Returns (result_df, error_message, execution_time_ms).
        """
        start_time = time.perf_counter()

        if self.engine_type == "postgres":
            adapted_query = adapt_to_postgres(query)
            try:
                with self.pg_conn.cursor() as cur:
                    timeout_ms = int(timeout_sec * 1000)
                    cur.execute(f"SET statement_timeout = '{timeout_ms}';")
                    cur.execute(adapted_query)
                    if cur.description is not None:
                        cols = [d[0] for d in cur.description]
                        rows = cur.fetchall()
                        df = pd.DataFrame(rows, columns=cols)
                    else:
                        df = pd.DataFrame()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return df, None, elapsed_ms
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                err_msg = str(e).strip()
                if "canceling statement due to statement timeout" in err_msg.lower():
                    err_msg = f"Execution timed out (> {timeout_sec:.1f}s) - runaway query terminated safely."
                return None, err_msg, elapsed_ms
        else:
            timer = threading.Timer(timeout_sec, self.con.interrupt)
            timer.start()
            try:
                df = self.con.execute(query).df()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return df, None, elapsed_ms
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                err_msg = str(e)
                if "Interrupt" in type(e).__name__ or "Interrupted" in err_msg:
                    err_msg = f"Execution timed out (> {timeout_sec:.1f}s) - runaway query terminated safely."
                return None, err_msg, elapsed_ms
            finally:
                timer.cancel()

    def profile_query(self, query: str) -> Tuple[Optional[Any], Optional[str]]:
        """
        Runs execution plan profiling:
        - DuckDB: EXPLAIN (FORMAT JSON)
        - PostgreSQL: EXPLAIN (ANALYZE, FORMAT JSON, VERBOSE)
        """
        if self.engine_type == "postgres":
            adapted_query = adapt_to_postgres(query)
            try:
                with self.pg_conn.cursor() as cur:
                    cur.execute(f"EXPLAIN (ANALYZE, FORMAT JSON, VERBOSE) {adapted_query}")
                    res = cur.fetchone()[0]
                    if isinstance(res, str):
                        profile_json = json.loads(res)
                    else:
                        profile_json = res
                    return profile_json, None
            except Exception as e:
                return None, str(e)
        else:
            # DuckDB Primary: EXPLAIN (FORMAT JSON)
            try:
                prof_df = self.con.execute(f"EXPLAIN (FORMAT JSON) {query}").df()
                if not prof_df.empty and "explain_value" in prof_df.columns:
                    profile_raw = prof_df["explain_value"].iloc[0]
                    profile_json = json.loads(profile_raw)
                    return profile_json, None
            except Exception:
                pass

            # DuckDB Fallback: EXPLAIN ANALYZE with JSON profiling
            try:
                self.con.execute("PRAGMA enable_profiling = 'json';")
                prof_df = self.con.execute(f"EXPLAIN ANALYZE {query}").df()
                self.con.execute("PRAGMA disable_profiling;")

                if prof_df.empty or "explain_value" not in prof_df.columns:
                    return None, "Empty profile returned by DuckDB"

                profile_raw = prof_df["explain_value"].iloc[0]
                profile_json = json.loads(profile_raw)
                return profile_json, None
            except Exception as e:
                try:
                    self.con.execute("PRAGMA disable_profiling;")
                except Exception:
                    pass
                return None, str(e)

    @staticmethod
    def extract_operators(profile_tree: Any) -> List[Dict[str, Any]]:
        """
        Recursively extracts all operators from execution plan trees.
        Supports both DuckDB (JSON tree) and PostgreSQL (EXPLAIN JSON tree).
        """
        operators = []

        def _traverse_duckdb(node: Any):
            if isinstance(node, list):
                for item in node:
                    _traverse_duckdb(item)
                return
            if not isinstance(node, dict):
                return

            raw_type = node.get("operator_type") or node.get("name") or "UNKNOWN"
            op_type = raw_type
            if op_type in ("SEQ_SCAN", "COLUMN_DATA_SCAN"):
                op_type = "TABLE_SCAN"

            operators.append({
                "type": op_type,
                "raw_type": raw_type,
                "name": node.get("operator_name") or node.get("name", ""),
                "cardinality": node.get("operator_cardinality") or node.get("extra_info", {}).get("Estimated Cardinality", 0),
                "timing_sec": node.get("operator_timing", 0.0),
                "rows_scanned": node.get("operator_rows_scanned", 0),
                "extra_info": node.get("extra_info", {})
            })
            for child in node.get("children", []):
                _traverse_duckdb(child)

        def _traverse_postgres(node: Any):
            if isinstance(node, list):
                for item in node:
                    _traverse_postgres(item)
                return
            if not isinstance(node, dict):
                return

            plan_node = node.get("Plan", node)
            raw_type = plan_node.get("Node Type", "UNKNOWN")
            op_type = raw_type.upper().replace(" ", "_")

            operators.append({
                "type": op_type,
                "raw_type": raw_type,
                "name": plan_node.get("Relation Name") or plan_node.get("Alias") or raw_type,
                "cardinality": plan_node.get("Actual Rows") or plan_node.get("Plan Rows", 0),
                "timing_sec": (plan_node.get("Actual Total Time", 0.0)) / 1000.0,
                "rows_scanned": plan_node.get("Actual Rows", 0),
                "extra_info": {
                    "Startup Cost": plan_node.get("Startup Cost", 0.0),
                    "Total Cost": plan_node.get("Total Cost", 0.0),
                    "Actual Loops": plan_node.get("Actual Loops", 1)
                }
            })
            for child in plan_node.get("Plans", []):
                _traverse_postgres(child)

        if isinstance(profile_tree, list) and len(profile_tree) > 0 and isinstance(profile_tree[0], dict) and "Plan" in profile_tree[0]:
            _traverse_postgres(profile_tree)
        elif isinstance(profile_tree, dict) and "Plan" in profile_tree:
            _traverse_postgres(profile_tree)
        else:
            _traverse_duckdb(profile_tree)

        return operators

    @staticmethod
    def extract_profile_metrics(profile_tree: Any) -> Dict[str, Any]:
        """
        Extracts high-level execution and resource consumption metrics.
        Handles both DuckDB and PostgreSQL execution profiles.
        """
        if not profile_tree:
            return {}

        # PostgreSQL format
        if isinstance(profile_tree, list) and len(profile_tree) > 0 and isinstance(profile_tree[0], dict) and "Plan" in profile_tree[0]:
            root = profile_tree[0]
            plan = root.get("Plan", {})
            return {
                "cpu_time_sec": (root.get("Execution Time", 0.0)) / 1000.0,
                "latency_sec": (root.get("Execution Time", 0.0)) / 1000.0,
                "planning_time_sec": (root.get("Planning Time", 0.0)) / 1000.0,
                "cumulative_cardinality": plan.get("Actual Rows", 0),
                "rows_returned": plan.get("Actual Rows", 0),
                "total_cost": plan.get("Total Cost", 0.0)
            }

        # DuckDB format
        if isinstance(profile_tree, dict):
            return {
                "cpu_time_sec": profile_tree.get("cpu_time", 0.0),
                "latency_sec": profile_tree.get("latency", 0.0),
                "cumulative_cardinality": profile_tree.get("cumulative_cardinality", 0),
                "cumulative_rows_scanned": profile_tree.get("cumulative_rows_scanned", 0),
                "rows_returned": profile_tree.get("rows_returned", 0),
                "peak_buffer_memory_bytes": profile_tree.get("system_peak_buffer_memory", 0),
                "peak_temp_dir_bytes": profile_tree.get("system_peak_temp_dir_size", 0)
            }

        return {}

    @classmethod
    def detect_anti_patterns(
        cls, 
        profile_tree: Any, 
        disallowed_ops: Optional[List[str]] = None
    ) -> List[str]:
        """
        Scans the query execution tree for architectural anti-patterns.
        """
        if not profile_tree:
            return []

        operators = cls.extract_operators(profile_tree)
        detected = []

        if disallowed_ops is not None:
            active_disallowed = {op.upper() for op in disallowed_ops}
        else:
            active_disallowed = {"CROSS_PRODUCT", "BLOCKWISE_NL_JOIN", "NESTED_LOOP"}

        for op in operators:
            op_type = op["type"].upper()
            if op_type in active_disallowed:
                detected.append(
                    f"Disallowed operator '{op_type}' detected in execution plan (intermediate cardinality: {op['cardinality']})"
                )

        return detected
