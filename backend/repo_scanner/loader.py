import json

def load_rules(path="policies/ansible_rules.json"):
    with open(path) as f:
        return json.load(f)["rules"]