"""Compare every rule the library states with every other statement of the same rule, using plain code.

For each attribute, two atoms are compared only when their scopes overlap and neither narrows the other on purpose.
The one with the strongest standing (an addendum for its state, then a policy, a procedure, then a job aid, FAQ or
bulletin, and the newer one on a tie) is the authority, and any comparable atom with a different value is a
conflict. A difference inside a narrower scope someone stated on purpose is a variation, recorded with its reason
and never flagged. An older version of a document still in the library is superseded as a whole.
"""
from engine import scope

TYPE_RANK = {"addendum": 0, "policy": 1, "procedure": 2, "job_aid": 3, "faq": 3, "bulletin": 3, "other": 4}


def standing(atom):
    """Sort key: lower is stronger."""
    return (TYPE_RANK.get(atom["doc_type"], 4), tuple(-int(x) for x in atom["effective"].split("-")), atom["clause"])


def same_value(a, b):
    return a["value"] == b["value"]


def latest(docs):
    out = {}
    for d in docs:
        out[d["id"]] = max(out.get(d["id"], 0), d["version"])
    return out


def variation_reason(a, b):
    """Why a difference is intended, naming the side that narrows the scope the way scope.deliberate found it."""
    if not scope.overlaps(a, b):
        return "Their scopes don't overlap."
    narrow = next(x for x, y in ((a, b), (b, a))
                  if (x["explicit"] or x["doc_type"] == "addendum") and scope.narrower_somewhere(x, y))
    if narrow["doc_type"] == "addendum":
        return "A state addendum sets its own value for its state."
    if narrow.get("scope_text"):
        return f"One clause narrows the scope on purpose ({narrow['scope_text']})."
    return "One clause narrows the scope on purpose."


def conflicts(atoms, docs):
    """(conflict findings, variations) among the current versions of every document."""
    newest = latest(docs)
    current = [a for a in atoms if a["version"] == newest[a["doc_id"]]]
    by_attr = {}
    for a in current:
        by_attr.setdefault(a["attribute"], []).append(a)
    found, variations, seen = [], [], set()
    for attr in sorted(by_attr):
        group = sorted(by_attr[attr], key=standing)
        for x in group:
            comparable, deliberate = [], []
            for y in group:
                if y is x or y["clause"] == x["clause"]:
                    continue
                if scope.deliberate(x, y):
                    if not same_value(x, y):
                        deliberate.append(y)
                    continue
                comparable.append(y)
            for y in deliberate:
                k = ("v",) + tuple(sorted((x["clause"], y["clause"])))
                if k not in seen:
                    seen.add(k)
                    variations.append({"type": "variation", "attribute": attr, "clauses": sorted([x["clause"], y["clause"]]),
                                       "reason": variation_reason(x, y)})
            if not comparable:
                continue
            authority = min(comparable + [x], key=standing)
            if authority is x or same_value(authority, x):
                continue
            k = ("c",) + tuple(sorted((x["clause"], authority["clause"])))
            if k in seen:
                continue
            seen.add(k)
            found.append({"type": "conflict", "attribute": attr, "clauses": [authority["clause"], x["clause"]],
                          "authoritative": authority["clause"], "values": [authority["value"], x["value"]],
                          "texts": [authority["value_text"], x["value_text"]], "decided_by": "code",
                          "rule": "The same rule in overlapping scopes with different values"})
    return found, variations


def superseded(atoms, docs):
    """One finding per older version still in the library, with the values that changed since."""
    newest = latest(docs)
    by_doc = {}
    for a in atoms:
        by_doc.setdefault(a["doc"], []).append(a)
    keys = {(d["id"], d["version"]): d["key"] for d in docs}
    out = []
    for d in sorted(docs, key=lambda x: x["key"]):
        if d["version"] == newest[d["id"]]:
            continue
        cur_key = keys[(d["id"], newest[d["id"]])]
        cur = {a["attribute"]: a for a in by_doc.get(cur_key, [])}
        changes = []
        for a in by_doc.get(d["key"], []):
            b = cur.get(a["attribute"])
            if b and not same_value(a, b):
                changes.append({"attribute": a["attribute"], "old": a["clause"], "current": b["clause"],
                                "old_value": a["value"], "current_value": b["value"]})
        out.append({"type": "superseded", "doc": d["key"], "current": cur_key, "changes": changes,
                    "clauses": [c["old"] for c in changes], "decided_by": "code",
                    "rule": "Two versions of one document are both in the library, and the newer one replaces the older"})
    return out
