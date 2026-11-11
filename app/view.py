"""The page's view model: the review turned into what each tab shows, as plain data the renderer and the page script
share. Every count comes from the review. The answer key is read only for the evaluation panels, which say so.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from agents import decisions as decided_mod
from agents import inputs
from engine import lexicon, scope
from evals import agreement
from generate import bank, taxonomy

HERE = Path(__file__).resolve().parent.parent
TOPIC_OF_CODE = {code: t for t, code in taxonomy.TOPIC_CODES.items()}
CELLS = len(scope.ALL_STATES) * len(scope.ALL_LINES)
KINDS = ("exception_path", "unit", "role_generic", "older_version")


def fid(f):
    ids = sorted(f["clauses"]) or [f.get("doc", "")]
    return "f-" + hashlib.sha256(json.dumps([f["type"]] + ids).encode()).hexdigest()[:8]


def doc_topic(doc_id):
    return TOPIC_OF_CODE.get(doc_id.split("-")[1], "addenda")


def topic_name(t):
    return taxonomy.TOPICS[t]["short"] if t in taxonomy.TOPICS else "State addenda"


def breadth(states, lines):
    return round(len(set(states)) * len(set(lines)) / CELLS, 3)


def risk(f, cfg):
    """The ranking score. An older version the specialist decided is a live conflict weighs as a conflict."""
    t = cfg["topics"].get(f["topic"], {"severity": 1, "customer": False})
    cat = "conflict" if f.get("live") else f["type"]
    return round(cfg["category"][cat] * (t["severity"] + (cfg["customer_weight"] if t["customer"] else 0)
                                          + cfg["breadth_weight"] * f["breadth"]), 2)


def marks(text, atoms):
    """[start, end, kind] spans in a clause: the values, the stated scope and any condition, never overlapping."""
    spans = []
    for a in atoms:
        for kind, s in (("value", a.get("value_text")), ("scope", a.get("scope_text")), ("cond", a.get("condition"))):
            i = text.find(s) if s else -1
            if i >= 0 and all(i >= e or i + len(s) <= b for b, e, _ in spans):
                spans.append([i, i + len(s), kind])
    return sorted(spans)


class View:
    def __init__(self, result, combined, key=None, experts=None, decisions=None, risk_cfg=None, eval_pairs=None):
        self.result, self.combined, self.key = result, combined, key or {"items": []}
        self.eval_pairs = eval_pairs or []
        self.experts = experts or {"pairs": {}}
        self.decisions = decisions or {"decisions": {}}
        self.cfg = risk_cfg or json.loads(HERE.joinpath("config", "risk.json").read_text())
        self.idx = inputs.clause_index(result)
        self.atoms = {}
        for a in combined["atoms"]:
            self.atoms.setdefault(a["clause"], []).append(a)
        self.titles = {d["key"]: d["title"] for d in result["documents"]}

    def atom(self, cid, attr):
        return next((a for a in self.atoms.get(cid, []) if a["attribute"] == attr), None)

    # ------------------------------------------------------------------ the library and the run strip
    def library(self):
        docs = self.result["documents"]
        newest = {}
        for d in docs:
            newest[d["id"]] = max(newest.get(d["id"], 0), d["version"])
        return {"bank": bank.BANK_NAME, "states": len(scope.ALL_STATES), "documents": len(docs),
                "clauses": self.result["counts"]["clauses"], "older": sum(1 for d in docs if d["version"] < newest[d["id"]]),
                "by_type": dict(Counter(d["type"] for d in docs).most_common()),
                "by_format": dict(Counter(d["format"] for d in docs).most_common()),
                "by_topic": dict(Counter(topic_name(doc_topic(d["id"])) for d in docs).most_common()),
                "held": [h["file"] for h in self.result["held"]]}

    def strip(self):
        c, ai = self.combined, self.combined.get("ai", {})
        current = Counter(a["attribute"] for a in c["atoms"])
        found = Counter(f["type"] for f in c["findings"])
        return {"documents": len(self.result["documents"]), "clauses": self.result["counts"]["clauses"],
                "code_atoms": len(self.result["atoms"]), "queued": len(self.result["queue"]),
                "ai_atoms": ai.get("extract", {}).get("accepted", 0),
                "comparisons": sum(n * (n - 1) // 2 for n in current.values()),
                "code_conflicts": sum(1 for f in c["findings"] if f["type"] == "conflict" and f["decided_by"] == "code"),
                "variations": len(self.variations()), "to_classifier": len(c["pairs"]), "classified": len(c["decided"]),
                "waiting": len(c["waiting"]), "findings": sum(found.values()), "conflicts": found["conflict"],
                "duplicates": found["duplicate"], "superseded": found["superseded"]}

    def tiles(self):
        s = self.strip()
        open_groups = sum(1 for k in KINDS if k not in self.decisions["decisions"])
        held = len(self.result["held"]) + len(self.combined.get("ai", {}).get("extract", {}).get("held", {}))
        return {"conflicts": s["conflicts"], "duplicates": s["duplicates"], "superseded": s["superseded"],
                "variations": s["variations"], "decisions": open_groups, "held": held}

    # ------------------------------------------------------------------ findings
    def scope_of(self, f):
        if f["type"] == "conflict":
            a, b = (self.atom(c, f["attribute"]) for c in f["clauses"])
            return sorted(set(a["states"]) & set(b["states"])), sorted(set(a["lines"]) & set(b["lines"]))
        keys = f.get("docs") or [f["doc"]]
        ds = [self.idx_doc(k) for k in keys]
        return (sorted(set.intersection(*(set(d["states"]) for d in ds))),
                sorted(set.intersection(*(set(d["lines"]) for d in ds))))

    def idx_doc(self, doc_key):
        return next(d for d in self.result["documents"] if d["key"] == doc_key)

    def findings(self):
        out = []
        for f in self.combined["findings"]:
            attr = f.get("attribute") or (f["changes"][0]["attribute"] if f.get("changes") else None)
            topic = lexicon.L[attr]["topic"] if attr else doc_topic((f.get("docs") or [f["doc"]])[0].split("@")[0])
            states, lines = self.scope_of(f)
            row = {"id": fid(f), "type": f["type"], "topic": topic, "topic_name": topic_name(topic),
                   "attribute": attr, "label": lexicon.LABELS.get(attr, "") if attr else "",
                   "clauses": f["clauses"], "decided_by": f.get("decided_by", "code"), "rule": f.get("rule", ""),
                   "rationale": f.get("rationale", ""), "states": states, "lines": lines,
                   "breadth": breadth(states, lines), "customer": self.cfg["topics"].get(topic, {}).get("customer", False),
                   "live": bool(f.get("live"))}
            row["risk"] = risk(row, self.cfg)
            row.update(self.where(f))
            out.append(row)
        return sorted(out, key=lambda r: (-r["risk"], r["id"]))

    def where(self, f):
        """The documents a finding names, and which one wins."""
        if f["type"] == "conflict":
            keep, other = f["authoritative"], next(c for c in f["clauses"] if c != f["authoritative"])
            return {"keep": self.idx[keep][0]["key"], "change": self.idx[other][0]["key"],
                    "docs": [self.idx[c][0]["key"] for c in f["clauses"]]}
        if f["type"] == "duplicate":
            a, b = f["docs"]
            keep = min((a, b), key=lambda k: (scope_rank(self.idx_doc(k)), k))
            return {"keep": keep, "change": b if keep == a else a, "docs": f["docs"]}
        return {"keep": f["current"], "change": f["doc"], "docs": [f["current"], f["doc"]]}

    def side(self, cid, attr=None):
        d, s, c = self.idx[cid]
        atoms = [a for a in self.atoms.get(cid, []) if attr is None or a["attribute"] == attr]
        return {"clause": cid, "doc": d["key"], "title": d["title"], "type": d["type"], "version": d["version"],
                "effective": d["effective"], "applies_to": d["applies_to"], "heading": s["heading"], "text": c["text"],
                "marks": marks(c["text"], atoms),
                "atoms": [{"label": lexicon.LABELS.get(a["attribute"], a["attribute"]), "value_text": a["value_text"],
                           "decided_by": a.get("decided_by", "code"), "scope_text": a.get("scope_text"),
                           "condition": a.get("condition")} for a in atoms]}

    def detail(self, f):
        """Both sides of one finding, ready to set side by side."""
        if f["type"] == "conflict":
            return {"sides": [self.side(c, f["attribute"]) for c in f["clauses"]]}
        if f["type"] == "duplicate":
            src = next(x for x in self.combined["findings"] if fid(x) == f["id"])
            return {"runs": [[self.side(c) for c in src["first"]], [self.side(c) for c in src["second"]]]}
        src = next(x for x in self.combined["findings"] if fid(x) == f["id"])
        return {"changes": [{"label": lexicon.LABELS.get(ch["attribute"], ch["attribute"]),
                             "old": self.side(ch["old"], ch["attribute"]), "current": self.side(ch["current"], ch["attribute"])}
                            for ch in src["changes"]]}

    # ------------------------------------------------------------------ what wasn't flagged
    def variations(self):
        """One entry per clause that narrows a rule's scope on purpose, with every bank-wide statement it differs from."""
        out = {}
        for v in self.combined["variations"]:
            if v["reason"].startswith("Their scopes"):
                continue
            a, b = (self.atom(c, v["attribute"]) for c in v["clauses"])
            if a is None or b is None:
                continue
            narrow, wide = next(((x, y) for x, y in ((a, b), (b, a))
                                 if (x["explicit"] or x["doc_type"] == "addendum") and scope.narrower_somewhere(x, y)),
                                (a, b))
            e = out.setdefault(narrow["clause"], {"clause": narrow["clause"], "attribute": v["attribute"],
                                                  "label": lexicon.LABELS.get(v["attribute"], ""), "reason": v["reason"],
                                                  "value_text": narrow["value_text"], "others": []})
            if wide["clause"] not in e["others"]:
                e["others"].append(wide["clause"])
        return sorted(out.values(), key=lambda e: (e["attribute"], e["clause"]))

    def decoys(self):
        """The evaluation's planted look-alikes, read from the answer key, with why code never compared them."""
        out = []
        for it in self.key["items"]:
            if it["category"] != "N":
                continue
            read = [a["attribute"] for a in self.atoms.get(it["target"], [])]
            flagged = any(it["target"] in f["clauses"] for f in self.combined["findings"] if f["type"] == "conflict")
            out.append({"item": it["id"], "clause": it["target"], "text": self.idx[it["target"]][2]["text"],
                        "title": self.idx[it["target"]][0]["title"], "near": lexicon.LABELS.get(it["decoy_of"], ""),
                        "read": lexicon.LABELS.get(read[0], "") if read else "", "flagged": flagged})
        return out

    # ------------------------------------------------------------------ the experts' disagreements
    def decision_groups(self):
        pairs = {p["pair"]: p for p in self.eval_pairs}
        pair_kinds = decided_mod.kinds(self.eval_pairs, self.key)
        ex = self.experts["pairs"]
        names = list(ex)
        groups = []
        for kind in KINDS:
            ids = [pid for pid in pairs if pair_kinds.get(pid) == kind]
            if not ids:
                continue
            first = pairs[ids[0]]
            groups.append({"kind": kind, "count": len(ids),
                           "example": {"a": self.side_text(first["a"]), "b": self.side_text(first["b"])},
                           "experts": [{"key": n, "name": bank.EXPERTS[n]["name"], "role": bank.EXPERTS[n]["title"],
                                        "label": ex[n][ids[0]]["label"], "rationale": ex[n][ids[0]]["rationale"]}
                                       for n in names],
                           "decision": self.decisions["decisions"].get(kind)})
        labels = {n: {pid: v["label"] for pid, v in ex[n].items()} for n in names}
        before = agreement.kappa(*(labels[n] for n in names)) if len(names) == 2 else None
        after = agreement.kappa(*(decided_mod.apply(labels[n], pair_kinds, self.decisions) for n in names)) \
            if len(names) == 2 else None
        return {"groups": groups, "kappa_before": before, "kappa_after": after,
                "decided": len(self.decisions["decisions"]), "version": self.decisions.get("key_version", 1)}

    def side_text(self, cid):
        d, s, c = self.idx[cid]
        return {"clause": cid, "title": d["title"], "type": d["type"], "version": d["version"], "text": c["text"]}

    def build(self):
        fs, vs = self.findings(), self.variations()
        ai = self.combined.get("ai", {})
        totals = [ai[s]["totals"] for s in ("extract", "classify") if s in ai]
        return {"timings": self.result["timings"],
                "ai_totals": {"calls": sum(t["calls"] for t in totals), "dollars": sum(t["dollars"] for t in totals)},
                "library": self.library(), "strip": self.strip(), "tiles": self.tiles(), "findings": fs,
                "details": {f["id"]: self.detail(f) for f in fs}, "variations": vs,
                "variation_sides": {v["clause"]: self.side(v["clause"], v["attribute"]) for v in vs},
                "decoys": self.decoys(), "decisions": self.decision_groups(), "risk": self.cfg,
                "titles": self.titles}


def scope_rank(doc):
    from engine import compare
    return compare.TYPE_RANK.get(doc["type"], 4)
