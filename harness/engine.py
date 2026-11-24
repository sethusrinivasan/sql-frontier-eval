import duckdb
import pandas as pd
import json
import os
import re
import time
import threading
import sqlparse
from typing import Optional, Tuple, Dict, Any, List

try:
    import psycopg2
    from psycopg2 import sql as pgsql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from databricks import sql as dbsql
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False


def load_env_file(filepath: str = ".env"):
    """Loads key=value pairs from .env into os.environ if not already set."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

load_env_file()


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


def adapt_to_databricks(sql: str) -> str:
    """
    Adapts DuckDB-centric benchmark queries and DDL to Databricks SQL / Spark SQL:
    1. Strips DuckDB engine pragma/extension commands (INSTALL, LOAD, PRAGMA)
    2. Converts unparameterized VARCHAR and TEXT to STRING
    3. Converts square-bracket array literals [1.0, 2.0] to array(1.0, 2.0)
    4. Converts date_diff('unit', ...) to date_diff(UNIT, ...)
    5. Converts DuckDB ASOF JOIN ON ... AND condition to Databricks MATCH_CONDITION
    """
    if not sql:
        return ""
    res = re.sub(r"INSTALL\s+\w+;\s*LOAD\s+\w+;?", "", sql, flags=re.IGNORECASE)
    res = re.sub(r"PRAGMA\s+[^;]+;?", "", res, flags=re.IGNORECASE)
    # Convert unparameterized VARCHAR and TEXT to STRING
    res = re.sub(r"\bVARCHAR\b(?!\s*\()", "STRING", res, flags=re.IGNORECASE)
    res = re.sub(r"\bTEXT\b", "STRING", res, flags=re.IGNORECASE)
    # Convert fixed-size or bracketed array types FLOAT[N] -> ARRAY<FLOAT>
    res = re.sub(r"\bFLOAT\[\d+\]", "ARRAY<FLOAT>", res, flags=re.IGNORECASE)
    res = re.sub(r"\bDOUBLE\[\d+\]", "ARRAY<DOUBLE>", res, flags=re.IGNORECASE)
    res = re.sub(r"\bINT(EGER)?\[\d*\]", "ARRAY<INT>", res, flags=re.IGNORECASE)
    # Convert square-bracket float/number array literals [0.1, 0.2] to array(0.1, 0.2)
    res = re.sub(r"(?<![A-Za-z0-9_])\[\s*([0-9\.\,\s\-]+)\s*\]", r"array(\1)", res)
    # Databricks date_diff expects unquoted unit: date_diff('second', a, b) -> date_diff(SECOND, a, b)
    res = re.sub(r"\bdate_diff\s*\(\s*['\"](\w+)['\"]\s*,", lambda m: f"date_diff({m.group(1).upper()},", res, flags=re.IGNORECASE)
    # Databricks ASOF JOIN: convert ON ... AND t1.ts >= t2.ts to ON ... MATCH_CONDITION ( t1.ts >= t2.ts )
    res = re.sub(
        r"ASOF\s+JOIN\s+([A-Za-z0-9_]+(?:\s+(?:AS\s+)?[A-Za-z0-9_]+)?)\s+ON\s+(.+?)\s+AND\s+([A-Za-z0-9_\.]+\s*(?:>=|<=|>|<)\s*[A-Za-z0-9_\.]+)",
        r"ASOF JOIN \1 ON \2 MATCH_CONDITION ( \3 )",
        res,
        flags=re.IGNORECASE | re.DOTALL
    )
    # Convert UNNEST(generate_series(start, end, step)) to explode(sequence(start, end, step))
    res = re.sub(r"\bUNNEST\s*\(\s*generate_series\s*\(", "explode(sequence(", res, flags=re.IGNORECASE)
    # Convert LAST_VALUE/FIRST_VALUE(expr IGNORE NULLS) -> last_value/first_value(expr, true)
    res = re.sub(r"LAST_VALUE\s*\(\s*([^,\)]+?)\s+IGNORE\s+NULLS\s*\)", r"last_value(\1, true)", res, flags=re.IGNORECASE)
    res = re.sub(r"FIRST_VALUE\s*\(\s*([^,\)]+?)\s+IGNORE\s+NULLS\s*\)", r"first_value(\1, true)", res, flags=re.IGNORECASE)
    return res.strip()


class SQLEvalEngine:
    """
    Unified analytical SQL execution sandbox supporting:
    - DuckDB (In-Memory Columnar OLAP engine)
    - PostgreSQL 19+ (Relational, Vector with pgvector, Full-Text & Analytical Extensions)
    - Databricks SQL (Serverless Warehouse / Unity Catalog Compute Cluster)
    Provides query execution, statement timeout watchdog, physical execution plan profiling,
    operator tree decomposition, and anti-pattern detection.
    """
    def __init__(
        self,
        engine_type: str = "duckdb",
        threads: int = 4,
        pg_conn_params: Optional[Dict[str, Any]] = None,
        databricks_conn_params: Optional[Dict[str, Any]] = None,
    ):
        self.engine_type = engine_type.lower()
        self.threads = threads
        self.con: Optional[duckdb.DuckDBPyConnection] = None
        self.pg_conn: Optional[Any] = None
        self.databricks_conn: Optional[Any] = None

        self.pg_conn_params = pg_conn_params or {
            "dbname": os.environ.get("PGDATABASE", "sql_frontier_eval"),
            "user": os.environ.get("PGUSER", "postgres"),
            "password": os.environ.get("PGPASSWORD", "postgrespassword"),
            "host": os.environ.get("PGHOST", "127.0.0.1"),
            "port": int(os.environ.get("PGPORT", "5432")),
        }

        self.databricks_conn_params = databricks_conn_params or {
            "server_hostname": os.environ.get("DATABRICKS_SERVER_HOSTNAME"),
            "http_path": os.environ.get("DATABRICKS_HTTP_PATH"),
            "access_token": os.environ.get("DATABRICKS_TOKEN"),
            "client_id": os.environ.get("DATABRICKS_CLIENT_ID"),
            "client_secret": os.environ.get("DATABRICKS_CLIENT_SECRET"),
            "catalog": os.environ.get("DATABRICKS_CATALOG", "main"),
            "schema": os.environ.get("DATABRICKS_SCHEMA", "eval_sandbox"),
        }

        self.reset_sandbox()

    def reset_sandbox(self):
        """
        Reinitializes a clean database environment to prevent cross-task data leakage.
        - For DuckDB: recreates an isolated in-memory catalog (:memory:).
        - For PostgreSQL: recreates and sets search_path to an isolated 'eval_sandbox' schema.
        - For Databricks: isolates into configured sandbox schema and drops previous tables.
        """
        if self.engine_type == "postgres":
            if not PSYCOPG2_AVAILABLE:
                raise RuntimeError("psycopg2 is required for PostgreSQL execution. Install via pip install psycopg2-binary.")
            if self.pg_conn is None or getattr(self.pg_conn, "closed", True):
                self.pg_conn = psycopg2.connect(**self.pg_conn_params)
                self.pg_conn.autocommit = True
            with self.pg_conn.cursor() as cur:
                cur.execute("DROP SCHEMA IF EXISTS eval_sandbox CASCADE; CREATE SCHEMA eval_sandbox; SET search_path TO eval_sandbox, public;")

        elif self.engine_type == "databricks":
            if not DATABRICKS_AVAILABLE:
                raise RuntimeError("databricks-sql-connector is required for Databricks execution. Install via pip install databricks-sql-connector.")
            if not self.databricks_conn_params.get("server_hostname") or not self.databricks_conn_params.get("http_path"):
                raise ValueError(
                    "Databricks credentials missing. Please set DATABRICKS_SERVER_HOSTNAME and "
                    "DATABRICKS_HTTP_PATH in your environment or .env file."
                )
            if self.databricks_conn is None:
                conn_kwargs = {
                    "server_hostname": self.databricks_conn_params["server_hostname"],
                    "http_path": self.databricks_conn_params["http_path"],
                    "catalog": self.databricks_conn_params.get("catalog", "workspace"),
                    "schema": self.databricks_conn_params.get("schema", "sql_frontier_eval_sandbox"),
                }
                if self.databricks_conn_params.get("access_token"):
                    conn_kwargs["access_token"] = self.databricks_conn_params["access_token"]
                elif self.databricks_conn_params.get("client_id") and self.databricks_conn_params.get("client_secret"):
                    conn_kwargs["client_id"] = self.databricks_conn_params["client_id"]
                    conn_kwargs["client_secret"] = self.databricks_conn_params["client_secret"]
                    conn_kwargs["auth_type"] = "databricks-oauth"
                else:
                    # Default to native Databricks OAuth U2M
                    conn_kwargs["auth_type"] = "databricks-oauth"

                self.databricks_conn = dbsql.connect(**conn_kwargs)
            catalog = self.databricks_conn_params.get("catalog", "workspace")
            schema = self.databricks_conn_params.get("schema", "sql_frontier_eval_sandbox")
            with self.databricks_conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
                cur.execute(f"USE CATALOG {catalog}")
                cur.execute(f"USE SCHEMA {schema}")
                try:
                    cur.execute("SHOW TABLES")
                    tables = cur.fetchall()
                    for row in tables:
                        tname = row[1] if len(row) > 1 else row[0]
                        cur.execute(f"DROP TABLE IF EXISTS {tname}")
                except Exception:
                    pass

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
            elif self.engine_type == "databricks":
                adapted_sql = adapt_to_databricks(setup_sql)
                with self.databricks_conn.cursor() as cur:
                    statements = [
                        stmt.strip() for stmt in sqlparse.split(adapted_sql)
                        if stmt.strip() and not stmt.strip().startswith("--")
                    ]
                    for stmt in statements:
                        clean_stmt = stmt.rstrip(";").strip()
                        if clean_stmt:
                            cur.execute(clean_stmt)
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

        elif self.engine_type == "databricks":
            adapted_query = adapt_to_databricks(query)
            try:
                with self.databricks_conn.cursor() as cur:
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
                return None, str(e), elapsed_ms

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
        - Databricks: EXPLAIN EXTENDED
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

        elif self.engine_type == "databricks":
            adapted_query = adapt_to_databricks(query)
            try:
                with self.databricks_conn.cursor() as cur:
                    cur.execute(f"EXPLAIN EXTENDED {adapted_query}")
                    rows = cur.fetchall()
                    plan_text = "\n".join([str(r[0]) for r in rows if r])
                    return {"plan_text": plan_text}, None
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
        Supports DuckDB (JSON tree), PostgreSQL (EXPLAIN JSON tree), and Databricks (Plan text).
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

        def _traverse_databricks(plan_text: str):
            lines = plan_text.splitlines()
            for line in lines:
                line_str = line.strip()
                if not line_str or line_str.startswith("=="):
                    continue
                m = re.search(r"(\w+Join|CartesianProduct|HashAggregate|SortAggregate|Window|FileScan|BatchScan|Filter|Project|Sort)", line_str)
                if m:
                    raw_op = m.group(1)
                    op_type = raw_op.upper()
                    if "CARTESIANPRODUCT" in op_type or "BROADCASTNESTEDLOOPJOIN" in op_type:
                        op_type = "CROSS_PRODUCT"
                    elif "JOIN" in op_type:
                        op_type = "HASH_JOIN"
                    elif "AGGREGATE" in op_type:
                        op_type = "HASH_GROUP_BY"
                    elif "SCAN" in op_type:
                        op_type = "TABLE_SCAN"
                    operators.append({
                        "type": op_type,
                        "raw_type": raw_op,
                        "name": raw_op,
                        "cardinality": 0,
                        "timing_sec": 0.0,
                        "rows_scanned": 0,
                        "extra_info": {"plan_line": line_str[:120]}
                    })

        if isinstance(profile_tree, dict) and "plan_text" in profile_tree:
            _traverse_databricks(profile_tree["plan_text"])
        elif isinstance(profile_tree, list) and len(profile_tree) > 0 and isinstance(profile_tree[0], dict) and "Plan" in profile_tree[0]:
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
        Handles DuckDB, PostgreSQL, and Databricks execution profiles.
        """
        if not profile_tree:
            return {}

        # Databricks format
        if isinstance(profile_tree, dict) and "plan_text" in profile_tree:
            return {
                "cpu_time_sec": 0.0,
                "latency_sec": 0.0,
                "plan_preview": profile_tree["plan_text"][:300]
            }

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
