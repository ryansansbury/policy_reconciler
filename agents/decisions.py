"""The specialist's decisions on the experts' disagreements, and the precedence rules they become.

The two experts disagree in four places by design: an exception one document mentions and another leaves out, days
against business days, a general role against a specific one, and an older version that's still published.
Each group's decision is recorded once with its reason in evals/decisions.json. Each decision then does
three things. It labels every disputed pair of its group in the answer key's next version, it becomes a precedence
rule code applies instead of asking the classifier, and a test holds code to it.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PATH = HERE.joinpath("evals", "decisions.json")
KINDS = ("exception_path", "unit", "role_generic", "older_version")


def load(path=PATH):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else {"decisions": {}, "key_version": 1}


def kinds(pairs, key):
    """{evaluation pair id: disagreement group}. These are the pairs generate/experts.py has the experts disagree on:
    every A pair by its kind, and the first three S pairs as an older version that's still published."""
    items = {i["id"]: i for i in key["items"]}
    out, older = {}, 0
    for p in pairs:
        if p["category"] == "A":
            out[p["pair"]] = items[p["item"]]["kind"]
        elif p["category"] == "S" and older < 3:
            out[p["pair"]] = "older_version"
            older += 1
    return out


def rule(kind, decisions):
    """The label code applies to a group's pairs, or None while the group is undecided."""
    d = (decisions or {}).get("decisions", {}).get(kind)
    return d["label"] if d else None


def apply(labels, pair_kinds, decisions):
    """One expert's labels with every decided group's pairs set to the decision."""
    return {pid: rule(pair_kinds.get(pid), decisions) or lab for pid, lab in labels.items()}
