import duckdb
import pandas as pd
import json
import time
import threading
from typing import Optional, Tuple, Dict, Any, List

class SQLEvalEngine:
    """
    Isolated DuckDB execution sandbox with profiling and anti-pattern analysis.
    """
    def __init__(self, threads: int = 4):
        self.threads = threads
        self.con: duckdb.DuckDBPyConnection = None
        self.reset_sandbox()

    def reset_sandbox(self):
        """Reinitializes a clean in-memory database instance to prevent cross-task leakage."""
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
        Runs EXPLAIN (FORMAT JSON) to extract the execution plan tree.
        Falls back to EXPLAIN ANALYZE for backward compatibility.
        """
        # Primary: EXPLAIN (FORMAT JSON)
        try:
            prof_df = self.con.execute(f"EXPLAIN (FORMAT JSON) {query}").df()
            if not prof_df.empty and "explain_value" in prof_df.columns:
                profile_raw = prof_df["explain_value"].iloc[0]
                profile_json = json.loads(profile_raw)
                return profile_json, None
        except Exception:
            pass

        # Fallback: EXPLAIN ANALYZE with JSON profiling
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
        Recursively extracts all operators from DuckDB's profile JSON tree.
        Handles both DuckDB 1.x and 2.x formats.
        """
        operators = []

        def _traverse(node: Any):
            if isinstance(node, list):
                for item in node:
                    _traverse(item)
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
                _traverse(child)

        _traverse(profile_tree)
        return operators

    @staticmethod
    def extract_profile_metrics(profile_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts high-level execution and resource consumption metrics.
        """
        if not profile_tree or not isinstance(profile_tree, dict):
            return {}

        return {
            "cpu_time_sec": profile_tree.get("cpu_time", 0.0),
            "latency_sec": profile_tree.get("latency", 0.0),
            "cumulative_cardinality": profile_tree.get("cumulative_cardinality", 0),
            "cumulative_rows_scanned": profile_tree.get("cumulative_rows_scanned", 0),
            "rows_returned": profile_tree.get("rows_returned", 0),
            "peak_buffer_memory_bytes": profile_tree.get("system_peak_buffer_memory", 0),
            "peak_temp_dir_bytes": profile_tree.get("system_peak_temp_dir_size", 0)
        }

    @classmethod
    def detect_anti_patterns(
        cls, 
        profile_tree: Dict[str, Any], 
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
            active_disallowed = {"CROSS_PRODUCT", "BLOCKWISE_NL_JOIN"}

        for op in operators:
            op_type = op["type"].upper()
            if op_type in active_disallowed:
                detected.append(
                    f"Disallowed operator '{op_type}' detected in execution plan (intermediate cardinality: {op['cardinality']})"
                )

        return detected