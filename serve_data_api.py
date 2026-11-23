#!/usr/bin/env python3
"""
SQL-Frontier-Eval: Alibaba Cloud Quick BI Compatible Data API Service

Exposes benchmark datasets, task definitions, fixture tables, and evaluation
leaderboards conforming to Alibaba Cloud Quick BI Custom Data API specifications.
Supports CORS origins including https://bi-us-east-1.alibabacloud.com.
"""

import argparse
import glob
import json
import math
import os
import sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
FIXTURES_DIR = os.path.join(DATA_DIR, "fixtures")
GOLDEN_DIR = os.path.join(DATA_DIR, "golden_results")

ALLOWED_ORIGINS = [
    "https://bi-us-east-1.alibabacloud.com",
    "http://bi-us-east-1.alibabacloud.com",
]

def load_dataset(resource: str, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads records for the requested resource."""
    if resource in ("aws_1m", "1m", "multi_region", "aws_usage_1m"):
        parquet_path = os.path.join(DATA_DIR, "aws_1m_usage.parquet")
        sample_path = os.path.join(DATA_DIR, "aws_1m_sample.csv")
        if os.path.exists(parquet_path):
            try:
                import duckdb
                return duckdb.query(f"SELECT * FROM '{parquet_path}' LIMIT 10000").df().fillna("").to_dict(orient="records")
            except Exception:
                pass
        if os.path.exists(sample_path):
            df = pd.read_csv(sample_path)
            return df.fillna("").to_dict(orient="records")
        return []

    elif resource in ("aws_daily", "real_aws_daily", "aws_usage", "costs", "usage"):
        csv_path = os.path.join(DATA_DIR, "real_aws_usage_daily.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return df.fillna("").to_dict(orient="records")
        return []

    elif resource in ("aws_services", "real_aws_services", "services"):
        csv_path = os.path.join(DATA_DIR, "real_aws_usage_services.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return df.fillna("").to_dict(orient="records")
        return []

    elif resource in ("aws_summary", "real_aws_summary"):
        csv_path = os.path.join(DATA_DIR, "real_aws_usage_summary.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return df.fillna("").to_dict(orient="records")
        return []

    elif resource == "leaderboard":
        csv_path = os.path.join(DATA_DIR, "benchmark_leaderboard.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return df.fillna("").to_dict(orient="records")
        return []

    elif resource == "fixtures" and table_name:
        csv_path = os.path.join(FIXTURES_DIR, f"{table_name}.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(FIXTURES_DIR, table_name)
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return df.fillna("").to_dict(orient="records")
        return []

    elif resource == "fixtures":
        # Return listing of all fixture tables
        files = sorted(glob.glob(os.path.join(FIXTURES_DIR, "*.csv")))
        items = []
        for f in files:
            bn = os.path.basename(f).replace(".csv", "")
            items.append({
                "table_key": bn,
                "file_name": os.path.basename(f),
                "size_bytes": os.path.getsize(f)
            })
        return items

    elif resource == "golden_results":
        files = sorted(glob.glob(os.path.join(GOLDEN_DIR, "*.csv")))
        items = []
        for f in files:
            bn = os.path.basename(f).replace(".csv", "")
            items.append({
                "result_key": bn,
                "file_name": os.path.basename(f),
                "size_bytes": os.path.getsize(f)
            })
        return items

    else:
        # Default: benchmark tasks
        csv_path = os.path.join(DATA_DIR, "benchmark_tasks.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            return df.fillna("").to_dict(orient="records")
        return []


class AlibabaCloudDataAPIHandler(BaseHTTPRequestHandler):
    """
    HTTP Request handler conforming to Alibaba Cloud Quick BI Custom API specs.
    Provides CORS support for https://bi-us-east-1.alibabacloud.com/ai/resource.
    """

    def _set_cors_headers(self):
        req_origin = self.headers.get("Origin", "")
        if req_origin in ALLOWED_ORIGINS or "alibabacloud.com" in req_origin:
            self.send_header("Access-Control-Allow-Origin", req_origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Origin, X-Custom-Header")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def _handle_request(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Health check
        if path == "/healthz":
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            resp = {
                "code": 200,
                "message": "healthy",
                "service": "sql-frontier-eval-data-api",
                "status": "UP"
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        # Check endpoints
        # Supports /ai/resource, /ai/resource/paginated, /api/resource, /api/resource/paginated, /api/data, etc.
        valid_endpoints = [
            "/ai/resource",
            "/ai/resource/paginated",
            "/api/resource",
            "/api/resource/paginated",
            "/api/data",
            "/api/v1/data",
            "/api/tasks",
            "/api/leaderboard",
            "/api/fixtures",
            "/"
        ]

        if path not in valid_endpoints and not path.startswith("/data"):
            self.send_response(404)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "code": 404,
                "message": f"Endpoint {path} not found. Valid endpoints include /ai/resource, /ai/resource/paginated, /api/resource, /api/data",
                "data": None
            }).encode("utf-8"))
            return

        # Paginated REST API endpoint serving 1M+ records per specification with Date Filtering
        if path in ("/ai/resource/paginated", "/api/resource/paginated"):
            qp = {k.lower(): v for k, v in query_params.items()}

            # Date range filters
            start_date = None
            end_date = None
            for k in ("startdate", "start_date", "date_from", "from", "start", "min_date"):
                if k in qp:
                    start_date = qp[k][0].split("T")[0].split(" ")[0].strip()
                    break
            for k in ("enddate", "end_date", "date_to", "to", "end", "max_date"):
                if k in qp:
                    end_date = qp[k][0].split("T")[0].split(" ")[0].strip()
                    break
            if "date" in qp:
                d_val = qp["date"][0].strip()
                if "," in d_val:
                    parts = d_val.split(",")
                    start_date, end_date = parts[0].strip(), parts[1].strip()
                else:
                    start_date, end_date = d_val, d_val

            # SQL WHERE clause parsing if passed
            raw_filter = qp.get("where", qp.get("filter", [""]))[0]
            if raw_filter:
                import re
                m_start = re.search(r"date\s*(?:>=|>|=)\s*['\"]?(\d{4}-\d{2}-\d{2})['\"]?", raw_filter, re.I)
                if m_start:
                    start_date = m_start.group(1)
                m_end = re.search(r"date\s*(?:<=|<|=)\s*['\"]?(\d{4}-\d{2}-\d{2})['\"]?", raw_filter, re.I)
                if m_end:
                    end_date = m_end.group(1)

            region_filter = qp.get("region", [None])[0]

            try:
                page_val = int(qp.get("page", qp.get("pagenum", [1]))[0])
            except (ValueError, TypeError):
                page_val = 1

            try:
                raw_page_size = qp.get("pagesize", qp.get("page_size", qp.get("limit", [None])))[0]
                page_size_val = int(raw_page_size) if raw_page_size is not None else 1000
            except (ValueError, TypeError):
                page_size_val = 1000

            if "offset" in qp:
                try:
                    off_val = int(qp["offset"][0])
                    page_val = (off_val // max(1, page_size_val)) + 1
                except (ValueError, TypeError):
                    pass

            sort_by = qp.get("sort_by", ["date"])[0]
            sort_order = qp.get("sort_order", ["desc"])[0]

            parquet_path = os.path.join(DATA_DIR, "aws_1m_usage.parquet")
            paginated_data = None
            err_msg = None

            if page_size_val <= 0:
                err_msg = "pageSize must be >= 1"
            elif sort_by not in ("date", "gross_usd", "region", "workload_type"):
                err_msg = f"Unknown sort field: {sort_by}"
            elif os.path.exists(parquet_path):
                try:
                    import duckdb
                    effective_page_size = min(page_size_val, 10000)
                    where_clauses = []
                    if start_date:
                        where_clauses.append(f"date >= '{start_date}'")
                    if end_date:
                        where_clauses.append(f"date <= '{end_date}'")
                    if region_filter:
                        where_clauses.append(f"region = '{region_filter}'")

                    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
                    con = duckdb.connect()

                    if where_str:
                        total = con.execute(f"SELECT COUNT(*) FROM '{parquet_path}' {where_str}").fetchone()[0]
                    else:
                        total = 1_000_000

                    total_pages = math.ceil(total / effective_page_size) if total > 0 else 0
                    if page_val > total_pages:
                        paginated_data = {
                            "total": total,
                            "page": page_val,
                            "pageSize": 0,
                            "totalPages": total_pages,
                            "hasNext": False,
                            "hasPrev": page_val > 1,
                            "records": [],
                        }
                    else:
                        offset = (page_val - 1) * effective_page_size
                        order_dir = sort_order.upper() if sort_order.lower() in ("asc", "desc") else "DESC"
                        data_sql = f"""
                            SELECT date, region, workload_type, gross_usd, color_class, status_label, top_5_services_json, raw_services_json
                            FROM '{parquet_path}'
                            {where_str}
                            ORDER BY {sort_by} {order_dir}
                            LIMIT {effective_page_size} OFFSET {offset}
                        """
                        rows = con.execute(data_sql).fetchall()
                        records = []
                        for r in rows:
                            top5 = json.loads(r[6]) if isinstance(r[6], str) else r[6]
                            raw = json.loads(r[7]) if isinstance(r[7], str) else r[7]
                            records.append({
                                "date": r[0],
                                "region": r[1],
                                "workload_type": r[2],
                                "gross_usd": float(r[3]),
                                "color_class": r[4],
                                "status_label": r[5],
                                "top_5_services": top5,
                                "raw_services": raw,
                            })
                        paginated_data = {
                            "total": total,
                            "page": page_val,
                            "pageSize": len(records),
                            "totalPages": total_pages,
                            "hasNext": page_val < total_pages,
                            "hasPrev": page_val > 1,
                            "records": records,
                        }
                except Exception as exc:
                    err_msg = None
                    paginated_data = None

            if paginated_data is None and err_msg is None:
                from paginator import get_paginated_records
                paginated_data, err_msg = get_paginated_records(
                    page=page_val,
                    page_size=page_size_val,
                    sort_by=sort_by,
                    sort_order=sort_order,
                )

            if err_msg:
                err_bytes = json.dumps({"code": 400, "message": err_msg}).encode("utf-8")
                self.send_response(400)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(err_bytes)))
                self.end_headers()
                self.wfile.write(err_bytes)
                return

            res_payload = {
                "code": 200,
                "message": "success",
                "data": paginated_data,
            }
            response_bytes = json.dumps(res_payload, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(response_bytes)
            return

        # Parse query options
        # Resource selector: tasks, leaderboard, fixtures, golden_results
        resource = query_params.get("resource", [""])[0].lower()
        if not resource:
            if "leaderboard" in path:
                resource = "leaderboard"
            elif "tasks" in path:
                resource = "tasks"
            elif "fixtures" in path:
                resource = "fixtures"
            else:
                resource = query_params.get("dataset", [query_params.get("type", ["tasks"])[0]])[0].lower()

        table_name = query_params.get("table", [query_params.get("name", [""])[0]])[0]
        fmt = query_params.get("format", ["json"])[0].lower()

        # If direct CSV requested
        if fmt == "csv":
            if resource in ("aws_1m", "1m", "multi_region", "aws_usage_1m"):
                csv_file = os.path.join(DATA_DIR, "aws_1m_sample.csv")
            elif resource in ("aws_daily", "real_aws_daily", "costs", "usage"):
                csv_file = os.path.join(DATA_DIR, "real_aws_usage_daily.csv")
            elif resource == "leaderboard":
                csv_file = os.path.join(DATA_DIR, "benchmark_leaderboard.csv")
            elif resource == "fixtures" and table_name:
                csv_file = os.path.join(FIXTURES_DIR, f"{table_name}.csv")
            else:
                csv_file = os.path.join(DATA_DIR, "benchmark_tasks.csv")

            if os.path.exists(csv_file):
                self.send_response(200)
                self._set_cors_headers()
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'inline; filename="{os.path.basename(csv_file)}"')
                self.end_headers()
                with open(csv_file, "rb") as f:
                    self.wfile.write(f.read())
                return

        # Fetch records
        records = load_dataset(resource, table_name)
        total = len(records)

        # Pagination per Alibaba Quick BI spec (pageNum, pageSize, default size 50, max 1000)
        try:
            page_num = max(1, int(query_params.get("pageNum", query_params.get("page", [1]))[0]))
        except ValueError:
            page_num = 1

        try:
            page_size = min(1000, max(1, int(query_params.get("pageSize", query_params.get("size", query_params.get("limit", [1000])))[0])))
        except ValueError:
            page_size = 1000

        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        paged_records = records[start_idx:end_idx]

        # Alibaba Cloud Quick BI standard Custom API response schema
        payload = {
            "code": 200,
            "message": "success",
            "data": {
                "total": total,
                "pageSize": page_size,
                "pageNum": page_num,
                "resource": resource,
                "records": paged_records
            }
        }

        response_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(response_bytes)


def run_server(port: int = 8088, host: str = "0.0.0.0"):
    server_address = (host, port)
    httpd = HTTPServer(server_address, AlibabaCloudDataAPIHandler)
    print(f"============================================================")
    print(f" SQL-Frontier-Eval: Alibaba Cloud Quick BI Data API Service")
    print(f"============================================================")
    print(f" Listening on:        http://{host}:{port}/")
    print(f" Quick BI Endpoint:   http://{host}:{port}/ai/resource")
    print(f" API Resource:        http://{host}:{port}/api/resource")
    print(f" Tasks Endpoint:      http://{host}:{port}/api/tasks")
    print(f" Leaderboard API:     http://{host}:{port}/api/leaderboard")
    print(f" Allowed CORS Origin: https://bi-us-east-1.alibabacloud.com")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alibaba Cloud Quick BI compatible data API server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8088)), help="Port to listen on (default: 8088)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    args = parser.parse_args()
    run_server(port=args.port, host=args.host)
