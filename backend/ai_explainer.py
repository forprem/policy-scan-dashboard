import ollama

client = ollama.Client(host="http://192.168.1.172:11434")


def explain_issue(issue):

    prompt = f"""
You are a cybersecurity expert.

Explain this Ansible security issue in simple language.

Rule ID:
{issue.get("rule_id")}

Severity:
{issue.get("severity")}

Issue:
{issue.get("message")}

Code:
{issue.get("line_content")}

Please explain:
1. Why this is dangerous
2. Real-world attack scenario
3. Secure alternative
4. Best practice
"""

    response = client.chat(   # ✅ IMPORTANT FIX HERE
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]