import os
import threading
import time
import requests
import pytest
from serve_data_api import run_server, AlibabaCloudDataAPIHandler
from http.server import HTTPServer

TEST_PORT = 18088

@pytest.fixture(scope="module")
def api_server():
    server = HTTPServer(("127.0.0.1", TEST_PORT), AlibabaCloudDataAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    yield f"http://127.0.0.1:{TEST_PORT}"
    server.shutdown()
    server.server_close()

def test_cors_preflight(api_server):
    headers = {
        "Origin": "https://bi-us-east-1.alibabacloud.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    resp = requests.options(f"{api_server}/ai/resource", headers=headers)
    assert resp.status_code == 204
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://bi-us-east-1.alibabacloud.com"
    assert "POST" in resp.headers.get("Access-Control-Allow-Methods", "")

def test_alibaba_quick_bi_endpoint_format(api_server):
    headers = {
        "Origin": "https://bi-us-east-1.alibabacloud.com",
        "Accept": "application/json"
    }
    resp = requests.get(f"{api_server}/ai/resource", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://bi-us-east-1.alibabacloud.com"

    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    assert "data" in body
    assert body["data"]["total"] == 120
    assert isinstance(body["data"]["records"], list)
    assert len(body["data"]["records"]) > 0

    first_record = body["data"]["records"][0]
    assert "task_id" in first_record
    assert "name" in first_record
    assert "category" in first_record

def test_leaderboard_endpoint(api_server):
    resp = requests.get(f"{api_server}/api/leaderboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["total"] > 0
    records = body["data"]["records"]
    models = [r["model"] for r in records]
    assert any("Claude Opus" in m for m in models)
    assert any("Gemini 3.8 Flash" in m for m in models)

def test_fixtures_and_csv_format(api_server):
    resp_fixtures = requests.get(f"{api_server}/ai/resource?resource=fixtures")
    assert resp_fixtures.status_code == 200
    body = resp_fixtures.json()
    assert body["data"]["total"] >= 140

    resp_csv = requests.get(f"{api_server}/ai/resource?resource=tasks&format=csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers.get("Content-Type", "")
    assert "task_id" in resp_csv.text

def test_csv_files_exist_on_disk():
    assert os.path.exists("data/benchmark_leaderboard.csv")
    assert os.path.exists("data/benchmark_tasks.csv")
    assert os.path.isdir("data/fixtures")
    assert os.path.isdir("data/golden_results")
    assert len(os.listdir("data/fixtures")) >= 140
    assert len(os.listdir("data/golden_results")) == 120

def test_paginated_endpoint_spec(api_server):
    headers = {"Origin": "https://bi-us-east-1.alibabacloud.com"}
    resp = requests.get(f"{api_server}/ai/resource/paginated?page=1&pageSize=1000", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://bi-us-east-1.alibabacloud.com"

    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    data = body["data"]
    assert data["total"] == 1_000_000
    assert data["page"] == 1
    assert data["pageSize"] == 1000
    assert data["totalPages"] == 1000
    assert data["hasNext"] is True
    assert data["hasPrev"] is False
    assert len(data["records"]) == 1000

    rec = data["records"][0]
    assert "date" in rec
    assert "gross_usd" in rec
    assert "color_class" in rec
    assert "status_label" in rec
    assert "top_5_services" in rec
    assert "raw_services" in rec
    assert isinstance(rec["top_5_services"], list)
    assert len(rec["top_5_services"]) <= 5
    for s in rec["top_5_services"]:
        assert "service" in s
        assert "acronym" in s
        assert "amount" in s
        assert "percent" in s
        assert "short_display" in s

def test_paginated_edge_cases(api_server):
    # Page beyond totalPages
    resp = requests.get(f"{api_server}/ai/resource/paginated?page=1001&pageSize=1000")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["records"] == []
    assert data["pageSize"] == 0
    assert data["hasNext"] is False

    # PageSize > 10000 capped
    resp = requests.get(f"{api_server}/ai/resource/paginated?page=1&pageSize=20000")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["pageSize"] == 10000
    assert len(data["records"]) == 10000

    # PageSize <= 0 returns error 400
    resp = requests.get(f"{api_server}/ai/resource/paginated?page=1&pageSize=0")
    assert resp.status_code == 400
    body = resp.json()
    assert body["message"] == "pageSize must be >= 1"

    # Invalid sort_by returns error 400
    resp = requests.get(f"{api_server}/ai/resource/paginated?sort_by=invalid_field")
    assert resp.status_code == 400
    body = resp.json()
    assert "Unknown sort field: invalid_field" in body["message"]

