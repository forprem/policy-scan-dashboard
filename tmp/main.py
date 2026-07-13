from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from typing import Any

from scanner import validate_site
from repo_scanner.engine import scan_repo
from repo_scanner.git_utils import clone_repo
from ai_explainer import explain_issue, remediate_finding

import shutil

app = FastAPI()
REMEDIATE_MAX_PARALLEL = int(os.getenv("REMEDIATE_MAX_PARALLEL", "4"))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- MODELS --------

class ScanRequest(BaseModel):
    url: str

class RepoScanRequest(BaseModel):
    repo: str
    pat: str | None = None


class RemediateRequest(BaseModel):
    file: str | None = None
    line_number: int | str | None = None
    severity: str | None = None
    rule: str | None = None
    rule_id: str | None = None
    line_content: str | None = None
    message: str | None = None


class RemediateBatchRequest(BaseModel):
    findings: list[RemediateRequest]
    max_parallel: int | None = None


def _normalize_remediate_finding(finding: dict[str, Any]) -> dict[str, Any]:
    line_number = finding.get("line_number")
    try:
        normalized_line_number = int(line_number) if line_number is not None else 0
    except (TypeError, ValueError):
        normalized_line_number = 0

    line_content = finding.get("line_content")
    if not line_content:
        line_content = finding.get("message")

    return {
        "file": finding.get("file") or "unknown",
        "line_number": normalized_line_number,
        "severity": finding.get("severity") or "UNKNOWN",
        "rule": finding.get("rule") or finding.get("rule_id") or "unknown-rule",
        "line_content": line_content or "",
    }


# -------- WEBSITE SCAN --------

@app.post("/scan")
def scan_site(request: ScanRequest):
    return validate_site(request.url)


# -------- REPO SCAN --------

@app.post("/scan-repo")
def scan_repository(request: RepoScanRequest):
    temp_dir = None

    try:
        if request.repo.startswith("http"):
            temp_dir = clone_repo(request.repo, request.pat)
            result = scan_repo(temp_dir)
        else:
            result = scan_repo(request.repo)

        return result

    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

# --------- AI EXPLAINER ---------

@app.post("/explain")
def explain(issue: dict):

    result = explain_issue(issue)

    if isinstance(result, dict) and "explanation" in result:
        return result

    return {
        "explanation": result
    }


@app.post("/remediate")
def remediate(request: RemediateRequest):
    normalized = _normalize_remediate_finding(request.model_dump())
    result = remediate_finding(normalized)
    return result


@app.post("/remediate/batch")
def remediate_batch(request: RemediateBatchRequest):
    if not request.findings:
        return {
            "status": "ok",
            "total": 0,
            "parallelism_used": 0,
            "results": [],
        }

    requested_parallel = request.max_parallel or REMEDIATE_MAX_PARALLEL
    parallelism = max(1, min(requested_parallel, 16))
    findings = [_normalize_remediate_finding(item.model_dump()) for item in request.findings]
    results: list[dict] = [None] * len(findings)

    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        future_to_index = {
            executor.submit(remediate_finding, finding): index
            for index, finding in enumerate(findings)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                finding = findings[index]
                results[index] = {
                    "explanation": "Could not generate AI remediation right now.",
                    "remediation_steps": ["Retry this finding or review manually."],
                    "fixed_code": finding.get("line_content"),
                    "risk_summary": f"Rule {finding.get('rule', 'unknown-rule')} may expose risk if unresolved.",
                    "status": "error",
                    "error": str(exc),
                }

    return {
        "status": "ok",
        "total": len(results),
        "parallelism_used": parallelism,
        "results": results,
    }