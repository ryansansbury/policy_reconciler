"""Code's review with the AI steps' recordings replayed into it, in the order the steps run.

    1. Code reads the library and queues the clauses it can't read for certain.
    2. The rule extractor's recorded atoms for those clauses join code's atoms.
    3. Comparison runs again, and the pairs code can't settle go to the classifier.
    4. The specialist's decisions settle the pairs in the groups the specialist decided, and the classifier's recorded labels decide the
       rest. Only "conflict" becomes a finding.

Nothing here calls a model. A step with no recording leaves its items waiting, and the page says so. models names
each step's model, as items.step_models() does, so a classifier on another model than the extractor is replayed with
its own recordings. A plain list of model ids applies to both steps.
"""
from agents import combine, inputs, replay


def step_models(models, step):
    """The model ids one step's recordings are replayed for."""
    if isinstance(models, dict):
        m = models.get(step)
        return [m] if isinstance(m, str) else m
    return models


def summary(r, asked):
    return {"asked": asked, "accepted": len(r["accepted"]), "held": r["held"], "stale": r["stale"],
            "missing": len(r["missing"]), "totals": replay.totals(r["used"]),
            "recorded_at": max((u.get("recorded_at", "") for u in r["used"]), default=None) or None}


def run(result, tag, root=None, models=None, decisions=None):
    """The combined review of one library, with what each AI step contributed. decisions is evals/decisions.json,
    and a decided group's pairs are settled by the specialist's rule instead of the classifier."""
    ext = inputs.extract_items(result)
    a1 = replay.load("extract", tag, root, step_models(models, "extract"), items=ext)
    first = combine.review(result, a1["accepted"], decisions=decisions)
    a2 = replay.load("classify", tag, root, step_models(models, "classify"), items=first["pairs"])
    out = combine.review(result, a1["accepted"], a2["accepted"], decisions)
    out["ai"] = {"extract": summary(a1, len(ext)), "classify": summary(a2, len(first["pairs"]))}
    return out
