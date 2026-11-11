"""Score a review against a seed's frozen answer key.

    C and P   caught when a conflict finding includes the planted clause, and the authority it names is right when
              it's the planted authority or one of the clauses that state the right value
    D         caught when a duplicate finding includes at least three of the copied clauses
    S         caught when a superseded finding names the older version
    V and N   a false alarm when a conflict finding includes the planted clause
    A         not scored until the experts' disagreement is decided. Reported as what the review said, including
              the classifier's label when the AI steps decided it.

Conflict findings that match no planted item are counted as unexplained and listed, since a precise review is one
whose every finding means something.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load_key(seed, root=None):
    root = Path(root or HERE.joinpath("data", "key"))
    return json.loads(root.joinpath(str(seed), "key.json").read_text())


def score(result, key, decisions=None):
    """decisions is evals/decisions.json. A disputed item whose group the specialist decided is scored against that ruling, as
    the answer key's next version says: caught when the review flags it and he ruled it a conflict, or when the review
    leaves it alone and he ruled otherwise. Its result is kept apart from the frozen categories."""
    conflicts = [f for f in result["findings"] if f["type"] == "conflict"]
    dups = [f for f in result["findings"] if f["type"] == "duplicate"]
    older = [f for f in result["findings"] if f["type"] == "superseded"]
    in_conflict = {}
    for f in conflicts:
        for c in f["clauses"]:
            in_conflict.setdefault(c, []).append(f)
    queued = {q["clause"] for q in result.get("queue", [])}
    decided = {c: f"the classifier said {d['label']}" for d in result.get("decided", [])
               for c in (d["a"]["clause"], d["b"]["clause"])}
    decided.update({c: f"the decision says {d['label']}" for d in result.get("ruled", [])
                    for c in (d["a"]["clause"], d["b"]["clause"])})
    per = {c: {"planted": 0, "caught": 0, "missed": []} for c in ("C", "P", "D", "S")}
    alarms = {c: {"planted": 0, "flagged": 0, "flags": []} for c in ("V", "N")}
    disputed = []
    explained = set()
    authority = [0, 0]
    planted_conflicts = {it["target"] for it in key["items"] if it["category"] in ("C", "P")}
    for it in key["items"]:
        cat = it["category"]
        if cat in ("C", "P"):
            per[cat]["planted"] += 1
            hit = in_conflict.get(it["target"], [])
            if hit:
                per[cat]["caught"] += 1
                explained.update(id(f) for f in hit)
                right = {it["authoritative"], *it.get("conflicts_with", [])}
                authority[0] += any(f["authoritative"] in right for f in hit)
                authority[1] += 1
            else:
                per[cat]["missed"].append(it["id"])
        elif cat == "D":
            per[cat]["planted"] += 1
            if any(len(set(it["copy"]) & set(f["clauses"])) >= 3 for f in dups):
                per[cat]["caught"] += 1
            else:
                per[cat]["missed"].append(it["id"])
        elif cat == "S":
            per[cat]["planted"] += 1
            if any(f["doc"] == it["old_doc"] for f in older):
                per[cat]["caught"] += 1
            else:
                per[cat]["missed"].append(it["id"])
        elif cat in ("V", "N"):
            alarms[cat]["planted"] += 1
            hit = [f for f in in_conflict.get(it["target"], []) if not set(f["clauses"]) & planted_conflicts]
            if hit:
                alarms[cat]["flagged"] += 1
                alarms[cat]["flags"].append(it["id"])
                explained.update(id(f) for f in hit)
        elif cat == "A":
            # The disputed clause is the one the experts argue about: the statement that leaves the exception out,
            # or the one with the other unit or the general role.
            t = it["target"]
            problem = it.get("anchor") if it["kind"] == "exception_path" else t
            hits = [f for f in in_conflict.get(problem, []) if f["attribute"] == it["attribute"]
                    and (it["kind"] != "exception_path" or f["authoritative"] != problem)]
            flagged = bool(hits)
            explained.update(id(f) for f in hits)
            said = ("conflict" if flagged else decided[t] if t in decided
                    else "sent to AI" if t in queued else "consistent")
            ruled = ((decisions or {}).get("decisions", {}).get(it["kind"]) or {}).get("label")
            row = {"item": it["id"], "kind": it["kind"], "said": said}
            if ruled:
                row.update(ruled=ruled, matches=flagged == (ruled == "conflict"))
            disputed.append(row)
            explained.update(id(f) for f in in_conflict.get(it["target"], []))
    ruled_extra = [f for f in conflicts if id(f) not in explained and f.get("decided_by") == "rule"]
    unexplained = [f for f in conflicts if id(f) not in explained and f.get("decided_by") != "rule"]
    caught = sum(per[c]["caught"] for c in per)
    planted = sum(per[c]["planted"] for c in per)
    flagged = sum(alarms[c]["flagged"] for c in alarms)
    return {"per_category": per, "false_alarms": alarms, "disputed": disputed,
            "conflict_findings": len(conflicts), "unexplained": [f["clauses"] for f in unexplained],
            "ruled_extra": [f["clauses"] for f in ruled_extra],
            "summary": {"caught": caught, "planted": planted, "false_alarms": flagged,
                        "unexplained": len(unexplained), "ruled_extra": len(ruled_extra),
                        "queue": len(result.get("queue", [])),
                        "authority_right": authority[0], "authority_checked": authority[1],
                        "decided_match": sum(1 for d in disputed if d.get("matches")),
                        "decided_of": sum(1 for d in disputed if "ruled" in d),
                        "key_version": (decisions or {}).get("key_version", 1)}}
