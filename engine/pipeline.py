"""The code-only review of one library: parse, extract, compare, find duplicates and superseded versions.

Every step here is deterministic. The AI steps add to this result later. They never replace it, so the page can
always show what code alone decided.
"""
import time
from pathlib import Path

from engine import compare, duplicates, extract, parse


def run(folder):
    t0 = time.time()
    timings = {}

    def lap(name):
        nonlocal t0
        now = time.time()
        timings[name] = round(now - t0, 3)
        t0 = now

    docs, held = parse.parse_folder(Path(folder))
    lap("parse")
    atoms, queue = extract.extract(docs)
    lap("extract")
    found, variations = compare.conflicts(atoms, docs)
    lap("compare")
    older = compare.superseded(atoms, docs)
    lap("superseded")
    dups = duplicates.find(docs)
    lap("duplicates")
    clauses = sum(len(s["clauses"]) for d in docs for s in d["sections"])
    return {"documents": docs, "held": held, "atoms": atoms, "queue": queue,
            "findings": found + older + dups, "variations": variations, "timings": timings,
            "counts": {"documents": len(docs), "clauses": clauses, "atoms": len(atoms), "queue": len(queue),
                       "conflicts": len(found), "superseded": len(older), "duplicates": len(dups),
                       "variations": len(variations), "held": len(held)}}
