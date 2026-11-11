"""The evaluation sets, drawn from each seed's planted library and frozen with the catalog.

    extraction  clauses with their gold atoms, for the rule extractor
    pairs       clause pairs with their gold labels, for the conflict classifier and the whole pipeline
    judge       consolidated drafts with known defects, for calibrating the judge
    assistant   questions with gold answers and citations, for the before-and-after assistant
"""
from generate import library, taxonomy
from generate.values import key as vkey
from generate.values import render

HEDGES = ("generally", "in most cases", "where appropriate", "as needed")


def clause_index(docs):
    out = {}
    for d in docs:
        for si, s in enumerate(d["sections"]):
            for c in s["clauses"]:
                out[c["id"]] = (d, s, c)
    return out


def context(d, s):
    return {"doc": d["key"], "doc_id": d["id"], "title": d["title"], "type": d["type"], "version": d["version"],
            "effective": d["effective"], "states": d["states"], "lines": d["lines"], "heading": s["heading"]}


def extraction_set(rng, docs, key, size=150, non_rules=30):
    idx = clause_index(docs)
    planted = {cid for i in key["items"] for cid in i.get("touched", [])}
    rules = [cid for cid, (d, s, c) in idx.items() if c["kind"] in ("rule", "row")]
    must = sorted(cid for cid in rules if cid in planted)
    rest = sorted(cid for cid in rules if cid not in planted)
    rng.shuffle(rest)
    chosen = (must + rest)[:size]
    others = sorted(cid for cid, (d, s, c) in idx.items() if c["kind"] in ("step", "text"))
    rng.shuffle(others)
    out = []
    for cid in sorted(chosen) + sorted(others[:non_rules]):
        d, s, c = idx[cid]
        out.append({"clause": cid, "text": c["text"], "kind": c["kind"], "context": context(d, s),
                    "gold": [{k: a[k] for k in ("attribute", "value", "value_text", "actor", "actor_inferred",
                                                "lines", "states", "scope_text") if k in a} for a in c["atoms"]]})
    return out


def pairs_set(rng, docs, key, consistent=40, unrelated=20):
    idx = clause_index(docs)
    out = []

    def pair(a, b, label, category, item=None):
        out.append({"pair": f"pair-{len(out) + 1:03d}", "a": a, "b": b, "label": label, "category": category,
                    "item": item})

    for it in key["items"]:
        if it["category"] == "D":
            pair(it["source"][0], it["copy"][0], "duplicate", "D", it["id"])
        else:
            pair(it["anchor"], it["target"], it["label"], it["category"], it["id"])
    used = {cid for p in out for cid in (p["a"], p["b"])}
    groups = {}
    for d, c, a in library.rule_instances(docs, include_decoys=False):
        if d["status"] != "current" or c["id"] in used or c["plants"]:
            continue
        attr = taxonomy.BY_ID[a["attribute"]]
        canon = next((v for ls, v in attr["canonical"] if set(ls) & set(a["lines"])), None)
        if canon is None or vkey(a["value"]) != vkey(canon):
            continue
        groups.setdefault((a["attribute"], tuple(sorted(a["lines"]))), []).append(c["id"])
    keys = sorted(k for k, v in groups.items() if len(v) >= 2)
    made, tries = 0, 0
    while made < consistent and tries < 1000:
        tries += 1
        k = rng.choice(keys)
        a, b = rng.sample(groups[k], 2)
        if idx[a][0]["key"] == idx[b][0]["key"] or a in used or b in used:
            continue
        used.update({a, b})
        pair(a, b, "consistent", "consistent")
        made += 1
    by_topic = {}
    for d, c, a in library.rule_instances(docs, include_decoys=False):
        if d["status"] == "current" and c["id"] not in used and not c["plants"]:
            by_topic.setdefault(a["topic"], []).append((c["id"], a["attribute"]))
    topics = sorted(t for t, v in by_topic.items() if len({x[1] for x in v}) >= 2)
    made, tries = 0, 0
    while made < unrelated and tries < 1000:
        tries += 1
        t = rng.choice(topics)
        (a, attr_a), (b, attr_b) = rng.sample(by_topic[t], 2)
        if attr_a == attr_b or a in used or b in used:
            continue
        used.update({a, b})
        pair(a, b, "unrelated", "unrelated")
        made += 1
    for p in out:
        for side in ("a", "b"):
            d, s, c = idx[p[side]]
            p[side + "_text"] = c["text"]
            p[side + "_context"] = context(d, s)
    return out


