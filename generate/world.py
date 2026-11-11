"""Build the synthetic world for every seed: the documents the engine reads, and the gold it never sees.

    data/library/<seed>/   the documents, in DOCX, HTML and Markdown
    data/key/<seed>/       plan.json (every clause with its gold atoms), key.json (the planted catalog),
                           evals.json and experts.json
    data/scale/<seed>/     the 2,000-document library for the cost-at-scale run, with its counts

Every seed rebuilds byte for byte. evals/frozen.json records the hashes, and a test fails if they drift, since a
changed catalog after scoring would let the checks be tuned to the answers.
"""
import argparse
import hashlib
import json
import random
import shutil
from datetime import datetime
from pathlib import Path

from generate import catalog, evalsets, experts, library, writers

HERE = Path(__file__).resolve().parent.parent
DATA = HERE.joinpath("data")
SEEDS = {"dev": [11, 23], "heldout": [4211, 5309, 7717], "heldout_b": [6101, 6202, 6303], "heldout_c": [8101, 8202, 8303],
         "demo": [2026], "scale": [9001]}
SCALE = 10


def dump(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def folder_hash(folder):
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(folder).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


CONTENT_FILES = ("bank.py", "catalog.py", "content.py", "evalsets.py", "experts.py", "library.py", "taxonomy.py",
                 "values.py", "writers.py")


def generator_hash():
    """A fingerprint of every file that decides what gets generated. This orchestration file isn't one of them."""
    h = hashlib.sha256()
    for p in sorted(HERE.joinpath("generate", n) for n in CONTENT_FILES):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def build_seed(seed, role, root=DATA):
    scale = SCALE if role == "scale" else 1
    rng = random.Random(seed)
    docs = library.build(rng, scale)
    key = catalog.plant(rng, docs, scale)
    lib = root.joinpath("scale" if role == "scale" else "library", str(seed))
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir(parents=True)
    for d in sorted(docs, key=lambda x: x["key"]):
        d["file"] = writers.write(d, lib)
    out = {"library": folder_hash(lib), "documents": len(docs), "counts": key["counts"]}
    if role != "scale":
        evals = evalsets.build(random.Random(seed + 1), docs, key)
        items = {i["id"]: i for i in key["items"]}
        labels = experts.label_pairs(evals["pairs"], items)
        grades = experts.grade_drafts(evals["judge"])
        kd = root.joinpath("key", str(seed))
        if kd.exists():
            shutil.rmtree(kd)
        kd.mkdir(parents=True)
        kd.joinpath("plan.json").write_text(dump({"seed": seed, "role": role, "documents": docs}), encoding="utf-8")
        kd.joinpath("key.json").write_text(dump(dict(key, seed=seed, role=role)), encoding="utf-8")
        kd.joinpath("evals.json").write_text(dump(evals), encoding="utf-8")
        kd.joinpath("experts.json").write_text(dump({"pairs": labels, "drafts": grades}), encoding="utf-8")
        out.update(key=folder_hash(kd), eval_sizes={k: len(v) for k, v in evals.items()})
    return out


def build_all(roles=None, root=DATA):
    result = {"generator": generator_hash(), "seeds": {}}
    for role, seeds in SEEDS.items():
        if roles and role not in roles:
            continue
        for seed in seeds:
            result["seeds"][str(seed)] = dict(build_seed(seed, role, root), role=role)
    return result


def up_to_date(want, root=DATA):
    """True when the generator and every seed's files on disk already match the freeze, so nothing needs rebuilding."""
    if generator_hash() != want["generator"]:
        return False
    for seed, info in want["seeds"].items():
        lib = root.joinpath("scale" if info["role"] == "scale" else "library", seed)
        if not lib.exists() or folder_hash(lib) != info["library"]:
            return False
        if info.get("key"):
            kd = root.joinpath("key", seed)
            if not kd.exists() or folder_hash(kd) != info["key"]:
                return False
    return True


def freeze_new_seeds(root=DATA):
    """Build every seed that isn't in the freeze yet and add its hashes. The generator must still match the freeze,
    so a new seed is a fresh draw from the same frozen catalog and never a change to it."""
    path = HERE.joinpath("evals", "frozen.json")
    want = json.loads(path.read_text())
    if generator_hash() != want["generator"]:
        raise SystemExit("The generator changed after the freeze, so a new seed would come from a different catalog.")
    added = []
    for role, seeds in SEEDS.items():
        for seed in seeds:
            if str(seed) not in want["seeds"]:
                want["seeds"][str(seed)] = dict(build_seed(seed, role, root), role=role)
                added.append(seed)
    if added:
        want.setdefault("added", []).append({"seeds": added, "at": datetime.now().isoformat(timespec="minutes")})
        path.write_text(dump(want), encoding="utf-8")
    return added


def stage(profile=None, words=None):
    """The build stage: regenerate every seed unless the files on disk already match evals/frozen.json, and fail if
    a regenerated seed doesn't match the freeze."""
    frozen = HERE.joinpath("evals", "frozen.json")
    if frozen.exists():
        missing = [s for ss in SEEDS.values() for s in ss if str(s) not in json.loads(frozen.read_text())["seeds"]]
        if missing:
            raise SystemExit(f"Seeds {missing} aren't in evals/frozen.json yet. "
                             "Run python3 -m generate.world --freeze-new-seeds")
    if frozen.exists() and up_to_date(json.loads(frozen.read_text())):
        return {"skipped": "the generated world already matches the freeze"}
    result = build_all()
    if frozen.exists():
        want = json.loads(frozen.read_text())
        drift = [s for s, v in result["seeds"].items()
                 if want["seeds"].get(s, {}).get("library") != v["library"]
                 or want["seeds"].get(s, {}).get("key") != v.get("key")]
        if drift:
            raise SystemExit(f"The generated world no longer matches evals/frozen.json for seeds {drift}. "
                             "A change after the freeze needs a new catalog version.")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the synthetic world.")
    ap.add_argument("--freeze-new-seeds", action="store_true", help="build seeds that aren't frozen yet and add them")
    if ap.parse_args().freeze_new_seeds:
        print(f"Added seeds {freeze_new_seeds()} to evals/frozen.json.")
