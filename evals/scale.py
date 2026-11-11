"""Cost and time at scale: the 1,853-document library through every deterministic stage, timed, and the AI cost
estimated from what each step costs per item on the demo library.

    the code review   parse, extract, compare and duplicates on the scale seed, run in full and timed
    the AI steps      the items that reach each step at scale, times the measured tokens per item on the demo
                      library, times the step's model's list prices, shown with its arithmetic and labeled an estimate.
                      Claude's tokens leave out the client context its recordings carry on every call, as the API would bill

The result goes to data/out/scale.json. It reruns only when the engine or the scale library changes, since the full
review of the scale library takes about fifteen seconds.
"""
import json
import time
from pathlib import Path

from agents import combine, drafting, items, replay
from engine import pipeline
from evals import freeze

HERE = Path(__file__).resolve().parent.parent
OUT = HERE.joinpath("data", "out", "scale.json")
SEED, DEMO = "9001", "2026"


def measure():
    t0 = time.perf_counter()
    result = pipeline.run(HERE.joinpath("data", "scale", SEED))
    seconds = round(time.perf_counter() - t0, 2)
    review = combine.review(result)
    return {"documents": result["counts"]["documents"], "clauses": result["counts"]["clauses"], "seconds": seconds,
            "timings": result["timings"], "items": {"extract": len(result["queue"]), "classify": len(review["pairs"]),
                                                    "draft": len(drafting.groups(review, result))}}


def per_item(step, tag, models):
    """Measured input and output tokens per item for one step on the demo library, or None before a recording."""
    used = replay.load(step, tag, None, [models[step]])["used"]
    n = sum(len(r["input"]) for r in used)
    if not n:
        return None
    t = replay.totals(used)
    return {"input": t["api_input_tokens"] / n, "output": t["output_tokens"] / n}


def estimate(scale, models=None):
    """Each step's estimated cost at scale with the numbers behind it."""
    models = models or items.step_models()
    prices = {m["id"]: m for m in json.loads(HERE.joinpath("config", "models.json").read_text())["models"]}
    out = {}
    for step, n in scale["items"].items():
        tokens = per_item(step, DEMO, models)
        if tokens is None:
            out[step] = {"items": n, "model": models[step], "estimate": None}
            continue
        p = prices[models[step]]
        dollars = n * (tokens["input"] * p["price_in"] + tokens["output"] * p["price_out"]) / 1e6
        out[step] = {"items": n, "model": models[step], "tokens_in": round(tokens["input"]), "tokens_out": round(tokens["output"]),
                     "price_in": p["price_in"], "price_out": p["price_out"], "estimate": round(dollars, 2)}
    return out


def sample_check(ai, models=None):
    """The estimate's tokens per item against the scale library's own sample, once the owner has recorded it."""
    models = models or items.step_models()
    real = per_item("extract", f"sample-{SEED}", models)
    est = ai.get("extract", {})
    if real is None or est.get("estimate") is None:
        return None
    return {"sample": items.SAMPLE, "estimated_in": est["tokens_in"], "measured_in": round(real["input"]),
            "estimated_out": est["tokens_out"], "measured_out": round(real["output"]),
            "off_by": round((real["input"] + real["output"]) / (est["tokens_in"] + est["tokens_out"]) - 1, 3)}


def stage(profile=None, words=None):
    frozen = json.loads(HERE.joinpath("evals", "frozen.json").read_text())
    stamp = {"engine": freeze.engine_hash(), "library": frozen["seeds"][SEED]["library"]}
    old = json.loads(OUT.read_text()) if OUT.exists() else None
    scale = old["scale"] if old and old.get("stamp") == stamp else measure()
    ai = estimate(scale)
    data = {"stamp": stamp, "scale": scale, "ai": ai, "sample_check": sample_check(ai)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    return data
