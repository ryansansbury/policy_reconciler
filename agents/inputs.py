"""Build what each AI step sees: the clause or the pair, with just enough document context to read it.

The rule extractor gets each queued clause with its heading and its document's title, type and "Applies to" line.
The classifier gets both clauses of a pair with their documents' type, version and date, the rule they state, and
code's reason for not deciding. Neither step ever sees the answer key. The evaluation sets are built the same way,
so a model is measured on exactly what it would see in a review.
"""
import hashlib
import json

from engine import lexicon

EVAL_REASON = "This pair comes from the evaluation set, so code's own reading isn't shared."


def clause_index(result):
    out = {}
    for d in result["documents"]:
        for s in d["sections"]:
            for c in s["clauses"]:
                out[c["id"]] = (d, s, c)
    return out


def doc_context(d):
    return {"title": d["title"], "type": d.get("type"), "version": d["version"], "effective": d["effective"],
            "applies_to": d["applies_to"]}


def clause_item(idx, cid):
    d, s, c = idx[cid]
    return {"clause": c["id"], "text": c["text"], "heading": s["heading"],
            "document": {k: v for k, v in doc_context(d).items() if k in ("title", "type", "applies_to")}}


def extract_items(result, ids=None):
    """The rule extractor's items: every clause code queued, or the clauses named."""
    idx = clause_index(result)
    ids = [q["clause"] for q in result["queue"]] if ids is None else ids
    return [clause_item(idx, cid) for cid in ids]


def fresh_items(fresh):
    """The hand-written clauses of evals/fresh_wording.json, framed as one procedure."""
    ctx = fresh["context"]
    doc = {"title": ctx["title"], "type": ctx["type"], "applies_to": ctx["applies_to"]}
    return [{"clause": c["id"], "text": c["text"], "heading": "Requirements", "document": doc} for c in fresh["clauses"]]


def pair_id(a, b):
    return "pair-" + hashlib.sha256(json.dumps(sorted([a, b])).encode()).hexdigest()[:10]


def classify_item(result, a, b, attribute, label, reason, idx=None):
    idx = idx or clause_index(result)
    da, sa, ca = idx[a]
    db, sb, cb = idx[b]
    return {"pair": pair_id(a, b), "rule": label, "attribute": attribute, "reason": reason,
            "a": {"clause": a, "text": ca["text"], "heading": sa["heading"], "document": doc_context(da)},
            "b": {"clause": b, "text": cb["text"], "heading": sb["heading"], "document": doc_context(db)}}


def eval_pair_items(result, pairs):
    """The classifier's items for a labeled evaluation set. The rule named is the one code read in either clause,
    and none when code read no tracked rule in either."""
    idx = clause_index(result)
    read = {}
    for a in result["atoms"]:
        read.setdefault(a["clause"], a["attribute"])
    out = []
    for p in pairs:
        attr = read.get(p["a"]) or read.get(p["b"])
        out.append(classify_item(result, p["a"], p["b"], attr, lexicon.LABELS[attr] if attr else None, EVAL_REASON,
                                 idx))
    return out


def batches(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]

