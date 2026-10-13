import pytest
from harness.llm import OpenRouterClient

def test_extract_sql_standard():
    raw = """Here is the SQL query to solve your request:
```sql
SELECT
    merchant_id,
    SUM(base_amount) AS total_gross_sales
FROM merchants
GROUP BY merchant_id;
```
Hope this helps!"""
    extracted = OpenRouterClient.extract_sql_from_response(raw)
    assert extracted.startswith("SELECT")
    assert extracted.endswith(";")
    assert "Hope this helps" not in extracted

def test_extract_sql_generic_fence():
    raw = """```
SELECT 1 AS test;
```"""
    extracted = OpenRouterClient.extract_sql_from_response(raw)
    assert extracted == "SELECT 1 AS test;"

def test_extract_sql_no_fence():
    raw = "SELECT merchant_id FROM merchants;"
    extracted = OpenRouterClient.extract_sql_from_response(raw)
    assert extracted == "SELECT merchant_id FROM merchants;"

def test_extract_sql_empty():
    assert OpenRouterClient.extract_sql_from_response("") == ""
    assert OpenRouterClient.extract_sql_from_response(None) == ""
