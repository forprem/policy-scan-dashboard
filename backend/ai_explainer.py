import logging
import os
import socket
from threading import Lock
from time import perf_counter
import ollama

OLLAMA_OFFICE_IP = "100.26.10.88"
OLLAMA_HOME_IP = "192.168.1.172"
OLLAMA_PORT = 11434
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "320"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

logger = logging.getLogger(__name__)
_count_lock = Lock()
_explain_request_count = 0
current_host = ""


def _next_request_count() -> int:
    global _explain_request_count
    with _count_lock:
        _explain_request_count += 1
        return _explain_request_count

def _detect_ollama_host() -> str:
    """Try office IP first; fall back to home IP based on reachability."""
    for ip in (OLLAMA_OFFICE_IP, OLLAMA_HOME_IP):
        try:
            with socket.create_connection((ip, OLLAMA_PORT), timeout=2):
                return f"http://{ip}:{OLLAMA_PORT}"
        except OSError:
            continue
    # Last resort: localhost
    return f"http://localhost:{OLLAMA_PORT}"


def _build_client() -> ollama.Client:
    global current_host
    current_host = _detect_ollama_host()
    logger.info("Ollama host selected (first 33 chars): %s", current_host[:33])
    return ollama.Client(host=current_host)


client = _build_client()

def explain_issue(issue):
    request_count = _next_request_count()
    start_time = perf_counter()
    attempt_count = 1
    file_path = issue.get("file")

    prompt = f"""
You are a cybersecurity expert.

Explain this Ansible or Python security issue in simple language.

File:
{file_path}

Rule ID:
{issue.get("rule_id")}

Severity:
{issue.get("severity")}

Issue:
{issue.get("message")}

Code:
{issue.get("line_content")}

Please explain:
1. Why this is dangerous
2. Real-world attack scenario
3. Secure alternative
4. Best practice
5. A sample code snippet fix for THIS exact line and file type

Response format rules:
- Be concise. Total response should be under 220 words.
- Keep each numbered section to 2-4 short bullet points.
- For item 5, return only one short snippet.
- Do not use markdown code fences in item 5.
- Return snippet as plain code lines only.

Snippet rules:
- Infer file type from the File path extension and the Code line.
- If file path ends with .java, return a Java snippet and include concise Java-style comments (//).
- Match the snippet language to the inferred file type when possible.
- Keep snippet short and practical (5-12 lines).
- The snippet must directly address the flagged code line.
"""

    global client

    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "num_predict": OLLAMA_NUM_PREDICT,
                "temperature": OLLAMA_TEMPERATURE,
            }
        )
    except ConnectionError:
        # Re-detect host once in case network changed between office/home.
        logger.warning("Ollama connection failed. Re-detecting host and retrying once.")
        attempt_count = 2
        client = _build_client()
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "num_predict": OLLAMA_NUM_PREDICT,
                "temperature": OLLAMA_TEMPERATURE,
            }
        )

    explanation = response["message"]["content"]
    elapsed_seconds = perf_counter() - start_time
    elapsed_ms = round(elapsed_seconds * 1000, 2)

    logger.info(
        "Explain metrics | req=%s attempts=%s model=%s host=%s time_ms=%s num_predict=%s temp=%s prompt_chars=%s response_chars=%s file=%s rule_id=%s",
        request_count,
        attempt_count,
        OLLAMA_MODEL,
        current_host[:33],
        elapsed_ms,
        OLLAMA_NUM_PREDICT,
        OLLAMA_TEMPERATURE,
        len(prompt),
        len(explanation),
        file_path,
        issue.get("rule_id"),
    )

    return {
        "explanation": explanation,
        "metrics": {
            "request_count": request_count,
            "attempt_count": attempt_count,
            "elapsed_ms": elapsed_ms,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "ollama_host_first33": current_host[:33],
            "model": OLLAMA_MODEL,
            "options_used": {
                "num_predict": OLLAMA_NUM_PREDICT,
                "temperature": OLLAMA_TEMPERATURE,
            },
            "prompt_chars": len(prompt),
            "response_chars": len(explanation),
        },
    }
