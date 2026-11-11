"""The items each AI step reads, by tag, built the same way for recording, for replay and for scoring.

    extract   a seed's queued clauses (<seed>), its extraction set (evals-<seed>), or the hand-written clauses
              (fresh_wording)
    classify  the pairs a seed's review couldn't settle once the extractor's atoms are in (<seed>), or a seed's
              labeled pairs (evals-<seed>)
    draft     one group per contradicted rule in a seed's combined review (<seed>)
    judge     the drafter's drafts for a seed (<seed>), a seed's calibration drafts (judge-<seed>), or every model's
              comparison drafts, each read by a judge from another vendor (drafts-<seed>)
    assist    a seed's preset questions against the index before reconciliation (before-<seed>) and after the
              approved drafts are in (after-<seed>)
    any step  the model comparison's fixed subset of a seed's items (cmp-<seed>)
    extract   the first queued clauses of the scale library, for checking the cost estimate (sample-<seed>)

Each step's items depend on the steps before it, so a step's model comes from config/models.json, where "steps"
names the model each step records with.
"""
import hashlib
import json
from pathlib import Path

from agents import assisting, combine, decisions, drafting, flow, inputs, judging, replay, rulings
from engine import pipeline, publish

HERE = Path(__file__).resolve().parent.parent
DATA = HERE.joinpath("data")
APPROVALS = HERE.joinpath("evals", "approvals.json")


_LIBRARIES = {}


def library(seed, data=DATA):
    """Code's review of one seed's library, run once per process. A review never changes once it's made, and the
    build and the scorer ask for the same libraries many times."""
    path = Path(data).joinpath("library", str(seed))
    if str(path) not in _LIBRARIES:
        _LIBRARIES[str(path)] = pipeline.run(path)
    return _LIBRARIES[str(path)]


def configured_models():
    """Each step's model in config/models.json, before any route. The model comparison builds every step's items on
    these, so turning routes on never changes what a comparison measured."""
    return dict(json.loads(HERE.joinpath("config", "models.json").read_text())["steps"])


def step_models():
    """The model each step uses: config/models.json's choice, or the routed one once the client policy turns routes on
    and a comparison exists for its approved vendors."""
    models = configured_models()
    policy = json.loads(HERE.joinpath("config", "client_policy.json").read_text())
    comparison = HERE.joinpath("evals", "model_comparison.json")
    if policy.get("use_routes") and comparison.exists():
        routes = json.loads(comparison.read_text()).get("routes", {}).get(" + ".join(sorted(policy["approved_vendors"])), {})
        models.update({s: r["model"] for s, r in routes.items() if r.get("model")})
    return models


SAMPLE = 30


def sample_items(seed, data=DATA):
    """The first queued clauses of the scale library, for checking the cost estimate against real calls."""
    path = Path(data).joinpath("scale", str(seed))
    if str(path) not in _LIBRARIES:
        _LIBRARIES[str(path)] = pipeline.run(path)
    return inputs.extract_items(_LIBRARIES[str(path)])[:SAMPLE]


def tags_for(step, seeds, evals, fresh=False, compare=(), sample=(), drafts=()):
    if sample:
        return [f"sample-{s}" for s in sample] if step == "extract" else []
    if drafts:
        return [f"drafts-{s}" for s in drafts] if step == "judge" else []
    if compare:
        return [f"cmp-{s}" for s in compare]
    if step == "assist":
        return [f"{when}-{s}" for s in seeds for when in ("before", "after")]
    out = list(seeds)
    if step in ("extract", "classify"):
        out += [f"evals-{s}" for s in evals]
    if step == "judge":
        out += [f"judge-{s}" for s in evals]
    if step == "extract" and fresh:
        out.append("fresh_wording")
    return out


def approvals(path=None):
    path = Path(path or APPROVALS)
    return json.loads(path.read_text()) if path.exists() else {"approved": {}, "held": {}}


def text_sha(text):
    return hashlib.sha256(str(text).encode()).hexdigest()[:16]


def approval_for(group, rendered, record=None):
    """The approval that covers this exact draft text, or None when it was never approved or changed since."""
    a = (record or approvals())["approved"].get(group)
    return a if a and a.get("text_sha") == text_sha(rendered) else None


def review(seed, runs, models, data=DATA):
    result = library(seed, data)
    steps = {"extract": models["extract"], "classify": models.get("classify", models["extract"])}
    return result, flow.run(result, str(seed), runs, steps, decisions.load())


