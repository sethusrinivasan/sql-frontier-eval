import duckdb
import pandas as pd
import json
import time
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

    def execute_query(self, query: str) -> Tuple[Optional[pd.DataFrame], Optional[str], float]:
        """
        Executes an analytical SQL query.
        Returns (result_df, error_message, execution_time_ms).
        """
        start_time = time.perf_counter()
        try:
            df = self.con.execute(query).df()
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return df, None, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return None, str(e), elapsed_ms

    def profile_query(self, query: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Runs EXPLAIN ANALYZE with JSON profiling enabled and returns the parsed profile tree.
        """
        try:
            # Enable JSON profiling specifically for this EXPLAIN ANALYZE statement
            self.con.execute("PRAGMA enable_profiling = 'json';")
            prof_df = self.con.execute(f"EXPLAIN ANALYZE {query}").df()
            self.con.execute("PRAGMA disable_profiling;")

            if prof_df.empty or "explain_value" not in prof_df.columns:
                return None, "Empty profile returned by DuckDB"

            profile_raw = prof_df["explain_value"].iloc[0]
            profile_json = json.loads(profile_raw)
            return profile_json, None
        except Exception as e:
            # Ensure profiling is disabled if an error occurs
            try:
                self.con.execute("PRAGMA disable_profiling;")
            except Exception:
                pass
            return None, str(e)

    @staticmethod
    def extract_operators(profile_tree: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recursively extracts all operators from DuckDB's profile JSON tree.
        """
        operators = []

        def _traverse(node: Dict[str, Any]):
            if not isinstance(node, dict):
                return
            if "operator_type" in node or "operator_name" in node:
                operators.append({
                    "type": node.get("operator_type", "UNKNOWN"),
                    "name": node.get("operator_name", ""),
                    "cardinality": node.get("operator_cardinality", 0),
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

        default_disallowed = {"CROSS_PRODUCT", "BLOCKWISE_NL_JOIN"}
        if disallowed_ops:
            default_disallowed.update(op.upper() for op in disallowed_ops)

        for op in operators:
            op_type = op["type"].upper()
            if op_type in default_disallowed:
                detected.append(
                    f"Disallowed operator '{op_type}' detected in execution plan (intermediate cardinality: {op['cardinality']})"
                )

        return detected