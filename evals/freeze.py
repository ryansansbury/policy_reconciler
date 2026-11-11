"""Freeze the engine or the prompts before a scored run, so nothing can be tuned to the held-out answers.

    python3 -m evals.freeze engine --note "why this version"
    python3 -m evals.freeze prompts --note "why this version"

Each freeze records hashes and a version number, and keeps every earlier version in its history. Tests fail when
the files change after a freeze. A new version is scored once on seeds no earlier version was scored on.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from agents import prompts

HERE = Path(__file__).resolve().parent.parent
ENGINE_FREEZE = HERE.joinpath("evals", "engine_freeze.json")
PROMPT_FREEZE = HERE.joinpath("evals", "prompt_freeze.json")


# The files that decide the findings. The gate, the diff, the search and the publisher live in engine/ too, but they
# never change what a review finds, so they sit outside the freeze.
DETECTION = ("__init__.py", "compare.py", "duplicates.py", "extract.py", "lexicon.py", "parse.py", "pipeline.py",
             "scope.py", "store.py", "values.py")


def engine_files():
    return [HERE.joinpath("engine", n) for n in DETECTION]


def engine_hash():
    h = hashlib.sha256()
    for p in engine_files():
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def engine_record(note):
    from engine import duplicates
    return {"engine": engine_hash(), "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                                               for p in engine_files()},
            "thresholds": {"duplicate_similarity": duplicates.MIN_SIM, "duplicate_run": duplicates.MIN_RUN},
            "note": note}


def prompt_record(note, steps=None, old=None):
    """The hashes of the prompts named, with any other step's frozen hash kept as it was."""
    kept = dict((old or {}).get("prompts", {}))
    kept.update({s: prompts.prompt_hash(s) for s in (steps or prompts.FILES)})
    return {"prompts": kept, "note": note, "steps": list(steps or prompts.FILES)}


def freeze(path, record):
    """Write a new version to path, moving the current one into its history."""
    old = json.loads(path.read_text()) if path.exists() else None
    history = (old.pop("history", []) + [old]) if old else []
    new = dict(record, version=(old["version"] + 1) if old else 1,
               frozen_at=datetime.now().isoformat(timespec="minutes"), history=history)
    path.write_text(json.dumps(new, indent=1, sort_keys=True) + "\n")
    return new


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=["engine", "prompts"])
    ap.add_argument("--note", required=True)
    ap.add_argument("--steps", default="", help="the prompts to freeze, like extract,classify, and every prompt if empty")
    args = ap.parse_args(argv)
    if args.what == "engine":
        new = freeze(ENGINE_FREEZE, engine_record(args.note))
        print(f"Engine version {new['version']} frozen: {new['engine'][:16]}")
    else:
        import json as _json
        old = _json.loads(PROMPT_FREEZE.read_text()) if PROMPT_FREEZE.exists() else None
        steps = [s.strip() for s in args.steps.split(",") if s.strip()] or None
        new = freeze(PROMPT_FREEZE, prompt_record(args.note, steps, old))
        print(f"Prompts version {new['version']} frozen: " + ", ".join(f"{k} {v[:12]}" for k, v in new["prompts"].items()))


if __name__ == "__main__":
    main()
