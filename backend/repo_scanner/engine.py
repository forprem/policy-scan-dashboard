import os

from .loader import load_rules
from .ansible_scanner import scan_ansible_files
from .python_scanner import scan_python_files


def scan_repo(repo_path):

    findings = []

    # -----------------------------
    # STEP 1: Detect file types
    # -----------------------------
    has_py = False
    has_yaml = False

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                has_py = True
            elif file.endswith((".yml", ".yaml")):
                has_yaml = True

    # -----------------------------
    # STEP 2: Run scanners conditionally
    # -----------------------------

    if has_yaml:
        ansible_rules = load_rules("ansible")
        findings.extend(
            scan_ansible_files(repo_path, ansible_rules)
        )

    if has_py:
        python_rules = load_rules("python")
        findings.extend(
            scan_python_files(repo_path, python_rules)
        )

    return {
        "total_issues": len(findings),
        "findings": findings
    }
