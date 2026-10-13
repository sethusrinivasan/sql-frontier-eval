import os
import re
import time
from typing import Optional, Tuple, Dict, Any
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert Principal Analytics Engineer writing high-performance, semantically correct SQL for analytical databases (DuckDB dialect).

Your tasks require solving complex analytical queries while avoiding silent correctness traps (such as multi-table join fan-out, metric inflation, chasm traps, temporal mismatch, and null semantics) and computational anti-patterns (such as Cartesian cross products and quadratic self-joins).

RULES:
1. Return ONLY the executable SQL query inside a single ```sql code block.
2. Do NOT provide conversational explanations or markdown outside the ```sql block.
3. Ensure all requested output column aliases and ordering strictly match the prompt specifications.
4. Favor standard analytical functions (CTEs, Window Functions, aggregation before joins) over inefficient nested joins.
"""

class OpenRouterClient:
    """
    OpenRouter API client for evaluating Frontier and Open-Weight models on analytical SQL.
    """
    def __init__(self, api_key: Optional[str] = None, site_url: str = "https://github.com/sql-frontier-eval", app_name: str = "SQL Frontier Eval"):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.site_url = site_url
        self.app_name = app_name
        self.client = None

        if self.api_key:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name
                }
            )

    @staticmethod
    def extract_sql_from_response(raw_text: str) -> str:
        """
        Extracts SQL query from markdown code block or plain text.
        """
        if not raw_text:
            return ""

        # Match ```sql ... ``` (case insensitive)
        sql_block_match = re.search(r"```sql\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
        if sql_block_match:
            return sql_block_match.group(1).strip()

        # Fallback to generic ``` ... ```
        generic_block_match = re.search(r"```\s*([\s\S]*?)\s*```", raw_text)
        if generic_block_match:
            return generic_block_match.group(1).strip()

        # If no code block, strip leading/trailing whitespace
        return raw_text.strip()

    def generate_sql(
        self,
        task_prompt: str,
        setup_sql: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.0,
        timeout: int = 45
    ) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """
        Submits prompt to OpenRouter model and returns:
        (extracted_sql, error_message, metadata)
        """
        if not self.client:
            return None, "OPENROUTER_API_KEY is not configured in environment or client", {}

        user_content = f"""### DATABASE SCHEMA & FIXTURES:
```sql
{setup_sql.strip()}
```

### ANALYTICAL REQUIREMENT:
{task_prompt.strip()}

### INSTRUCTIONS:
Write a single SQL query solving the analytical requirement. Output the query inside a ```sql code block."""

        start_time = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                timeout=timeout
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            choice = response.choices[0]
            raw_content = choice.message.content or ""
            extracted_sql = self.extract_sql_from_response(raw_content)

            usage = response.usage
            metadata = {
                "model": model,
                "latency_ms": elapsed_ms,
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
                "raw_response": raw_content
            }

            return extracted_sql, None, metadata

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return None, str(e), {"latency_ms": elapsed_ms, "model": model}
