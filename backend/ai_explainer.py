import logging
import json
import os
import re
from threading import Lock
from time import perf_counter
from typing import Any

import requests

try:
    import ollama
except ImportError:
    ollama = None

# ========== CONFIGURATION ==========

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "320"))
GROQ_TIMEOUT = int(os.getenv("GROQ_TIMEOUT", "60"))
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")

# Ollama fallback configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# Remediation configuration
REMEDIATE_MAX_TOKENS = int(os.getenv("REMEDIATE_MAX_TOKENS", "400"))
REMEDIATE_TEMPERATURE = float(os.getenv("REMEDIATE_TEMPERATURE", "0.2"))
REMEDIATE_TIMEOUT = int(os.getenv("REMEDIATE_TIMEOUT", "60"))

logger = logging.getLogger(__name__)

# ========== THREAD-SAFE COUNTERS ==========

_lock = Lock()
_explain_request_count = 0
_remediate_request_count = 0

# Success/Failure statistics
_explain_success_count = 0
_explain_failure_count = 0
_remediate_success_count = 0
_remediate_failure_count = 0


def _next_explain_request_count() -> int:
    global _explain_request_count
    with _lock:
        _explain_request_count += 1
        return _explain_request_count


def _next_remediate_request_count() -> int:
    global _remediate_request_count
    with _lock:
        _remediate_request_count += 1
        return _remediate_request_count


def _record_explain_success():
    global _explain_success_count
    with _lock:
        _explain_success_count += 1


def _record_explain_failure():
    global _explain_failure_count
    with _lock:
        _explain_failure_count += 1


def _record_remediate_success():
    global _remediate_success_count
    with _lock:
        _remediate_success_count += 1


def _record_remediate_failure():
    global _remediate_failure_count
    with _lock:
        _remediate_failure_count += 1


def get_ai_stats() -> dict[str, int]:
    """Return cumulative AI operation statistics for all endpoints."""
    with _lock:
        return {
            "explain_total_requests": _explain_request_count,
            "explain_success": _explain_success_count,
            "explain_failure": _explain_failure_count,
            "remediate_total_requests": _remediate_request_count,
            "remediate_success": _remediate_success_count,
            "remediate_failure": _remediate_failure_count,
        }


# ========== GROQ & OLLAMA CALLS ==========


def _call_groq(prompt: str) -> str:
    """Call Groq API with automatic retry on transient failures."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": GROQ_TEMPERATURE,
                    "max_tokens": GROQ_MAX_TOKENS,
                },
                timeout=GROQ_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            if attempt < max_retries - 1:
                logger.warning(f"Groq attempt {attempt + 1} failed, retrying: {exc}")
                continue
            raise


def _call_ollama(prompt: str) -> str:
    """Call Ollama API with automatic retry on transient failures."""
    if ollama is None:
        raise RuntimeError("ollama package is not installed")

    max_retries = 2
    for attempt in range(max_retries):
        try:
            client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"]
        except Exception as exc:
            if attempt < max_retries - 1:
                logger.warning(f"Ollama attempt {attempt + 1} failed, retrying: {exc}")
                continue
            raise


# ========== EXPLAIN ISSUE (Button 1) ==========


def explain_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """
    Explain a security issue using Groq (primary) with Ollama fallback.
    
    Returns a dict with:
      - explanation: human-readable explanation
      - metrics: timing, attempt count, provider info, success flag
      - provider_used: which provider succeeded (groq/ollama/none)
    """
    request_count = _next_explain_request_count()
    start_time = perf_counter()
    attempt_count = 0
    file_path = issue.get("file", "unknown")
    rule_id = issue.get("rule_id", "unknown")
    provider_used = None

    prompt = f"""You are a cybersecurity expert.

Explain this security issue in simple language.

File:
{file_path}

Rule ID:
{rule_id}

Severity:
{issue.get("severity", "UNKNOWN")}

Issue:
{issue.get("message", "")}

