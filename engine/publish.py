"""The assistant's index before and after reconciliation.

Before, the index holds every clause in the library, older versions included, since staff can find all of them
today. After, the older versions are archived and each approved draft replaces the clauses it consolidates. Every
replaced clause keeps its lineage: the draft that replaced it, the finding behind the draft and who approved it.
"""
from engine import compare


def entry(d, c):
    return {"id": c["id"], "text": c["text"], "title": d["title"], "type": d["type"], "version": d["version"],
            "effective": d["effective"], "applies_to": d["applies_to"]}


def before(result):
    return [entry(d, c) for d in result["documents"] for s in d["sections"] for c in s["clauses"]]


def after(result, drafts):
    """drafts are approved ones: {"group", "title", "text" (rendered), "replaces": [clause ids], "finding", "approved_by"}."""
    newest = compare.latest(result["documents"])
    replaced = {cid: d for d in drafts for cid in d["replaces"]}
    index, archived = [], []
    for d in result["documents"]:
        for s in d["sections"]:
            for c in s["clauses"]:
                if d["version"] < newest[d["id"]]:
                    archived.append({"id": c["id"], "reason": "older version"})
                elif c["id"] in replaced:
                    r = replaced[c["id"]]
                    archived.append({"id": c["id"], "reason": "replaced", "by": f"draft:{r['group']}",
                                     "finding": r.get("finding"), "approved_by": r.get("approved_by")})
                else:
                    index.append(entry(d, c))
    for r in drafts:
        index.append({"id": f"draft:{r['group']}", "text": r["text"], "title": r["title"], "type": "consolidated",
                      "version": 1, "effective": r.get("effective", ""), "applies_to": r.get("applies_to", ""),
                      "replaces": r["replaces"]})
    return index, archived
