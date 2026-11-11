"""Score what the AI steps recorded, against gold the steps never saw.

    python3 -m evals.score_ai                       every recorded tag, for the default model
    python3 -m evals.score_ai --model claude-haiku

    the rule extractor   exact atoms on a seed's extraction set and on the hand-written clauses: every gold rule
                         found with its value, nothing invented, and the actor and scope agreement on the matches
    the classifier       accuracy by label on a seed's labeled pairs, with every miss listed. "conflict" gets its
                         own precision and recall, since it's the only label that becomes a finding
    the whole pipeline   code plus both AI steps on a seed's library, beside code alone, scored by evals/score.py

The disputed pairs are reported as answered and never scored until the experts' disagreement is decided. The
results go to data/out/ai_scores.json, which the page reads. After the scored round, --record-scored keeps the
held-out results once in evals/ai_scored.json with the versions they came from. It keeps only libraries no earlier
scored run used, and refuses when there are none.
"""
import argparse
import hashlib
import json
from pathlib import Path

from datetime import datetime

from agents import assisting, decisions, flow, inputs, items, judging, replay, validate
from engine import pipeline
from evals import freeze, score
from generate import world

HERE = Path(__file__).resolve().parent.parent
DATA = HERE.joinpath("data")
OUT = DATA.joinpath("out", "ai_scores.json")
SCORED = HERE.joinpath("evals", "ai_scored.json")
NOT_HELD_OUT = {str(s) for role in ("dev", "demo") for s in world.SEEDS[role]}


def vkey(value):
    v = validate.canonical(value)
    v.pop("generic", None)
    return json.dumps(v, sort_keys=True)


