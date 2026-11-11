"""The data behind the Drafts and Assistant tabs: each contradicted rule's consolidated draft with its gate result, the
test that injects an untraced value, the diff against every clause it replaces, the judge's grades and the approval,
and each preset question answered before and after reconciliation. Everything comes from recordings, and anything
not recorded yet says so.
"""
import json
from pathlib import Path

from agents import assisting, drafting, items, judging, replay, rulings
from engine import diff, gate

HERE = Path(__file__).resolve().parent.parent
INJECTED = "On weekends the limit is $999."


def injected(draft, group):
    """The labeled gate test: the same draft with one value added outside any placeholder, and what the gate says."""
    text = draft["text"] + " " + INJECTED
    problems, _ = gate.check(text, group["allowed"], group["type"])
    return {"text": text, "problems": problems}


def judge_view(groups, accepted, models, runs, seed):
    """The judge's grades on each draft, and which criteria it's trusted on. The calibration comes from a scored round
    on a seed's calibration drafts, or from the model comparison, which ran every model on the same drafts."""
    graded = replay.load("judge", str(seed), runs, [models["judge"]], items=judging.draft_items(groups, accepted))
    calibration = None
    folder = Path(runs or replay.RUNS).joinpath("judge")
    tags = (sorted((p.name for p in folder.glob("judge-*")), reverse=True)
            + sorted((p.name for p in folder.glob("cmp-*")), reverse=True))
    for tag in tags:
        its = items.for_tag("judge", tag, runs, models)
        r = replay.load("judge", tag, runs, [models["judge"]], items=its)
        if r["accepted"]:
            experts = json.loads(HERE.joinpath("data", "key", tag.split("-", 1)[1], "experts.json").read_text())
            calibration = {"tag": tag, "by_criterion": judging.calibration(experts["drafts"], r["accepted"])}
            break
    return graded["accepted"], calibration


def ruled(group, draft, grades, record):
    """The judge's grades on one draft with the specialist's ruling on each failed criterion, when one covers it."""
    if not grades:
        return grades
    key = judging.draft_key(group, draft["rendered"])
    return {c: dict(v, ruling=None if v["pass"] else rulings.ruling(key, c, v["evidence"], record))
            for c, v in grades.items()}


def build(seed, runs=None, models=None):
    models = models or items.step_models()
    result, groups, accepted = items.drafts(seed, runs, models)
    recorded = replay.load("draft", str(seed), runs, [models["draft"]], items=groups)
    grades, calibration = judge_view(groups, accepted, models, runs, seed)
    ok = items.approvals()
    record = rulings.load()
    rows = []
    for g in groups:
        d = accepted.get(g["group"])
        old = " ".join(c["text"] for c in g["change"])
        rows.append({"group": g["group"], "rule": g["rule"], "keep": g["keep"], "change": g["change"],
                     "allowed": g["allowed"], "draft": d, "held": recorded["held"].get(g["group"]),
                     "diff": diff.diff(old, d["rendered"]) if d else None,
                     "injected": injected(d, g) if d else None,
                     "grades": ruled(g["group"], d, grades.get(g["group"]), record) if d else None,
                     "redrafted": bool(g.get("specialist_note")),
                     "approved": items.approval_for(g["group"], d["rendered"], ok) if d else None,
                     "hold": ok["held"].get(g["group"])})
    return {"groups": rows, "calibration": calibration, "model": models["draft"], "judge_model": models["judge"],
            "families_differ": judging.family_ok(models["draft"], models["judge"],
                                                 json.loads(HERE.joinpath("config", "models.json").read_text())["models"]),
            "assistant": assistant(seed, runs, models)}


def assistant(seed, runs, models):
    questions = json.loads(HERE.joinpath("data", "key", str(seed), "evals.json").read_text())["assistant"]
    out = {"questions": [], "recorded": False}
    sides = {}
    for when in ("before", "after"):
        tag = f"{when}-{seed}"
        its = items.for_tag("assist", tag, runs, models)
        r = replay.load("assist", tag, runs, [models["assist"]], items=its)
        sides[when] = {"items": {i["question"]: i for i in its}, "answers": r["accepted"], "held": r["held"]}
        out["recorded"] = out["recorded"] or bool(r["accepted"])
    for q in questions:
        qid = assisting.question_id(q)
        row = {"id": qid, "text": q["question"]}
        for when, side in sides.items():
            item, answer = side["items"].get(qid), side["answers"].get(qid)
            titles = {c["id"]: c["title"] for c in (item or {}).get("clauses", [])}
            row[when] = None if not answer else dict(answer, cited=[{"id": c, "title": titles.get(c, c)}
                                                                    for c in answer["citations"]])
        out["questions"].append(row)
    return out
