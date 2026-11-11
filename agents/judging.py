"""The judge's items, the code that checks its grades, and its calibration against the experts.

The judge grades a consolidated draft on four criteria: it keeps every rule its sources state, it adds no rule, it
keeps every stated scope, and it reads plainly. Each grade needs evidence quoted from the draft or a source. The
calibration set is drafts with known defects that both experts graded. On each criterion where the judge agrees with
their shared grade at or above the bar, it grades drafts at scale, and every other criterion stays with a person. The
judge never comes from the drafter's model family, since a model can favor its own family's writing.
"""
import hashlib

from agents import validate

CRITERIA = ("keeps_rules", "adds_no_rule", "keeps_scope", "plain")
BAR = 0.9


def calibration_items(judge_set):
    return [{"draft": d["draft"], "text": d["text"], "sources": d["source_text"]} for d in judge_set]


def draft_items(groups, drafts):
    """Items for the drafter's own drafts: each rendered draft with the clause it keeps as its source. The clauses a
    draft replaces state the very values it corrects, so a judge reading them as sources would fail every draft for
    leaving a wrong value out."""
    out = []
    for g in groups:
        d = drafts.get(g["group"])
        if d:
            out.append({"draft": g["group"], "text": d["rendered"], "sources": [g["keep"]["text"]]})
    return out


def check(batch, reply):
    """(per-draft grades, problems)."""
    try:
        data = validate.parse_json(reply)
    except ValueError as e:
        return {}, [f"the reply isn't valid JSON: {e}"]
    results = data.get("results")
    if not isinstance(results, list):
        return {}, ["the reply needs a results list"]
    by_id = {r.get("draft"): r for r in results if isinstance(r, dict)}
    out, problems = {}, []
    for item in batch:
        r = by_id.get(item["draft"])
        if r is None:
            problems.append(f"{item['draft']}: no result")
            continue
        scores, p = r.get("scores") if isinstance(r.get("scores"), dict) else {}, []
        for c in CRITERIA:
            s = scores.get(c)
            if not isinstance(s, dict) or not isinstance(s.get("pass"), bool):
                p.append(f"{c} needs pass as true or false")
                continue
            ev = str(s.get("evidence") or "")
            if not s["pass"] and not ev:
                p.append(f"{c} failed without evidence")
            elif ev and not any(validate.quoted(ev, t) for t in [item["text"]] + item["sources"]):
                p.append(f"the evidence for {c} isn't quoted from the draft or a source")
        if p:
            problems += [f"{item['draft']}: {x}" for x in p]
        else:
            out[item["draft"]] = {c: {"pass": scores[c]["pass"], "evidence": scores[c].get("evidence") or ""}
                                  for c in CRITERIA}
    return out, problems


def consensus(expert_grades):
    """{draft: {criterion: pass}} where both experts gave the same grade. A split grade is left out until decided."""
    a, b = expert_grades.values()
    return {d: {c: a[d][c][0] for c in CRITERIA if a[d][c][0] == b[d][c][0]} for d in a}


def calibration(expert_grades, grades, bar=BAR):
    """Per criterion: how often the judge matches the experts' shared grade, and whether that clears the bar."""
    gold = consensus(expert_grades)
    out = {}
    for c in CRITERIA:
        pairs = [(gold[d][c], g[c]["pass"]) for d, g in grades.items() if d in gold and c in gold[d]]
        agree = sum(x == y for x, y in pairs)
        share = round(agree / len(pairs), 3) if pairs else None
        out[c] = {"agree": agree, "of": len(pairs), "share": share, "trusted": share is not None and share >= bar,
                  "misses": [d for d, g in grades.items() if d in gold and c in gold[d] and gold[d][c] != g[c]["pass"]]}
    return out


def vendor(model_id, models):
    return next((m["vendor"] for m in models if m["id"] == model_id), None)


def family_ok(drafter, judge, models):
    """True when the judge's vendor differs from the drafter's."""
    a, b = vendor(drafter, models), vendor(judge, models)
    return a is not None and b is not None and a != b


def draft_key(group, text):
    """One id per distinct draft, so a judge reads identical drafts once and never sees which model wrote one."""
    return f"{group}.{hashlib.sha256(str(text).encode()).hexdigest()[:8]}"


def comparison_items(groups, drafts_by_model, judge, main_judge, vendor):
    """The comparison drafts one judge reads: each distinct draft from a vendor other than the judge's. The step's own
    judge reads every other vendor's drafts, and a second judge reads only those from the step's judge's vendor."""
    out, seen = [], set()
    for m, accepted in drafts_by_model.items():
        if vendor.get(m) == vendor.get(judge) or (judge != main_judge and vendor.get(m) != vendor.get(main_judge)):
            continue
        for x in draft_items(groups, accepted):
            key = draft_key(x["draft"], x["text"])
            if key not in seen:
                seen.add(key)
                out.append(dict(x, draft=key))
    return out


def comparison_grades(model, accepted, grades_by_judge, vendor, passes=None):
    """{group: (passed, key, grades)} for one drafter's comparison drafts, each from the first judge in grades_by_judge
    whose vendor differs from the drafter's and that read it. The step's own judge comes first. passes(key, grades)
    decides a pass, so the specialist's rulings can apply, and with none a draft passes on every criterion."""
    passes = passes or (lambda key, grades: all(grades[c]["pass"] for c in CRITERIA))
    out = {}
    for j, grades in grades_by_judge.items():
        if vendor.get(j) == vendor.get(model):
            continue
        for g, d in accepted.items():
            k = draft_key(g, d["rendered"])
            if g not in out and k in grades:
                out[g] = (passes(k, grades[k]), k, grades[k])
    return out
