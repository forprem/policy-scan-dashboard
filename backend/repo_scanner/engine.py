import os

from .loader import load_rules
from .ansible_scanner import scan_ansible_files
from .python_scanner import scan_python_files
from .java_scanner import scan_java_files
from .javascript_scanner import scan_javascript_files
from .terraform_scanner import scan_terraform_files


SCANNER_REGISTRY = {
    "ansible": {
        "extensions": (".yml", ".yaml"),
        "scanner": scan_ansible_files,
    },
    "python": {
        "extensions": (".py",),
        "scanner": scan_python_files,
    },
    "java": {
        "extensions": (".java",),
        "scanner": scan_java_files,
    },
    "javascript": {
        "extensions": (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"),
        "scanner": scan_javascript_files,
    },
    "terraform": {
        "extensions": (".tf", ".tfvars"),
        "scanner": scan_terraform_files,
    },
}


def scan_repo(repo_path):

    findings = []
    detected_languages = set()

    # -----------------------------
    # STEP 1: Detect file types
    # -----------------------------
    for root, _, files in os.walk(repo_path):
        for file in files:
            for language, config in SCANNER_REGISTRY.items():
                if file.endswith(config["extensions"]):
                    detected_languages.add(language)

    # -----------------------------
    # STEP 2: Run scanners conditionally
    # -----------------------------
    for language in detected_languages:
        rules = load_rules(language)
        scanner = SCANNER_REGISTRY[language]["scanner"]
        findings.extend(
            scanner(repo_path, rules)
        )

    return {
        "total_issues": len(findings),
        "findings": findings
    }