def score_extract(gold_items, answer):
    """gold_items are [{"clause", "text", "gold": [atoms]}], and answer is replay.load()'s result for them."""
    tp = fp = fn = 0
    actor_same = actor_seen = scope_same = scope_seen = 0
    outcome = {"exact": 0, "partial": 0, "missed": 0, "invented": 0, "empty": 0, "held": 0, "not_recorded": 0}
    misses = []
    for g in gold_items:
        cid = g["clause"]
        if cid in answer["held"]:
            outcome["held"] += 1
            misses.append({"clause": cid, "text": g["text"], "outcome": "held", "reasons": answer["held"][cid]})
            continue
        if cid not in answer["accepted"]:
            outcome["not_recorded"] += 1
            continue
        got = answer["accepted"][cid]
        want = {(a["attribute"], vkey(a["value"])): a for a in g["gold"]}
        have = {(a["attribute"], vkey(a["value"])): a for a in got}
        hit = set(want) & set(have)
        tp, fp, fn = tp + len(hit), fp + len(set(have) - hit), fn + len(set(want) - hit)
        for k in hit:
            if "actor" in want[k]:
                actor_seen += 1
                actor_same += want[k]["actor"] == have[k].get("actor")
            if "scope_text" in want[k]:
                scope_seen += 1
                scope_same += bool(want[k]["scope_text"]) == bool(have[k].get("scope_quote"))
        kind = ("empty" if not want and not have else "exact" if set(want) == set(have) else
                "invented" if not want else "missed" if not hit else "partial")
        outcome[kind] += 1
        if kind not in ("exact", "empty"):
            misses.append({"clause": cid, "text": g["text"], "outcome": kind,
                           "gold": [[a["attribute"], a["value"]] for a in g["gold"]],
                           "got": [[a["attribute"], a["value"], a.get("quote")] for a in got]})
    scored = sum(outcome[k] for k in ("exact", "partial", "missed", "invented", "empty"))
    return {"clauses": len(gold_items), "scored": scored, "outcomes": outcome,
            "exact_share": round((outcome["exact"] + outcome["empty"]) / scored, 3) if scored else None,
            "atoms": {"found": tp, "invented": fp, "missed": fn,
                      "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                      "recall": round(tp / (tp + fn), 3) if tp + fn else None},
            "actor_agreement": [actor_same, actor_seen], "scope_agreement": [scope_same, scope_seen],
            "misses": misses, "totals": replay.totals(answer["used"])}


def score_classify(pairs, answer):
    """pairs are a seed's labeled evaluation pairs, and answer is replay.load()'s result for their items."""
    by_label, confusion, misses, disputed = {}, {}, [], []
    held = not_recorded = 0
    said_conflict = right_conflict = gold_conflict = 0
    for p in pairs:
        pid = inputs.pair_id(p["a"], p["b"])
        if pid in answer["held"]:
            held += 1
            continue
        lab = answer["accepted"].get(pid)
        if lab is None:
            not_recorded += 1
            continue
        if p["label"] == "disputed":
            disputed.append({"item": p["item"], "said": lab["label"], "rationale": lab["rationale"]})
            continue
        row = by_label.setdefault(p["label"], [0, 0])
        row[1] += 1
        row[0] += lab["label"] == p["label"]
        confusion.setdefault(p["label"], {}).setdefault(lab["label"], 0)
        confusion[p["label"]][lab["label"]] += 1
        gold_conflict += p["label"] == "conflict"
        said_conflict += lab["label"] == "conflict"
        right_conflict += lab["label"] == "conflict" == p["label"]
        if lab["label"] != p["label"]:
            misses.append({"item": p["item"], "pair": pid, "gold": p["label"], "said": lab["label"],
                           "rationale": lab["rationale"], "a": p["a_text"], "b": p["b_text"]})
    right = sum(r[0] for r in by_label.values())
    asked = sum(r[1] for r in by_label.values())
    same = {"duplicate": "consistent"}
    decision_right = sum(n for gold, row in confusion.items() for said, n in row.items()
                         if same.get(said, said) == same.get(gold, gold))
    return {"pairs": len(pairs), "scored": asked, "accuracy": round(right / asked, 3) if asked else None,
            "decision_accuracy": round(decision_right / asked, 3) if asked else None,
            "variations_as_conflict": confusion.get("variation", {}).get("conflict", 0),
            "by_label": by_label, "confusion": confusion, "held": held, "not_recorded": not_recorded,
            "conflict": {"precision": round(right_conflict / said_conflict, 3) if said_conflict else None,
                         "recall": round(right_conflict / gold_conflict, 3) if gold_conflict else None},
            "misses": misses, "disputed": disputed, "totals": replay.totals(answer["used"])}


def pipeline_scores(seed, root=None, models=None, data=DATA):
    """Code alone and code with both AI steps, on one seed's library."""
    result = items.library(seed, data)
    key = score.load_key(seed, data.joinpath("key"))
    combined = flow.run(result, str(seed), root, models, decisions.load())
    dec = decisions.load()
    return {"code_only": score.score(result, key)["summary"], "combined": score.score(combined, key, dec),
            "ai": combined["ai"], "decided": [{k: d[k] for k in ("pair", "attribute", "label", "rationale", "reason")}
                                              for d in combined["decided"]]}


def recorded_tags(root=None, step="extract"):
    folder = Path(root or replay.RUNS).joinpath(step)
    return sorted(p.name for p in folder.iterdir() if p.is_dir()) if folder.exists() else []


def score_drafts(seed, root, models, data=DATA):
    """How many of a seed's groups have a draft that passed the gate, and why the rest were held."""
    groups = items.for_tag("draft", seed, root, models, data)
    r = replay.load("draft", seed, root, [models["draft"]], items=groups)
    recorded = len(r["accepted"]) + len(r["held"])
    return {"groups": len(groups), "passed": len(r["accepted"]), "held": r["held"], "missing": len(r["missing"]),
            "gate_pass_rate": round(len(r["accepted"]) / recorded, 3) if recorded else None,
            "totals": replay.totals(r["used"])}


def score_judge(tag, root, models, data=DATA):
    """On a calibration set, the judge against the experts by criterion. On a seed's drafts, what the judge found."""
    its = items.for_tag("judge", tag, root, models, data)
    r = replay.load("judge", tag, root, [models["judge"]], items=its)
    if tag.startswith("judge-"):
        experts = json.loads(data.joinpath("key", tag.split("-", 1)[1], "experts.json").read_text())["drafts"]
        return {"calibration": judging.calibration(experts, r["accepted"]), "held": r["held"],
                "totals": replay.totals(r["used"])}
    fails = {c: sorted(d for d, g in r["accepted"].items() if not g[c]["pass"]) for c in judging.CRITERIA}
    return {"graded": len(r["accepted"]), "fails": fails, "held": r["held"], "totals": replay.totals(r["used"])}


def score_assist(tag, root, models, data=DATA):
    seed = tag.split("-", 1)[1]
    questions = json.loads(data.joinpath("key", seed, "evals.json").read_text())["assistant"]
    its = items.for_tag("assist", tag, root, models, data)
    r = replay.load("assist", tag, root, [models["assist"]], items=its)
    rows = assisting.score(questions, r["accepted"], after=tag.startswith("after-"),
                           items_by_q={i["question"]: i for i in its})
    answerable = [x for x in rows if x.get("retrieved")]
    return {"questions": len(questions), "ok": sum(1 for x in rows if x.get("ok")), "rows": rows, "held": r["held"],
            "retrieved": len(answerable), "ok_answerable": sum(1 for x in answerable if x.get("ok")),
            "answers": r["accepted"], "totals": replay.totals(r["used"])}


def report(root=None, models=None, data=DATA):
    models = models or items.step_models()
    out = {"models": models, "seeds": {}, "extraction": {}, "pairs": {}, "drafts": {}, "judge": {}, "assist": {}}
    for tag in recorded_tags(root):
        if tag.isdigit():
            out["seeds"][tag] = pipeline_scores(tag, root, models, data)
        elif tag.startswith("evals-"):
            seed = tag.split("-", 1)[1]
            sets = json.loads(data.joinpath("key", seed, "evals.json").read_text())
            out["extraction"][tag] = score_extract(sets["extraction"], replay.load(
                "extract", tag, root, [models["extract"]], items.for_tag("extract", tag, root, models, data)))
            out["pairs"][tag] = score_classify(sets["pairs"], replay.load(
                "classify", tag, root, [models["classify"]], items.for_tag("classify", tag, root, models, data)))
        elif tag == "fresh_wording":
            fresh = json.loads(HERE.joinpath("evals", "fresh_wording.json").read_text())
            gold = [{"clause": c["id"], "text": c["text"], "gold": c["gold"]} for c in fresh["clauses"]]
            out["extraction"][tag] = score_extract(gold, replay.load(
                "extract", tag, root, [models["extract"]], inputs.fresh_items(fresh)))
    for tag in recorded_tags(root, "draft"):
        out["drafts"][tag] = score_drafts(tag, root, models, data)
    for tag in recorded_tags(root, "judge"):
        out["judge"][tag] = score_judge(tag, root, models, data)
    for tag in recorded_tags(root, "assist"):
        out["assist"][tag] = score_assist(tag, root, models, data)
    out["audit_problems"] = replay.audit_problems(root)
    return out


def versions():
    return {"engine": json.loads(freeze.ENGINE_FREEZE.read_text())["version"],
            "prompts": json.loads(freeze.PROMPT_FREEZE.read_text())["version"],
            "catalog": json.loads(HERE.joinpath("evals", "frozen.json").read_text())["version"]}


def latest(runs, part="seeds"):
    """The latest scored run that holds this part of the results, or None."""
    return next((run for run in reversed(runs) if run.get(part)), None)


def record_scored(r, path=SCORED, kept_versions=None):
    """Keep one scored round with the versions it measured. Seeds an earlier scored round used are refused."""
    kept_versions = kept_versions or versions()
    held_out = sorted(t for t in r["seeds"] if t not in NOT_HELD_OUT)
    held_out += sorted(t for t in r["extraction"] if t.startswith("evals-") and t[6:] not in NOT_HELD_OUT)
    held_out += ["fresh_wording"] if "fresh_wording" in r["extraction"] else []
    held_out += sorted(t for t in r.get("judge", {}) if t.startswith("judge-") and t[6:] not in NOT_HELD_OUT)
    old = json.loads(path.read_text()) if path.exists() else {"runs": []}
    used = {t for run in old["runs"] for t in run["held_out"]}
    held_out = [t for t in held_out if t not in used]
    if not held_out:
        raise SystemExit("Every held-out library here was already scored. A new version needs fresh seeds.")
    code = {p.relative_to(HERE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            for p in sorted(HERE.joinpath("agents").glob("*.py")) + [HERE.joinpath("evals", "decisions.json")] if p.exists()}
    old["runs"].append({"versions": kept_versions, "code": code, "at": datetime.now().isoformat(timespec="minutes"),
                        "models": r["models"],
                        "held_out": held_out,
                        "seeds": {t: v for t, v in r["seeds"].items() if t in held_out},
                        "extraction": {t: v for t, v in r["extraction"].items() if t in held_out},
                        "judge": {t: v for t, v in r.get("judge", {}).items() if t in held_out},
                        "pairs": {t: v for t, v in r["pairs"].items() if t in held_out}})
    path.write_text(json.dumps(old, indent=1, sort_keys=True) + "\n")
    return old["runs"][-1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", help="score one model's recordings for every step, instead of each step's own")
    ap.add_argument("--runs", default=None)
    ap.add_argument("--record-scored", action="store_true", help="keep the held-out results once in evals/ai_scored.json")
    args = ap.parse_args(argv)
    models = {k: args.model for k in items.step_models()} if args.model else None
    r = report(args.runs, models)
    if args.record_scored:
        kept = record_scored(r)
        print(f"Kept the scored round for {', '.join(kept['held_out'])} in evals/ai_scored.json.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    for tag, s in r["extraction"].items():
        print(f"extract {tag}: {s['outcomes']['exact'] + s['outcomes']['empty']} of {s['scored']} clauses exact, "
              f"atom precision {s['atoms']['precision']} and recall {s['atoms']['recall']}, {s['outcomes']['held']} held")
    for tag, s in r["pairs"].items():
        print(f"classify {tag}: accuracy {s['accuracy']} on {s['scored']} pairs, conflict precision "
              f"{s['conflict']['precision']} and recall {s['conflict']['recall']}, {s['held']} held")
    for seed, s in r["seeds"].items():
        c, a = s["code_only"], s["combined"]["summary"]
        print(f"seed {seed}: code alone {c['caught']} of {c['planted']} with {c['false_alarms']} false alarms, "
              f"code plus AI {a['caught']} with {a['false_alarms']} false alarms and {a['unexplained']} unexplained")
    print(f"audit: {len(r['audit_problems'])} problems")
    return r


if __name__ == "__main__":
    main()
