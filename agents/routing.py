"""Choose each AI step's model: the cheapest that clears the step's bar, within the vendors the client approves.

Each step has a quality bar from its evaluation, set against the best model measured:
    extract   exact atoms within one point of the best model
    classify  accuracy within two points of the best, and no deliberate variation ever labeled a conflict
    draft     as many drafts as the best model's pass both the gate and the judge, which reads every model's drafts
              because the gate proves values and nothing else. A held step stays on the model the engineer chose after reading
    judge     trusted on every criterion against the experts, and never from the drafter's vendor
    assist    within one question in ten of the best model, counting only questions whose clause search retrieved
Ties on cost go to the faster model. The other models that clear the bar become the fallback chain, cheapest first.
Every route states its reason as a key the page words: cheapest, hold, none_clears, same_vendor or unmeasured. Every
model that misses a bar gets a key too, in WHY. With no comparison recorded, each step keeps the model
config/models.json names.
"""
import json
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
COMPARISON = HERE.joinpath("evals", "model_comparison.json")
POLICY = HERE.joinpath("config", "client_policy.json")


def load(path=COMPARISON):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else None


WHY = ("not_measured", "extract_below", "classify_below", "classify_variation", "draft_unjudged", "draft_below",
       "judge_untrusted", "assist_below")
# How far below the best model a step's quality may sit. The judge's bar is instead every criterion at or above the
# calibration bar, so its lowest criterion is what the chart plots.
BELOW_BEST = {"extract": 0.01, "classify": 0.02, "draft": 0.0, "assist": 0.1}
JUDGE_BAR = 0.9


def measure(step, m):
    """The number a step's bar reads: the judge's lowest agreement on any criterion, and every other step's quality."""
    if step == "judge":
        shares = [v for v in (m.get("by_criterion") or {}).values() if v is not None]
        return min(shares) if shares else None
    return m.get("quality")


def bar(step, best):
    """The level a step's measure must reach, given the best model measured in the pool."""
    return JUDGE_BAR if step == "judge" else round(best - BELOW_BEST[step], 6)


def clears(step, m, best):
    """Whether one model's measured result clears the step's bar, and the WHY key when it doesn't."""
    q = m.get("quality")
    if q is None:
        return False, "not_measured"
    if step == "extract" and q < bar(step, best):
        return False, "extract_below"
    if step == "classify":
        if q < bar(step, best):
            return False, "classify_below"
        if m.get("variations_as_conflict", 0):
            return False, "classify_variation"
    if step == "draft":
        if not m.get("judged"):
            return False, "draft_unjudged"
        if q < bar(step, best):
            return False, "draft_below"
    if step == "judge" and not m.get("trusted_on_all"):
        return False, "judge_untrusted"
    if step == "assist" and q < bar(step, best):
        return False, "assist_below"
    return True, ""


def route(step, results, vendors, holds=None, drafter_vendor=None):
    """{model, reason, fallbacks, rejected, best} for one step. results maps model id to its measured result. A held
    step keeps the free route's fallbacks and names the model that would route without the hold."""
    hold = (holds or {}).get(step)
    if hold and hold in results and results[hold]["vendor"] in vendors:
        free = route(step, results, vendors, None, drafter_vendor)
        return {"model": hold, "reason": "hold", "unheld": free["model"], "best": free.get("best"),
                "fallbacks": [m for m in [free["model"]] + free["fallbacks"] if m and m != hold],
                "rejected": {k: v for k, v in free["rejected"].items() if k != hold}}
    pool = {k: v for k, v in results.items() if v["vendor"] in vendors}
    if step == "judge" and drafter_vendor:
        others = {k: v for k, v in pool.items() if v["vendor"] != drafter_vendor}
        if pool and not others:
            return {"model": None, "reason": "same_vendor", "fallbacks": [], "rejected": {}}
        pool = others
    if not pool:
        return {"model": None, "reason": "unmeasured", "fallbacks": [], "rejected": {}}
    best = max((v["quality"] for v in pool.values() if v.get("quality") is not None), default=0)
    ok, rejected = [], {}
    for k, v in pool.items():
        passed, why = clears(step, v, best)
        if passed:
            ok.append(k)
        else:
            rejected[k] = why
    ok.sort(key=lambda k: (pool[k]["cost_per_item"], pool[k]["seconds_per_item"], k))
    if not ok:
        return {"model": None, "reason": "none_clears", "fallbacks": [], "rejected": rejected, "best": best}
    return {"model": ok[0], "reason": "cheapest", "fallbacks": ok[1:], "rejected": rejected, "best": best}


def plan(comparison, vendors, holds=None):
    """Every step's route for one set of approved vendors. The judge is routed after the drafter so it can avoid the
    drafter's vendor."""
    out = {}
    for step in ("extract", "classify", "draft", "assist", "judge"):
        results = comparison["steps"].get(step, {})
        drafter = out.get("draft", {}).get("model")
        drafter_vendor = comparison["steps"].get("draft", {}).get(drafter, {}).get("vendor") if drafter else None
        out[step] = route(step, results, vendors, holds, drafter_vendor)
    return out


def blend(comparison, plan, counts):
    """(dollars, steps a person does) for one run on a plan's routes: each step's item count times its routed model's
    cost per item. counts maps a step to its items in one run, and a step without a count is left out."""
    dollars, people = 0.0, []
    for step, r in plan.items():
        if step not in counts:
            continue
        if r["model"] is None:
            people.append(step)
            continue
        dollars += counts[step] * comparison["steps"][step][r["model"]]["cost_per_item"]
    return round(dollars, 2), people


def every_policy(comparison, holds=None):
    """The routes for every combination of approved vendors, precomputed for the page's control."""
    vendors = sorted({v["vendor"] for step in comparison["steps"].values() for v in step.values()})
    out = {}
    for n in range(len(vendors), 0, -1):
        for combo in combinations(vendors, n):
            out[" + ".join(combo)] = plan(comparison, set(combo), holds)
    return out
