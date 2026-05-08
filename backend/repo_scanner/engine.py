from .loader import load_rules
from .ansible_scanner import scan_ansible_files

def scan_repo(repo_path):
    rules = load_rules()
    findings = scan_ansible_files(repo_path, rules)

    return {
        "total_issues": len(findings),
        "findings": [f.__dict__ for f in findings]
    }