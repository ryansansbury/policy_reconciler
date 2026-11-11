"""One command builds everything from the seeds: the library, the store, the findings, the scores and the page.

    python3 build.py                     the page from the recorded results
    python3 build.py --profile general   the public version, with no client words
    python3 build.py --only generate     one stage, for development

Every stage is deterministic. AI steps are never called here. The build replays what the owner scripts recorded
and validates each run again before anything uses it.
"""
import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import json  # noqa: E402

from app import words  # noqa: E402
from generate import world  # noqa: E402

DEMO_SEED = 2026


def review_stage(profile=None, words=None):
    """The demo library's review: code alone, then with the AI steps' recordings replayed into it. The code-only
    review is kept in SQLite, and both are summarized for the page."""
    from agents import decisions, flow
    from engine import pipeline, store
    from evals import score
    result = pipeline.run(HERE.joinpath("data", "library", str(DEMO_SEED)))
    store.save(result, HERE.joinpath("data", "store", f"{DEMO_SEED}.sqlite"))
    key = score.load_key(DEMO_SEED)
    scored = score.score(result, key)
    from agents import items
    combined = flow.run(result, str(DEMO_SEED), models=items.step_models(), decisions=decisions.load())
    out = HERE.joinpath("data", "out")
    out.mkdir(parents=True, exist_ok=True)
    out.joinpath(f"review_{DEMO_SEED}.json").write_text(json.dumps(
        {"counts": result["counts"], "timings": result["timings"], "score": scored["summary"],
         "findings": result["findings"], "variations": result["variations"], "queue": result["queue"],
         "combined": {"score": score.score(combined, key)["summary"], "findings": combined["findings"],
                      "decided": combined["decided"], "waiting": len(combined["waiting"]), "ai": combined["ai"]}},
        indent=1, sort_keys=True) + "\n")
    return scored["summary"]


def ai_stage(profile=None, words=None):
    """Score whatever the AI steps recorded, each on the model its step runs on, into data/out/ai_scores.json."""
    from evals import score_ai
    r = score_ai.report()
    score_ai.OUT.parent.mkdir(parents=True, exist_ok=True)
    score_ai.OUT.write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    if r["audit_problems"]:
        raise SystemExit("The audit log and the recordings disagree: " + "; ".join(r["audit_problems"][:3]))
    return r


def page_stage(profile=None, words=None):
    """The page in site/, with the strip check on every profile."""
    from app import bundle, readme
    results = json.loads(HERE.joinpath("evals", "code_only.json").read_text())["totals"]
    from agents import items
    out = bundle.build(profile, DEMO_SEED, items.step_models(), results)
    readme.write(words)
    return out


def scale_stage(profile=None, words=None):
    """The scale library's code review, timed, and the AI cost estimate. It reruns only when the engine changes."""
    from evals import scale
    return scale.stage()


STAGES = (("generate", world.stage), ("review", review_stage), ("ai", ai_stage), ("scale", scale_stage),
          ("page", page_stage))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", default=words.default_profile(), choices=words.profiles())
    ap.add_argument("--only", choices=[name for name, _ in STAGES] or None)
    args = ap.parse_args(argv)
    w = words.load(args.profile)
    t0 = time.time()
    for name, stage in STAGES:
        if args.only and name != args.only:
            continue
        stage(profile=args.profile, words=w)
    print(f"Built the {args.profile} profile in {time.time() - t0:.1f} s ({len(STAGES)} stages).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
