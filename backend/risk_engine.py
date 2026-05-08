def calculate_risk(result: dict):
    score = 0
    issues = []

    headers = result.get("headers", {})
    https = result.get("https", False)

    # 🔐 HTTPS check
    if not https:
        score += 50
        issues.append({
            "type": "HTTPS",
            "severity": "HIGH",
            "message": "Site is not using HTTPS"
        })

    # 🔐 Security Headers
    security_headers = {
        "content-security-policy": 20,
        "x-frame-options": 10,
        "x-content-type-options": 10,
        "strict-transport-security": 15,
    }

    for header, weight in security_headers.items():
        if header not in headers:
            score += weight
            issues.append({
                "type": "HEADER_MISSING",
                "severity": "MEDIUM",
                "message": f"{header} header is missing"
            })

    # 🍪 Cookie Security (optional if you capture cookies)
    cookies = result.get("cookies", "")
    if cookies:
        if "Secure" not in cookies:
            score += 10
            issues.append({
                "type": "COOKIE",
                "severity": "LOW",
                "message": "Cookies missing Secure flag"
            })
        if "HttpOnly" not in cookies:
            score += 10
            issues.append({
                "type": "COOKIE",
                "severity": "LOW",
                "message": "Cookies missing HttpOnly flag"
            })

    # 🧠 Normalize score
    if score > 100:
        score = 100

    # 🎯 Risk level
    if score >= 70:
        risk = "HIGH"
    elif score >= 30:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "risk": risk,
        "score": score,
        "issues": issues
    }