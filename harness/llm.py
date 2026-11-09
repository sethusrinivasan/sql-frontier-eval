import os
import re
import shutil
import subprocess
import time
from typing import Optional, Tuple, Dict, Any, List
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert Principal Analytics Engineer writing high-performance, semantically correct SQL for analytical databases (DuckDB dialect).

Your tasks require solving complex analytical queries while avoiding silent correctness traps (such as multi-table join fan-out, metric inflation, chasm traps, temporal mismatch, and null semantics) and computational anti-patterns (such as Cartesian cross products and quadratic self-joins).

RULES:
1. Return ONLY the executable SQL query inside a single ```sql code block.
2. Do NOT provide conversational explanations or markdown outside the ```sql block.
3. Ensure all requested output column aliases and ordering strictly match the prompt specifications.
4. Favor standard analytical functions (CTEs, Window Functions, aggregation before joins) over inefficient nested joins.
"""

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


class AgyClient:
    """
    Client interface executing queries against Frontier AI models via the Antigravity CLI.
    Supported models include:
      - gemini-3.8-flash-high
      - gemini-3.8-flash-medium
      - gemini-3.8-flash-low
      - claude-sonnet-4-6
      - claude-opus-4-6-thinking
      - gpt-oss-120b-medium
    """
    KNOWN_MODELS = [
        "gemini-3.8-flash-high",
        "gemini-3.8-flash-medium",
        "gemini-3.8-flash-low",
        "claude-sonnet-4-6",
        "claude-opus-4-6-thinking",
        "gpt-oss-120b-medium",
    ]

    def __init__(self, agy_path: Optional[str] = None):
        self.agy_path = (
            agy_path
            or os.environ.get("ANTIGRAVITY_AGENTAPI_EXE")
            or shutil.which("agy")
            or "/home/home/.local/bin/agy"
        )

    def is_available(self) -> bool:
        return bool(self.agy_path and os.path.exists(self.agy_path) and os.access(self.agy_path, os.X_OK))

    def generate_sql(
        self,
        task_prompt: str,
        setup_sql: str,
        model: str = "gemini-3.8-flash-medium",
        timeout: int = 90
    ) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """
        Submits prompt to an authenticated frontier model and returns:
        (extracted_sql, error_message, metadata)
        """
        if not self.is_available():
            return None, f"agy binary not found or not executable at {self.agy_path}", {}

        # Strip prefix if specified as agy/<model>
        clean_model = model.replace("agy/", "")

        user_content = f"""{SYSTEM_PROMPT}

### DATABASE SCHEMA & FIXTURES:
```sql
{setup_sql.strip()}
```

### ANALYTICAL REQUIREMENT:
{task_prompt.strip()}

### INSTRUCTIONS:
Write a single SQL query solving the analytical requirement for DuckDB. Output ONLY the query inside a single ```sql code block."""

        start_time = time.perf_counter()
        try:
            cmd = [
                self.agy_path,
                "--dangerously-skip-permissions",
                "--disable-slash-commands",
                f"--model={clean_model}",
                f"--print={user_content}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if result.returncode != 0:
                err_msg = result.stderr.strip() or f"agy command failed with code {result.returncode}"
                return None, err_msg, {"latency_ms": elapsed_ms, "model": clean_model}

            raw_content = result.stdout.strip()
            extracted_sql = extract_sql_from_response(raw_content)

            metadata = {
                "model": clean_model,
                "latency_ms": elapsed_ms,
                "backend": "agy",
                "raw_response": raw_content
            }
            return extracted_sql, None, metadata

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return None, f"Query generation timed out after {timeout}s", {"latency_ms": elapsed_ms, "model": clean_model}
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return None, str(e), {"latency_ms": elapsed_ms, "model": clean_model}


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
        return extract_sql_from_response(raw_text)

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
            extracted_sql = extract_sql_from_response(raw_content)

            usage = response.usage
            metadata = {
                "model": model,
                "latency_ms": elapsed_ms,
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
                "backend": "openrouter",
                "raw_response": raw_content
            }

            return extracted_sql, None, metadata

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return None, str(e), {"latency_ms": elapsed_ms, "model": model}


def get_llm_client(model: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Factory function returning the appropriate client backend for a given model identifier.
    Returns (client_instance, error_message).
    """
    clean_model = model.replace("agy/", "")

    # Check if model is supported by AgyClient
    agy_client = AgyClient()
    if clean_model in AgyClient.KNOWN_MODELS or model.startswith("agy/"):
        if agy_client.is_available():
            return agy_client, None
        return None, f"Antigravity CLI (agy) is not available to run model '{model}'"

    # Otherwise check OpenRouter
    openrouter_client = OpenRouterClient()
    if openrouter_client.api_key:
        return openrouter_client, None

    # Fallback to agy if available
    if agy_client.is_available():
        return agy_client, None

    return None, f"No provider configured for model '{model}'. Set OPENROUTER_API_KEY or install agy CLI."
