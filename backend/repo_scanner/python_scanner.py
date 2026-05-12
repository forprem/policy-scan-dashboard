import os
import re

from .models import Finding


def remove_triple_quotes(lines):

    cleaned = []
    inside_block = False
    quote_type = None

    for line in lines:

        stripped = line.strip()

        # Detect start of triple quotes
        if not inside_block:

            if stripped.startswith('"""') or stripped.startswith("'''"):
                inside_block = True
                quote_type = stripped[:3]

                # if starts and ends on same line → skip it
                if stripped.count(quote_type) == 2:
                    inside_block = False

                continue

        else:
            # End of triple quote block
            if quote_type in stripped:
                inside_block = False
            continue

        cleaned.append(line)

    return cleaned

def scan_python_files(repo_path, rules):

    findings = []

    for root, _, files in os.walk(repo_path):

        for file in files:

            if not file.endswith(".py"):
                continue

            full_path = os.path.join(root, file)

            with open(full_path, "r", errors="ignore") as f:
                lines = f.readlines()
                lines = remove_triple_quotes(lines)

            for i, line in enumerate(lines):

                stripped = line.strip()

                # Ignore comments
                if stripped.startswith("#"):
                    continue

                for rule in rules:

                    if re.search(rule["pattern"], line):

                        findings.append(Finding(
                            file=os.path.relpath(full_path, repo_path),
                            rule_id=rule["id"],
                            severity=rule["severity"],
                            message=rule["description"],
                            line_number=i + 1,
                            line_content=line.strip()
                        ))

    return findings