Code:
{issue.get("line_content", "")}

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

    explanation = None
    error_message = None

    # Try Groq first
    attempt_count = 1
    try:
        explanation = _call_groq(prompt)
        provider_used = "groq"
        _record_explain_success()
    except Exception as exc:
        error_message = str(exc)
        logger.warning(f"Groq call failed for req {request_count}: {exc}")

        # Try Ollama fallback
        attempt_count = 2
        try:
            explanation = _call_ollama(prompt)
            provider_used = "ollama"
            _record_explain_success()
        except Exception as ollama_exc:
            error_message = f"Groq failed: {exc}; Ollama fallback failed: {ollama_exc}"
            logger.error(f"Both Groq and Ollama failed for req {request_count}: {error_message}")
            _record_explain_failure()

    elapsed_seconds = perf_counter() - start_time
    elapsed_ms = round(elapsed_seconds * 1000, 2)

    # Return response
    if explanation:
        logger.info(
            f"Explain success | req={request_count} attempts={attempt_count} provider={provider_used} "
            f"time_ms={elapsed_ms} file={file_path} rule={rule_id}"
        )
        return {
            "explanation": explanation,
            "provider_used": provider_used,
            "success": True,
            "metrics": {
                "request_count": request_count,
                "attempt_count": attempt_count,
                "elapsed_ms": elapsed_ms,
                "elapsed_seconds": round(elapsed_seconds, 3),
                "provider": provider_used,
                "model": GROQ_MODEL if provider_used == "groq" else OLLAMA_MODEL,
                "prompt_chars": len(prompt),
                "response_chars": len(explanation),
            },
        }
    else:
        logger.error(
            f"Explain failed | req={request_count} attempts={attempt_count} "
            f"time_ms={elapsed_ms} file={file_path} rule={rule_id} error={error_message}"
        )
        return {
            "explanation": "AI explanation is currently unavailable. Please try again in a few moments.",
            "provider_used": None,
            "success": False,
            "error": error_message,
            "metrics": {
                "request_count": request_count,
                "attempt_count": attempt_count,
                "elapsed_ms": elapsed_ms,
                "elapsed_seconds": round(elapsed_seconds, 3),
                "provider": None,
                "prompt_chars": len(prompt),
                "response_chars": 0,
            },
        }


# ========== REMEDIATE FINDING (Buttons 2 & 3) ==========


def _extract_first_json_object(raw_text: str) -> dict[str, Any] | None:
    """Extract JSON object from potentially noisy model output."""
    if not raw_text:
        return None

    text = raw_text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Attempt to recover a JSON object from model wrappers/noise
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    candidate = re.sub(r"^```(?:json)?\n|\n```$", "", candidate.strip(), flags=re.IGNORECASE)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def _fallback_remediation(finding: dict[str, Any], error_message: str) -> dict[str, Any]:
    """Return a safe fallback remediation when AI calls fail."""
    safe_line = (finding.get("line_content") or "").strip()
    safe_rule = finding.get("rule") or "unknown-rule"
    return {
        "explanation": "Could not generate AI remediation at this time. Applying fallback guidance.",
        "remediation_steps": [
            "Review the impacted line and surrounding context for the violation.",
            "Replace the insecure pattern with a validated, parameterized, or safe alternative.",
            "Add input validation and apply secure defaults where applicable.",
            "Re-run security scan and unit tests after making changes.",
        ],
        "fixed_code": safe_line if safe_line else None,
        "risk_summary": f"Rule {safe_rule} may expose a security risk if left unresolved.",
        "status": "error",
        "error": error_message,
        "success": False,
    }


