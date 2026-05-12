import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def load_rules(language):

    rule_file = os.path.join(
        BASE_DIR,
        "policies",
        f"{language}_rules.json"
    )

    with open(rule_file, "r") as f:
        data = json.load(f)
        return data["rules"]
