"""The readiness report's facts and its recommendation, chosen by code from the results files.

Each condition in config/readiness.json is checked against a result the build or a scored run wrote. A condition
with no result yet counts as not met, so the report can never claim more than was measured. The recommendation is
"ready for a supervised pilot" only when every condition is met, and the report lists every one that isn't.
"""
import json
from pathlib import Path

from evals import score_ai

HERE = Path(__file__).resolve().parent.parent


def read(name):
    p = HERE.joinpath(*name.split("/"))
    return json.loads(p.read_text()) if p.exists() else None


def measured(vm):
    """The value behind each condition, or None when nothing measured it yet."""
    code = read("evals/code_only.json")["totals"]["by_category"]
    scored = read("evals/ai_scored.json")
    run = score_ai.latest(scored["runs"]) if scored else None
    if run:
        per = [s["combined"]["per_category"] for s in run["seeds"].values()]
        caught = sum(p[c]["caught"] for p in per for c in ("C", "P"))
        planted = sum(p[c]["planted"] for p in per for c in ("C", "P"))
        alarms = sum(s["combined"]["summary"]["false_alarms"] for s in run["seeds"].values())
    else:
        caught, planted = code["C"]["hit"] + code["P"]["hit"], code["C"]["of"] + code["P"]["of"]
        alarms = code["V_alarms"]["hit"] + code["N_alarms"]["hit"]
    cal = (vm.get("drafts") or {}).get("calibration")
    groups = (vm.get("drafts") or {}).get("groups", [])
    drafted = [g for g in groups if g["draft"] or g["held"]]
    return {"recall_cp": round(caught / planted, 3) if planted else None, "false_alarms": alarms,
            "decisions": vm["decisions"]["decided"],
            "judge_trusted": sum(1 for v in cal["by_criterion"].values() if v["trusted"]) if cal else None,
            "gate_pass_rate": round(sum(1 for g in drafted if g["draft"]) / len(drafted), 3) if drafted else None,
            "with_ai": bool(run)}


def recommend(vm, cfg=None):
    cfg = cfg or read("config/readiness.json")
    m = measured(vm)
    unmet = []
    for name, c in cfg["conditions"].items():
        v = m[name]
        ok = v is not None and (v >= c["min"] if "min" in c else v <= c["max"])
        if not ok:
            unmet.append({"name": name, "about": c["about"], "value": v, "need": c.get("min", c.get("max"))})
    return {"ready": not unmet, "unmet": unmet, "measured": m}