def remediate_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """
    Generate remediation guidance for a security finding using Groq (primary) with Ollama fallback.
    
    Used by /remediate (Button 2 - single finding) and /remediate/batch (Button 3 - multiple findings).
    
    Returns a dict with:
      - explanation: remediation explanation
      - remediation_steps: ordered list of steps
      - fixed_code: suggested code fix (optional)
      - risk_summary: summary of the risk
      - status: "ok" or "error"
      - success: boolean
      - provider_used: which provider succeeded (groq/ollama/none)
      - metrics: timing and attempt info
    """
    request_count = _next_remediate_request_count()
    start_time = perf_counter()
    attempt_count = 0
    file_path = finding.get("file", "unknown")
    rule_value = finding.get("rule") or finding.get("rule_id", "unknown-rule")
    provider_used = None

    prompt = f"""You are a secure coding remediation expert.

Return ONLY valid JSON with this exact schema and keys:
{{
  "explanation": "string",
  "remediation_steps": ["string", "string"],
  "fixed_code": "string or null",
  "risk_summary": "string or null"
}}

Rules:
- Output must be JSON only. No markdown. No extra keys.
- Keep explanation concise and specific to the impacted line.
- remediation_steps must be practical and ordered.
- fixed_code should be a short secure replacement snippet for the impacted line when possible.
- If file appears to be Java, return Java code style snippet. If Terraform, return HCL style. Match language from file extension.

Security Finding:
file: {file_path}
line_number: {finding.get("line_number", 0)}
severity: {finding.get("severity", "UNKNOWN")}
rule: {rule_value}
line_content: {finding.get("line_content", "")}
"""

    result = None
    error_message = None

    # Try Groq first
    attempt_count = 1
    try:
        response_text = _call_groq(prompt)
        parsed = _extract_first_json_object(response_text)
        if parsed:
            result = parsed
            provider_used = "groq"
            _record_remediate_success()
        else:
            logger.warning(f"Groq returned non-JSON for req {request_count}")
            error_message = "Groq response was not valid JSON"
    except Exception as exc:
        error_message = str(exc)
        logger.warning(f"Groq call failed for req {request_count}: {exc}")

        # Try Ollama fallback
        attempt_count = 2
        try:
            response_text = _call_ollama(prompt)
            parsed = _extract_first_json_object(response_text)
            if parsed:
                result = parsed
                provider_used = "ollama"
                _record_remediate_success()
            else:
                logger.warning(f"Ollama returned non-JSON for req {request_count}")
                error_message = f"Groq failed: {exc}; Ollama returned non-JSON"
        except Exception as ollama_exc:
            error_message = f"Groq failed: {exc}; Ollama failed: {ollama_exc}"
            logger.error(f"Both Groq and Ollama failed for req {request_count}: {error_message}")
            _record_remediate_failure()

    elapsed_seconds = perf_counter() - start_time
    elapsed_ms = round(elapsed_seconds * 1000, 2)

    # If we got a result, normalize and return it
    if result:
        remediation_steps = result.get("remediation_steps", [])
        if isinstance(remediation_steps, str):
            remediation_steps = [step.strip() for step in remediation_steps.split("\n") if step.strip()]
        if not isinstance(remediation_steps, list):
            remediation_steps = []

        normalized = {
            "explanation": str(result.get("explanation") or "Remediation guidance provided."),
            "remediation_steps": [str(step) for step in remediation_steps],
            "fixed_code": result.get("fixed_code") if result.get("fixed_code") else None,
            "risk_summary": result.get("risk_summary") if result.get("risk_summary") else None,
            "status": "ok",
            "error": None,
            "success": True,
            "provider_used": provider_used,
            "metrics": {
                "request_count": request_count,
                "attempt_count": attempt_count,
                "elapsed_ms": elapsed_ms,
                "elapsed_seconds": round(elapsed_seconds, 3),
                "provider": provider_used,
                "model": GROQ_MODEL if provider_used == "groq" else OLLAMA_MODEL,
            },
        }

        logger.info(
            f"Remediate success | req={request_count} attempts={attempt_count} provider={provider_used} "
            f"time_ms={elapsed_ms} file={file_path} rule={rule_value}"
        )
        return normalized

    # If all attempts failed, return fallback
    logger.error(
        f"Remediate failed | req={request_count} attempts={attempt_count} "
        f"time_ms={elapsed_ms} file={file_path} rule={rule_value} error={error_message}"
    )
    fallback = _fallback_remediation(finding, error_message or "Unknown error")
    fallback["metrics"] = {
        "request_count": request_count,
        "attempt_count": attempt_count,
        "elapsed_ms": elapsed_ms,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "provider": None,
    }
    return fallback
