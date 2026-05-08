import ssl
import socket
import requests
from urllib.parse import urlparse
from datetime import datetime

TIMEOUT = 5

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy"
]

def check_ssl(domain):
    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                expiry = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                issuer = dict(x[0] for x in cert['issuer'])

                return {
                    "valid": True,
                    "expiry": str(expiry),
                    "issuer": issuer.get("organizationName", "Unknown")
                }
    except Exception as e:
        return {"valid": False, "error": str(e)}

def check_headers(url):
    try:
        response = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        headers = response.headers

        missing = [h for h in SECURITY_HEADERS if h not in headers]

        return {
            "status_code": response.status_code,
            "missing_headers": missing,
            "redirects": len(response.history)
        }
    except Exception as e:
        return {"error": str(e)}

def validate_site(url):
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path

    ssl_result = check_ssl(domain)
    header_result = check_headers(url)

    risk_score = 0
    if not ssl_result.get("valid"):
        risk_score += 50
    if "missing_headers" in header_result:
        risk_score += len(header_result["missing_headers"]) * 5
    if header_result.get("redirects", 0) > 3:
        risk_score += 10

    return {
        "ssl": ssl_result,
        "headers": header_result,
        "risk_score": risk_score
    }
