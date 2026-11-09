import pandas as pd
import numpy as np
from decimal import Decimal
from typing import Dict, Any, Optional, List
from harness.engine import SQLEvalEngine

class SQLGrader:
    """
    Robust analytical SQL grader testing semantic data correctness and plan efficiency.
    """

    @classmethod
    def canonicalize_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalizes column names, numeric types, and null representations
        to ensure deterministic, non-flaky evaluation.
        """
        if df is None:
            return None

        clean_df = df.copy()

        # 1. Canonicalize column names: lowercase and stripped
        clean_df.columns = [str(col).strip().lower() for col in clean_df.columns]

        # 2. Normalize dtypes across columns
        for col in clean_df.columns:
            series = clean_df[col]
            # Coerce Decimal objects (from DuckDB DECIMAL types) to float64 for floating-point tolerance
            if series.dtype == object and len(series) > 0:
                first_val = series.dropna().iloc[0] if not series.dropna().empty else None
                if isinstance(first_val, Decimal):
                    clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce").astype(float)
                elif isinstance(first_val, str):
                    clean_df[col] = clean_df[col].apply(lambda x: str(x).strip() if pd.notnull(x) else np.nan)
            # Uniform integer bit-width
            elif pd.api.types.is_integer_dtype(series):
                if series.isna().any():
                    clean_df[col] = clean_df[col].astype("Int64")
                else:
                    clean_df[col] = clean_df[col].astype("int64")

        return clean_df

    @classmethod
    def sort_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Deterministically sorts rows by all columns when row ordering is unconstrained.
        Handles unhashable types (lists, numpy arrays, dicts) cleanly.
        """
        if df.empty or len(df) == 1:
            return df.reset_index(drop=True)

        sort_df = df.copy()
        for col in sort_df.columns:
            val = sort_df[col].dropna().iloc[0] if not sort_df[col].dropna().empty else None
            if isinstance(val, (list, np.ndarray, dict)):
                sort_df[col] = sort_df[col].apply(lambda x: tuple(x) if isinstance(x, (list, np.ndarray)) else str(x))

        sort_indices = sort_df.sort_values(by=list(sort_df.columns), na_position="first").index
        return df.iloc[sort_indices].reset_index(drop=True)

    @classmethod
    def grade(
        cls,
        candidate_df: Optional[pd.DataFrame],
        golden_df: pd.DataFrame,
        profile_tree: Optional[Dict[str, Any]] = None,
        ordered: bool = False,
        disallowed_ops: Optional[List[str]] = None,
        exec_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation pipeline:
        1. Execution error handling
        2. Non-empty result validation
        3. Shape verification
        4. Column schema alignment
        5. Row ordering & value equivalence (tolerance: rtol=1e-3, atol=1e-3)
        6. Plan efficiency & anti-pattern verification
        """
        # 1. Check for runtime / syntax execution error
        if exec_error:
            return {
                "passed": False,
                "verdict": "SYNTAX_OR_EXECUTION_ERROR",
                "reason": f"Query execution failed: {exec_error}",
                "diagnostics": {"error": exec_error}
            }

        if candidate_df is None:
            return {
                "passed": False,
                "verdict": "EXECUTION_ERROR",
                "reason": "Execution error: No data returned from query.",
                "diagnostics": {}
            }

        if golden_df is None:
            return {
                "passed": False,
                "verdict": "HARNESS_ERROR",
                "reason": "Harness error: Golden query produced no DataFrame.",
                "diagnostics": {}
            }

        # Canonicalize both dataframes
        c_cand = cls.canonicalize_dataframe(candidate_df)
        c_gold = cls.canonicalize_dataframe(golden_df)

        # 2. Shape verification
        if c_cand.shape != c_gold.shape:
            return {
                "passed": False,
                "verdict": "SHAPE_MISMATCH",
                "reason": f"Shape mismatch: Expected {c_gold.shape[0]} rows x {c_gold.shape[1]} cols, got {c_cand.shape[0]} rows x {c_cand.shape[1]} cols",
                "diagnostics": {
                    "expected_shape": c_gold.shape,
                    "actual_shape": c_cand.shape
                }
            }

        # 3. Column schema verification
        cand_cols = list(c_cand.columns)
        gold_cols = list(c_gold.columns)

        if set(cand_cols) != set(gold_cols):
            missing = sorted(list(set(gold_cols) - set(cand_cols)))
            unexpected = sorted(list(set(cand_cols) - set(gold_cols)))
            return {
                "passed": False,
                "verdict": "COLUMN_MISMATCH",
                "reason": f"Column mismatch: Expected {gold_cols}, got {cand_cols}. (Missing: {missing}, Unexpected: {unexpected})",
                "diagnostics": {
                    "missing_columns": missing,
                    "unexpected_columns": unexpected
                }
            }

        # Reorder candidate columns to match golden column order exactly
        c_cand = c_cand[gold_cols]

        # 4. Row ordering & deterministic sorting
        if not ordered:
            c_cand = cls.sort_dataframe(c_cand)
            c_gold = cls.sort_dataframe(c_gold)
        else:
            c_cand = c_cand.reset_index(drop=True)
            c_gold = c_gold.reset_index(drop=True)

        # 5. Numerical and categorical value equivalence
        try:
            pd.testing.assert_frame_equal(
                c_cand,
                c_gold,
                check_exact=False,
                rtol=1e-3,
                atol=1e-3,
                check_dtype=False
            )
        except AssertionError as e:
            err_line = str(e).splitlines()[0] if str(e).splitlines() else str(e)
            # Find the first mismatch row / column for clear diagnostic
            diff_diag = cls._find_first_mismatch(c_cand, c_gold)
            return {
                "passed": False,
                "verdict": "VALUE_MISMATCH",
                "reason": f"Data discrepancy: {err_line}",
                "diagnostics": diff_diag
            }

        # 6. Plan efficiency and anti-pattern analysis
        if profile_tree:
            anti_patterns = SQLEvalEngine.detect_anti_patterns(
                profile_tree, 
                disallowed_ops=disallowed_ops
            )
            if anti_patterns:
                return {
                    "passed": False,
                    "verdict": "EFFICIENCY_VIOLATION",
                    "reason": f"Performance failure: {anti_patterns[0]}",
                    "diagnostics": {
                        "anti_patterns": anti_patterns,
                        "profile_metrics": SQLEvalEngine.extract_profile_metrics(profile_tree)
                    }
                }

        # All checks passed
        profile_metrics = SQLEvalEngine.extract_profile_metrics(profile_tree) if profile_tree else {}
        return {
            "passed": True,
            "verdict": "PASS",
            "reason": "All correctness and performance checks passed",
            "diagnostics": {
                "profile_metrics": profile_metrics,
                "rows_verified": len(c_gold)
            }
        }

    @staticmethod
    def _find_first_mismatch(c_cand: pd.DataFrame, c_gold: pd.DataFrame) -> Dict[str, Any]:
        """
        Isolates the exact row, column, expected value, and actual value of first discrepancy.
        """
        for col in c_gold.columns:
            series_gold = c_gold[col]
            series_cand = c_cand[col]
            for idx in range(min(len(series_gold), len(series_cand))):
                val_g = series_gold.iloc[idx]
                val_c = series_cand.iloc[idx]
                if pd.isnull(val_g) and pd.isnull(val_c):
                    continue
                # Numeric comparison
                if isinstance(val_g, (int, float, np.number)) and isinstance(val_c, (int, float, np.number)):
                    if not np.isclose(val_g, val_c, rtol=1e-3, atol=1e-3):
                        exp_val = int(val_g) if isinstance(val_g, (int, np.integer)) else float(val_g)
                        act_val = int(val_c) if isinstance(val_c, (int, np.integer)) else float(val_c)
                        return {
                            "column": col,
                            "row_index": idx,
                            "expected": exp_val,
                            "actual": act_val,
                            "difference": float(val_c - val_g)
                        }
                elif val_g != val_c:
                    return {
                        "column": col,
                        "row_index": idx,
                        "expected": str(val_g),
                        "actual": str(val_c)
                    }
        return {}