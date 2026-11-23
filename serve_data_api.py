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
    if resource == "leaderboard":
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
        # Supports /ai/resource, /api/resource, /api/data, /api/tasks, /api/leaderboard, etc.
        valid_endpoints = [
            "/ai/resource",
            "/api/resource",
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
                "message": f"Endpoint {path} not found. Valid endpoints include /ai/resource, /api/resource, /api/data",
                "data": None
            }).encode("utf-8"))
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
            if resource == "leaderboard":
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
