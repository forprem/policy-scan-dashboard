import logging
import json
import os
import re
import socket
from threading import Lock
from time import perf_counter
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
import ollama

OLLAMA_OFFICE_IP = "88.88.88.88"
OLLAMA_HOME_IP = "192.168.1.172"
OLLAMA_PORT = 11434
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "320"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
OLLAMA_HTTP_TIMEOUT = float(os.getenv("OLLAMA_HTTP_TIMEOUT", "45"))
REMEDIATE_NUM_PREDICT = int(os.getenv("REMEDIATE_NUM_PREDICT", "420"))
REMEDIATE_TEMPERATURE = float(os.getenv("REMEDIATE_TEMPERATURE", "0.1"))

logger = logging.getLogger(__name__)
_count_lock = Lock()
_client_lock = Lock()
_explain_request_count = 0


def _next_request_count() -> int:
    global _explain_request_count
    with _count_lock:
        _explain_request_count += 1
        return _explain_request_count

def _detect_ollama_host() -> str:
    """Pick the first host that responds to Ollama API, not just open TCP."""
    env_host = os.getenv("OLLAMA_HOST", "").strip()
    candidates = []
    if env_host:
        candidates.append(env_host if env_host.startswith("http") else f"http://{env_host}")
    candidates.extend(
        [
            f"http://{OLLAMA_OFFICE_IP}:{OLLAMA_PORT}",
            f"http://{OLLAMA_HOME_IP}:{OLLAMA_PORT}",
            f"http://localhost:{OLLAMA_PORT}",
        ]
    )

    for base_url in candidates:
        try:
            # Validate Ollama endpoint instead of checking only port-level reachability.
            with urlopen(f"{base_url}/api/tags", timeout=3):
                return base_url
        except (URLError, OSError, ValueError):
            continue

    # Fall back to localhost so caller still has a deterministic endpoint.
    return f"http://localhost:{OLLAMA_PORT}"


def _is_retryable_ollama_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    retryable_keywords = [
        "remoteprotocolerror",
        "server disconnected",
        "connect",
        "timeout",
        "temporarily unavailable",
    ]
    return isinstance(exc, ConnectionError) or any(keyword in msg for keyword in retryable_keywords)


def _build_client() -> tuple[ollama.Client, str]:
    detected_host = _detect_ollama_host()
    logger.info("Ollama host selected (first 33 chars): %s", detected_host[:33])
    return ollama.Client(host=detected_host, timeout=OLLAMA_HTTP_TIMEOUT), detected_host


client, client_host = _build_client()


