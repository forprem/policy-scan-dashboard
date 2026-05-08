from dataclasses import dataclass

@dataclass
class Finding:
    file: str
    rule_id: str
    severity: str
    message: str
    line_number: int
    line_content: str