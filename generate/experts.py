"""Two synthetic experts label every evaluation pair and grade every calibration draft.

They agree on the clear cases. They disagree where reasonable people do: an exception one document mentions and
another leaves out, days against business days, a general role name against a specific one, and an older version
that's still published. Each label carries a short rationale in the expert's own terms. The specialist settles every
disagreement, and each decision becomes a rule and a test.
"""
from generate import bank

RATIONALE = {
    "conflict": "The two clauses set different values for the same rule in the same scope.",
    "variation": "The second clause states a narrower scope, so its different value is intended.",
    "duplicate": "The same steps appear in both documents.",
    "superseded": "These are two versions of one document, and the newer version replaces the older one.",
    "consistent": "Both clauses say the same thing.",
    "unrelated": "These clauses govern different things.",
}

DISAGREE = {
    "exception_path": {
        "operations": ("consistent", "The procedure covers the everyday case, and the exception lives in the policy where it belongs."),
        "compliance": ("conflict", "Staff who follow the procedure will refuse requests the policy allows, so the two documents disagree in practice."),
    },
    "unit": {
        "operations": ("consistent", "Everyone in the branches reads this deadline as business days."),
        "compliance": ("conflict", "Days and business days can differ by four days, and customers are told the shorter one."),
    },
    "role_generic": {
        "operations": ("consistent", "In a branch, the manager is the branch manager."),
        "compliance": ("conflict", "An assistant manager or head teller could read a general role as permission, so it widens who can approve."),
    },
    "older_version": {
        "operations": ("superseded", "The newer version replaced it, so this is a cleanup task."),
        "compliance": ("conflict", "The older version is still published and a branch can follow it today, so it's a live conflict until it's archived."),
    },
}

PLAIN_DISAGREE = {
    "operations": (True, "It's clear enough for a branch to act on."),
    "compliance": (False, "A qualifier like that leaves room for staff to decide for themselves."),
}


def label_pairs(pairs, items_by_id):
    """{expert: {pair id: {"label", "rationale"}}}."""
    out = {name: {} for name in bank.EXPERTS}
    older = 0
    for p in pairs:
        item = items_by_id.get(p["item"]) if p["item"] else None
        kind = None
        if p["category"] == "A":
            kind = item["kind"]
        elif p["category"] == "S" and older < 3:
            kind = "older_version"
            older += 1
        for name in bank.EXPERTS:
            if kind:
                label, why = DISAGREE[kind][name]
            else:
                label, why = p["label"], RATIONALE[p["label"]]
            out[name][p["pair"]] = {"label": label, "rationale": why}
    return out


def grade_drafts(drafts):
    """{expert: {draft id: {criterion: (pass, note)}}}. They differ on plainness for three unclear drafts."""
    out = {name: {} for name in bank.EXPERTS}
    disputed = [d["draft"] for d in drafts if d["defect"] == "unclear"][:3]
    for d in drafts:
        for name in bank.EXPERTS:
            grades = {k: [v, ""] for k, v in d["gold"].items()}
            if d["draft"] in disputed:
                ok, note = PLAIN_DISAGREE[name]
                grades["plain"] = [ok, note]
            out[name][d["draft"]] = grades
    return out
