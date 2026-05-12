from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scanner import validate_site
from repo_scanner.engine import scan_repo
from repo_scanner.git_utils import clone_repo
from ai_explainer import explain_issue

import shutil

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://policy-scan-dashboard.*prem-prakashs-projects.*\.vercel\.app",
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

    explanation = explain_issue(issue)

    return {
        "explanation": explanation
    }
