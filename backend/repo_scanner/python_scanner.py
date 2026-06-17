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


def is_non_literal_etree_input(line):
    call_match = re.search(
        r"(?:\bET\b|\betree\b|\bElementTree\b|xml\.etree\.ElementTree)\.(?:parse|fromstring)\s*\(([^)]*)\)",
        line
    )

    if not call_match:
        return False

    args = call_match.group(1)
    first_arg = args.split(",", 1)[0].strip()

    if not first_arg:
        return False

    # String literal arguments are treated as static and not flagged.
    if re.match(r"^[rRuUbBfF]{0,2}(['\"]).*\1$", first_arg):
        return False

    first_arg_lower = first_arg.lower()

    # Path construction calls are generally local/trusted file usage.
    if re.search(r"\b(os\.path\.|pathlib\.path|path\()", first_arg_lower):
        return False

    # Simple path/file variable names are treated as local file input.
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", first_arg):
        if re.search(r"(?:^|_)(path|file|filepath|filename|dir|directory|pom|xml_path|xml_file)(?:$|_)", first_arg_lower):
            return False

    # Explicit external/untrusted sources should be flagged.
    if re.search(r"(?:^|_|\.)(request|response|body|payload|input|user|param|query|form|header|cookie|raw|data|content|stream|socket|url)(?:$|_|\.)", first_arg_lower):
        return True

    return True


def classify_pickle_load_severity(line, default_severity):
    call_match = re.search(
        r"pickle\.(?:load|loads)\s*\(([^)]*)\)",
        line
    )

    if not call_match:
        return default_severity

    args = call_match.group(1)
    first_arg = args.split(",", 1)[0].strip()
    first_arg_lower = first_arg.lower()

    if not first_arg:
        return default_severity

    external_markers = (
        "request", "response", "body", "payload", "input", "user",
        "param", "query", "form", "header", "cookie", "upload",
        "download", "url", "http", "https", "socket", "stream",
        "tmp", "temp"
    )

    internal_markers = (
        "cache", "local", "internal", "trusted", "model", "artifact",
        "state", "session", "store", "db", "database", "file", "path"
    )

    if any(marker in first_arg_lower for marker in external_markers):
        return "HIGH"

    if any(marker in first_arg_lower for marker in internal_markers):
        return "LOW"

    if re.match(r"^[rRuUbBfF]{0,2}(['\"]).*\1$", first_arg):
        return "LOW"

    return default_severity


def is_safe_os_system_usage(line):
    call_match = re.search(
        r"os\.system\s*\(([^)]*)\)",
        line
    )

    if not call_match:
        return False

    arg = call_match.group(1).strip()
    arg_lower = arg.lower()

    # Safe literal clear-screen commands.
    if re.match(r"^[rRuUbBfF]{0,2}['\"](clear|cls)['\"]$", arg):
        return True

    # Safe conditional expression selecting only cls/clear.
    if "os.name" in arg_lower and " if " in arg_lower and " else " in arg_lower:
        if re.search(
            r"['\"](cls|clear)['\"]\s*if\s+.+\s+else\s+['\"](cls|clear)['\"]",
            arg_lower
        ):
            return True

    return False


def classify_eval_severity(line, default_severity):
    call_match = re.search(
        r"(^|[^.\w])eval\s*\(([^)]*)\)",
        line
    )

    if not call_match:
        return default_severity

    arg = call_match.group(2).strip()
    arg_lower = arg.lower()

    if not arg:
        return default_severity

    external_markers = (
        "input(", "request", "response", "body", "payload", "user",
        "param", "query", "form", "header", "cookie", "argv",
        "getenv", "os.environ", "raw", "stream", "socket", "url"
    )

    if any(marker in arg_lower for marker in external_markers):
        return "CRITICAL"

    # Literal arithmetic-like expressions are lower risk than arbitrary code.
    literal_match = re.match(r"^[rRuUbBfF]{0,2}(['\"])(.*)\1$", arg)
    if literal_match:
        expr_content = literal_match.group(2)
        if re.match(r"^[0-9\s+\-*/().%]+$", expr_content):
            return "LOW"
        return "MEDIUM"

    # Internal expression/format variables are still risky but lower confidence.
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", arg):
        if re.search(r"(fmt|format|expr|expression|formula|compare|calc|math)", arg_lower):
            return "LOW"

    return default_severity

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

                # Ignore assertion lines commonly used in tests.
                if re.search(r"\b(assert\s+|assert[A-Za-z_][A-Za-z0-9_]*\s*\()", stripped):
                    continue

                for rule in rules:

                    #if re.search(rule["pattern"], line):

                    # --------------------------------
                    # Main regex pattern match
                    # --------------------------------
                    pattern_match = re.search(
                        rule["pattern"],
                        line
                    )

                    if not pattern_match:
                        continue

                    if rule["id"] == "PYTHON_OS_SYSTEM_USAGE":
                        if is_safe_os_system_usage(line):
                            continue

                    # Special case: only flag ElementTree parsing when input
                    # is non-literal (dynamic or external source).
                    if rule["id"] == "PYTHON_XML_ETREE":
                        if not is_non_literal_etree_input(line):
                            continue

                    # --------------------------------
                    # Ignore pattern logic
                    # --------------------------------
                    if "ignore_pattern" in rule:

                        ignore_patterns = rule["ignore_pattern"]

                        # Support single string or list
                        if isinstance(ignore_patterns, str):
                            ignore_patterns = [ignore_patterns]

                        if any(
                            re.search(pattern, line)
                            for pattern in ignore_patterns
                        ):
                            continue

                    # --------------------------------
                    # Contains logic
                    # --------------------------------
                    if "contains" in rule:

                        if not any(
                            c in line for c in rule["contains"]
                        ):
                            continue

                    finding_severity = rule["severity"]
                    if rule["id"] == "PYTHON_PICKLE_LOADS":
                        finding_severity = classify_pickle_load_severity(
                            line,
                            rule["severity"]
                        )
                    elif rule["id"] == "PYTHON_EVAL_USAGE":
                        finding_severity = classify_eval_severity(
                            line,
                            rule["severity"]
                        )

                    findings.append(Finding(
                        file=os.path.relpath(full_path, repo_path),
                        rule_id=rule["id"],
                        severity=finding_severity,
                        message=rule["description"],
                        line_number=i + 1,
                        line_content=line.strip()
                    ))

    return findings