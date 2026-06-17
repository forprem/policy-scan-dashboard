import os
import re

from .models import Finding


def remove_tf_block_comments(lines):
    cleaned = []
    inside_block = False

    for line in lines:
        current = line

        if inside_block:
            end_idx = current.find("*/")
            if end_idx == -1:
                continue
            inside_block = False
            current = current[end_idx + 2:]

        while True:
            start_idx = current.find("/*")
            if start_idx == -1:
                break

            end_idx = current.find("*/", start_idx + 2)
            if end_idx == -1:
                inside_block = True
                current = current[:start_idx]
                break

            current = current[:start_idx] + current[end_idx + 2:]

        if current.strip():
            cleaned.append(current)

    return cleaned


def scan_terraform_files(repo_path, rules):
    findings = []

    for root, _, files in os.walk(repo_path):
        for file in files:
            if not file.endswith((".tf", ".tfvars")):
                continue

            full_path = os.path.join(root, file)

            with open(full_path, "r", errors="ignore") as f:
                lines = f.readlines()
                lines = remove_tf_block_comments(lines)

            for i, line in enumerate(lines):
                stripped = line.strip()

                if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                    continue

                # Remove trailing comment when it is not inside a quoted string.
                if "#" in line and line.count('"') % 2 == 0:
                    line = line.split("#", 1)[0]
                if "//" in line and line.count('"') % 2 == 0:
                    line = line.split("//", 1)[0]

                for rule in rules:
                    pattern_match = re.search(rule["pattern"], line)

                    if not pattern_match:
                        continue

                    if "ignore_pattern" in rule:
                        ignore_patterns = rule["ignore_pattern"]
                        if isinstance(ignore_patterns, str):
                            ignore_patterns = [ignore_patterns]

                        if any(re.search(pattern, line) for pattern in ignore_patterns):
                            continue

                    if "contains" in rule:
                        line_lower = line.lower()
                        if not any(c.lower() in line_lower for c in rule["contains"]):
                            continue

                    findings.append(Finding(
                        file=os.path.relpath(full_path, repo_path),
                        rule_id=rule["id"],
                        severity=rule["severity"],
                        message=rule["description"],
                        line_number=i + 1,
                        line_content=line.strip()
                    ))

    return findings
