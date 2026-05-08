import os
import re
from .models import Finding


def scan_ansible_files(repo_path, rules):
    findings = []

    for root, _, files in os.walk(repo_path):

        for file in files:

            # only scan yaml files
            if not file.endswith((".yml", ".yaml")):
                continue

            full_path = os.path.join(root, file)

            # -----------------------------
            # Read file safely
            # -----------------------------
            with open(full_path, "r", errors="ignore") as f:
                lines = f.readlines()

            # -----------------------------
            # Clean content
            # Ignore comments
            # -----------------------------
            clean_lines = []

            for line in lines:

                stripped = line.strip()

                # ignore full-line comments
                if stripped.startswith("#"):
                    continue

                # remove inline comments
                if "#" in line:
                    line = line.split("#", 1)[0]

                # skip empty lines
                if line.strip():
                    clean_lines.append(line)

            # -----------------------------
            # Rule evaluation
            # -----------------------------
            for rule in rules:

                for i, line in enumerate(clean_lines):

                    # regex match
                    pattern_match = re.search(
                        rule["pattern"],
                        line
                    )

                    if not pattern_match:
                        continue

                    # optional ignore pattern
                    if "ignore_pattern" in rule:
                        if re.search(
                            rule["ignore_pattern"],
                            line
                        ):
                            continue

                    # optional contains check
                    if "contains" in rule:
                        if not any(
                            c in line
                            for c in rule["contains"]
                        ):
                            continue

                    # clean relative path
                    relative_path = os.path.relpath(
                        full_path,
                        repo_path
                    )

                    findings.append(Finding(
                        file=relative_path,
                        rule_id=rule["id"],
                        severity=rule["severity"],
                        message=rule["description"],
                        line_number=i + 1,
                        line_content=line.strip()
                    ))

    return findings