def _extract_first_json_object(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None

    text = raw_text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Attempt to recover a JSON object from model wrappers/noise.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    candidate = re.sub(r"^```(?:json)?\\n|\\n```$", "", candidate.strip(), flags=re.IGNORECASE)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def _fallback_remediation(finding: dict[str, Any], error_message: str) -> dict[str, Any]:
    safe_line = (finding.get("line_content") or "").strip()
    safe_rule = finding.get("rule") or finding.get("rule_id") or "unknown-rule"
    return {
        "explanation": "Could not generate AI remediation right now. Apply secure coding best practices for the flagged line and review manually.",
        "remediation_steps": [
            "Review the impacted line and surrounding context.",
            "Replace insecure pattern with validated/parameterized secure alternative.",
            "Add input validation and safe defaults.",
            "Re-run scan and unit tests after changes.",
        ],
        "fixed_code": safe_line or None,
        "risk_summary": f"Rule {safe_rule} may expose security risk if left unresolved.",
        "status": "error",
        "error": error_message,
    }


def remediate_finding(finding: dict[str, Any]) -> dict[str, Any]:
    start_time = perf_counter()
    attempt_count = 1
    file_path = finding.get("file")
    rule_value = finding.get("rule") or finding.get("rule_id")

    prompt = f"""
You are a secure coding remediation assistant.

Return ONLY valid JSON with this exact schema and keys:
{{
  "explanation": "string",
  "remediation_steps": ["string", "string"],
  "fixed_code": "string or null",
  "risk_summary": "string or null",
  "status": "ok",
  "error": null
}}

Rules:
- Output must be JSON only. No markdown. No extra keys.
- Keep explanation concise and specific to the impacted line.
- remediation_steps must be practical and ordered.
- fixed_code should be a short secure replacement snippet for the impacted line when possible.
- If file appears to be Java, return Java code style snippet. If Terraform, return HCL style. Match language from file extension.

Finding:
file: {file_path}
line_number: {finding.get("line_number")}
severity: {finding.get("severity")}
rule: {rule_value}
line_content: {finding.get("line_content")}
"""

    global client, client_host
    active_host = client_host

    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "num_predict": REMEDIATE_NUM_PREDICT,
                "temperature": REMEDIATE_TEMPERATURE,
            },
        )
    except Exception as exc:
        if not _is_retryable_ollama_error(exc):
            elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Remediate failed | host=%s model=%s time_ms=%s rule=%s file=%s err=%s",
                active_host[:33],
                OLLAMA_MODEL,
                elapsed_ms,
                rule_value,
                file_path,
                str(exc),
            )
            return _fallback_remediation(finding, f"Ollama request failed: {exc}")

        logger.warning("Remediate connection/protocol failed. Re-detecting host and retrying once.")
        attempt_count = 2
        with _client_lock:
            client, client_host = _build_client()
            active_host = client_host
        try:
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                options={
                    "num_predict": REMEDIATE_NUM_PREDICT,
                    "temperature": REMEDIATE_TEMPERATURE,
                },
            )
        except Exception as exc:
            elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Remediate failed after retry | host=%s model=%s time_ms=%s rule=%s file=%s err=%s",
                active_host[:33],
                OLLAMA_MODEL,
                elapsed_ms,
                rule_value,
                file_path,
                str(exc),
            )
            return _fallback_remediation(finding, f"Ollama connection failed: {exc}")
    raw_text = response.get("message", {}).get("content", "")
    parsed = _extract_first_json_object(raw_text)

    if not parsed:
        elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
        logger.warning(
            "Remediate returned non-JSON output | host=%s model=%s time_ms=%s attempts=%s rule=%s file=%s",
            active_host[:33],
            OLLAMA_MODEL,
            elapsed_ms,
            attempt_count,
            rule_value,
            file_path,
        )
        return _fallback_remediation(finding, "Model output could not be parsed as JSON.")

    remediation_steps = parsed.get("remediation_steps")
    if isinstance(remediation_steps, str):
        remediation_steps = [step.strip() for step in remediation_steps.split("\n") if step.strip()]
    if not isinstance(remediation_steps, list):
        remediation_steps = []

    normalized = {
        "explanation": str(parsed.get("explanation") or "No explanation provided."),
        "remediation_steps": [str(step) for step in remediation_steps],
        "fixed_code": parsed.get("fixed_code") if parsed.get("fixed_code") else None,
        "risk_summary": parsed.get("risk_summary") if parsed.get("risk_summary") else None,
        "status": "ok",
        "error": None,
    }

    elapsed_ms = round((perf_counter() - start_time) * 1000, 2)
    logger.info(
        "Remediate metrics | attempts=%s model=%s host=%s time_ms=%s rule=%s file=%s",
        attempt_count,
        OLLAMA_MODEL,
        active_host[:33],
        elapsed_ms,
        rule_value,
        file_path,
    )
    return normalized

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

    global client, client_host
    active_host = client_host

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
    except Exception as exc:
        if not _is_retryable_ollama_error(exc):
            elapsed_seconds = perf_counter() - start_time
            elapsed_ms = round(elapsed_seconds * 1000, 2)
            return {
                "explanation": "AI explanation is currently unavailable. Please retry in a few moments.",
                "metrics": {
                    "request_count": request_count,
                    "attempt_count": attempt_count,
                    "elapsed_ms": elapsed_ms,
                    "elapsed_seconds": round(elapsed_seconds, 3),
                    "ollama_host_first33": active_host[:33],
                    "model": OLLAMA_MODEL,
                    "options_used": {
                        "num_predict": OLLAMA_NUM_PREDICT,
                        "temperature": OLLAMA_TEMPERATURE,
                    },
                    "prompt_chars": len(prompt),
                    "response_chars": 0,
                    "status": "error",
                    "error": str(exc),
                },
            }

        # Re-detect host once in case network changed between office/home.
        logger.warning("Ollama connection/protocol failed. Re-detecting host and retrying once.")
        attempt_count = 2
        with _client_lock:
            client, client_host = _build_client()
            active_host = client_host
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
        except Exception as retry_exc:
            elapsed_seconds = perf_counter() - start_time
            elapsed_ms = round(elapsed_seconds * 1000, 2)
            return {
                "explanation": "AI explanation is currently unavailable. Please retry in a few moments.",
                "metrics": {
                    "request_count": request_count,
                    "attempt_count": attempt_count,
                    "elapsed_ms": elapsed_ms,
                    "elapsed_seconds": round(elapsed_seconds, 3),
                    "ollama_host_first33": active_host[:33],
                    "model": OLLAMA_MODEL,
                    "options_used": {
                        "num_predict": OLLAMA_NUM_PREDICT,
                        "temperature": OLLAMA_TEMPERATURE,
                    },
                    "prompt_chars": len(prompt),
                    "response_chars": 0,
                    "status": "error",
                    "error": str(retry_exc),
                },
            }

    explanation = response["message"]["content"]
    elapsed_seconds = perf_counter() - start_time
    elapsed_ms = round(elapsed_seconds * 1000, 2)

    logger.info(
        "Explain metrics | req=%s attempts=%s model=%s host=%s time_ms=%s num_predict=%s temp=%s prompt_chars=%s response_chars=%s file=%s rule_id=%s",
        request_count,
        attempt_count,
        OLLAMA_MODEL,
        active_host[:33],
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
            "ollama_host_first33": active_host[:33],
            "model": OLLAMA_MODEL,
            "options_used": {
                "num_predict": OLLAMA_NUM_PREDICT,
                "temperature": OLLAMA_TEMPERATURE,
            },
            "prompt_chars": len(prompt),
            "response_chars": len(explanation),
        },
    }