def judge_set(rng, docs, key, size=30):
    """Consolidated drafts with known defects. Each draft says what its sources require, and the gold grades say
    which of four criteria it meets: it keeps every rule, adds none, keeps every scope, and reads plainly."""
    idx = clause_index(docs)
    conflicts = [i for i in key["items"] if i["category"] in ("C", "P")]
    variations = [i for i in key["items"] if i["category"] == "V" and i.get("origin") != "canonical"]
    out = []
    defects = ["clean", "dropped_rule", "added_rule", "unclear", "lost_scope"]
    for n in range(size):
        defect = defects[n % len(defects)]
        if defect == "lost_scope" and variations:
            it = variations[(n // len(defects)) % len(variations)]
        else:
            it = conflicts[(n // len(defects) * 3 + n) % len(conflicts)]
        anchor_text = idx[it["anchor"]][2]["text"]
        attr = taxonomy.BY_ID[it["attribute"]]
        siblings = [a for a in taxonomy.RULES if a["topic"] == attr["topic"] and a["id"] != attr["id"]
                    and a["type"] != "modal"]
        sib = siblings[n % len(siblings)] if siblings else None
        sib_value = sib["canonical"][0][1] if sib else None
        sib_text = library.render_rule(sib, sib_value, library.pick_family(rng, sib, sib_value), None,
                                       list(sib["canonical"][0][0]))[0] if sib else ""
        sources = [it["anchor"]] + ([it["target"]] if it["category"] == "V" else [])
        sentences = [anchor_text] + ([idx[it["target"]][2]["text"]] if it["category"] == "V" else []) + \
                    ([sib_text] if sib_text else [])
        grades = {"keeps_rules": True, "adds_no_rule": True, "keeps_scope": True, "plain": True}
        draft = list(sentences)
        if defect == "dropped_rule" and len(draft) > 1:
            draft.pop()
            grades["keeps_rules"] = False
        elif defect == "added_rule":
            extra_attr = [a for a in taxonomy.RULES if a["topic"] != attr["topic"] and a["type"] == "money"][n % 5]
            wrong = extra_attr["alts"][0]
            draft.append(library.render_rule(extra_attr, wrong, "a", None, list(extra_attr["lines"]))[0])
            grades["adds_no_rule"] = False
        elif defect == "unclear":
            hedge = HEDGES[n % len(HEDGES)]
            draft = [s[:-1] + f", {hedge}." for s in draft]
            grades["plain"] = False
        elif defect == "lost_scope" and it["category"] == "V":
            draft[1] = draft[1].split(",", 1)[1].strip()
            draft[1] = draft[1][0].upper() + draft[1][1:]
            grades["keeps_scope"] = False
        out.append({"draft": f"draft-{n + 1:02d}", "item": it["id"], "defect": defect, "sources": sources,
                    "source_text": sentences, "text": " ".join(draft), "gold": grades})
    return out


def assistant_set(rng, docs, key, size=10):
    idx = clause_index(docs)
    seen, out = set(), []
    for it in key["items"]:
        if it["category"] not in ("C", "P") or it["attribute"] in seen:
            continue
        attr = taxonomy.BY_ID[it["attribute"]]
        if not attr["question"]:
            continue
        seen.add(attr["id"])
        canon = it["values"]["canonical"]
        out.append({"question": attr["question"], "attribute": attr["id"], "item": it["id"],
                    "gold_value": canon, "gold_text": render(canon) if canon["type"] != "modal" else canon["modal"],
                    "gold_citation": it["anchor"], "conflicting": it["target"],
                    "before": "The library disagrees, so an answer must flag both sources.",
                    "after": "One consolidated rule, cited once."})
        if len(out) >= size:
            break
    return out


def build(rng, docs, key):
    return {"extraction": extraction_set(rng, docs, key), "pairs": pairs_set(rng, docs, key),
            "judge": judge_set(rng, docs, key), "assistant": assistant_set(rng, docs, key)}

