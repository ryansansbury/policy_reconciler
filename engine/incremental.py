"""Rerun only what a change touches. Every section has a fingerprint, the hash of its clauses' text. When one clause
changes, only the sections whose fingerprints changed are read again, and only the rules those sections state are
compared again. Every other atom and finding is reused as it was.

The page's "Change a rule" control shows one such change, precomputed by the build: what reran, what was reused, the
time against a full run, and the findings the change created or cleared.
"""
import copy
import hashlib
import time

from engine import compare, extract, pipeline


def section_key(clause_id):
    return clause_id.rsplit("/", 1)[0]


def fingerprints(docs):
    out = {}
    for d in docs:
        for n, s in enumerate(d["sections"], 1):
            out[f"{d['key']}/s{n}"] = hashlib.sha256("\n".join(c["text"] for c in s["clauses"]).encode()).hexdigest()
    return out


def change_clause(docs, clause_id, old_words, new_words):
    """A copy of the parsed documents with one clause's words changed."""
    out = copy.deepcopy(docs)
    for d in out:
        for s in d["sections"]:
            for c in s["clauses"]:
                if c["id"] == clause_id:
                    c["text"] = c["text"].replace(old_words, new_words, 1)
                    if c.get("cells"):
                        c["cells"] = [x.replace(old_words, new_words, 1) for x in c["cells"]]
    return out


def rerun(result, docs):
    """What changed between the reviewed library and these documents, and the review with only that redone."""
    t0 = time.perf_counter()
    before, after = fingerprints(result["documents"]), fingerprints(docs)
    changed = sorted(k for k in after if before.get(k) != after[k])
    kept = [a for a in result["atoms"] if section_key(a["clause"]) not in changed]
    fresh, reread = [], 0
    for d in docs:
        for n, s in enumerate(d["sections"], 1):
            if f"{d['key']}/s{n}" in changed:
                for c in s["clauses"]:
                    reread += 1
                    fresh += extract.extract_clause(c, d)[0]
    touched = {a["attribute"] for a in fresh} | {a["attribute"] for a in result["atoms"]
                                                 if section_key(a["clause"]) in changed}
    atoms = kept + fresh
    found, _ = compare.conflicts([a for a in atoms if a["attribute"] in touched], docs)
    reused = [f for f in result["findings"] if f["type"] == "conflict" and f["attribute"] not in touched]
    old = {tuple(f["clauses"]) for f in result["findings"] if f["type"] == "conflict" and f["attribute"] in touched}
    new = {tuple(f["clauses"]) for f in found}
    seconds = time.perf_counter() - t0
    return {"changed_sections": changed, "clauses_reread": reread, "rules_recompared": sorted(touched),
            "findings_reused": len(reused), "sections_total": len(after), "seconds": round(seconds, 4),
            "created": sorted(new - old), "cleared": sorted(old - new)}


def full_seconds(folder):
    t0 = time.perf_counter()
    pipeline.run(folder)
    return round(time.perf_counter() - t0, 3)