def draft_groups(seed, combined, result):
    """The drafting groups, each carrying the specialist's note when the specialist ruled a judge's flag on its last draft real.
    The note changes that group's input, so the recorder drafts only that group again."""
    notes = rulings.notes(seed)
    return [dict(g, specialist_note=notes[g["group"]]) if g["group"] in notes else g
            for g in drafting.groups(combined, result)]


def drafts(seed, runs, models, data=DATA):
    """(groups, {group: accepted draft}) for a seed, from the drafter's recordings."""
    result, combined = review(seed, runs, models, data)
    groups = draft_groups(seed, combined, result)
    return result, groups, replay.load("draft", str(seed), runs, [models["draft"]], items=groups)["accepted"]


def approved(seed, runs, models, data=DATA):
    """The approved drafts as the publisher takes them, with the clauses each one replaces."""
    result, groups, accepted = drafts(seed, runs, models, data)
    record = approvals()
    out = []
    for g in groups:
        d = accepted.get(g["group"])
        a = approval_for(g["group"], d["rendered"], record) if d else None
        if a:
            out.append({"group": g["group"], "title": d["title"], "text": d["rendered"], "attribute": g["attribute"],
                        "replaces": [c["clause"] for c in g["change"]], "approved_by": a.get("by"),
                        "applies_to": g["keep"]["document"]["applies_to"]})
    return result, out


COMPARE = {"extract": ("evals", 1), "classify": ("evals", 3), "judge": ("judge", 1), "draft": ("", 8),
           "assist": ("before", 1)}


def compare_items(step, seed, runs, models, data=DATA):
    """The model comparison's subset of a step's evaluation items, the same for every model: every extraction clause,
    every third labeled pair, every calibration draft, the first eight drafting groups and every preset question.
    Extraction moved from every third clause to all of them on 10/30, after GPT-6 Luna cleared 60 clauses and then
    read rules into the demo's clauses that don't state them."""
    kind, n = COMPARE[step]
    base = for_tag(step, f"{kind}-{seed}" if kind else str(seed), runs, models, data)
    return base[::n] if step in ("extract", "classify") else base[:n] if step == "draft" else base


def compare_drafts(seed, runs, models, data=DATA):
    """Every model's comparison drafts that models["judge"] may read, from judging.comparison_items. The step's own
    judge is the one config/models.json names, so turning routes on never changes what was read."""
    cfg = json.loads(HERE.joinpath("config", "models.json").read_text())
    vendor = {m["id"]: m["vendor"] for m in cfg["models"]}
    groups = compare_items("draft", seed, runs, configured_models(), data)
    by_model = {m: replay.load("draft", f"cmp-{seed}", runs, [m], items=groups)["accepted"] for m in vendor}
    return judging.comparison_items(groups, by_model, models["judge"], cfg["steps"]["judge"], vendor)


def for_tag(step, tag, runs, models, data=DATA):
    """The items one step reads for one tag."""
    kind, _, seed = tag.rpartition("-") if "-" in tag else ("", "", tag)
    if kind == "cmp":
        return compare_items(step, seed, runs, models, data)
    if kind == "drafts":
        return compare_drafts(seed, runs, models, data)
    if kind == "sample":
        return sample_items(seed, data)
    if tag == "fresh_wording":
        return inputs.fresh_items(json.loads(HERE.joinpath("evals", "fresh_wording.json").read_text()))
    sets = json.loads(data.joinpath("key", seed, "evals.json").read_text())
    if step == "extract":
        result = library(seed, data)
        return inputs.extract_items(result, [x["clause"] for x in sets["extraction"]] if kind == "evals" else None)
    if step == "classify":
        result = library(seed, data)
        if kind == "evals":
            return inputs.eval_pair_items(result, sets["pairs"])
        ai = replay.load("extract", seed, runs, [models["extract"]], items=inputs.extract_items(result))["accepted"]
        return combine.review(result, ai, decisions=decisions.load())["pairs"]
    if step == "draft":
        result, combined = review(seed, runs, models, data)
        return draft_groups(seed, combined, result)
    if step == "judge":
        if kind == "judge":
            return judging.calibration_items(sets["judge"])
        _, groups, accepted = drafts(seed, runs, models, data)
        return judging.draft_items(groups, accepted)
    if step == "assist":
        if kind == "before":
            result = library(seed, data)
            return assisting.items(publish.before(result), sets["assistant"])
        result, ok = approved(seed, runs, models, data)
        index, _ = publish.after(result, ok)
        return assisting.items(index, sets["assistant"]) if ok else []
    raise ValueError(f"no items for {step} {tag}")
