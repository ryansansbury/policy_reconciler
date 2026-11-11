"""Combine code's review with the AI steps' recorded outputs, under code's rules and the specialist's decisions.

The rule extractor's atoms join code's atoms, marked as read by the AI, except where code already read that rule in
that clause for certain, since code's reading wins. Comparison runs again over all of them. A comparison code can't
settle on its own is held back from the findings for one of six reasons:
- unit: the two durations share a number but not a unit, like 10 days and 10 business days;
- role_generic: one side names a general role, like "a manager";
- condition: one side carries a condition that may change the rule;
- actor_inferred: the AI inferred one side's actor instead of reading it;
- exception_path: the values match, but a statement leaves out a condition the rule's authority states, and staff
  following it act differently;
- added_condition: the values match, but a statement adds a condition the rule's authority doesn't state.
Two statements that carry the same condition agree, and they're never paired.
Three of those are groups the experts disagree on. Once the specialist decides a group, that decision settles its pairs by rule.
Every other held pair goes to the classifier, whose label decides it, and only "conflict" becomes a finding.
Everything else is kept with its label and rationale, so the page can show why a pair wasn't flagged.
"""
from engine import compare, lexicon, scope
from agents import decisions as decided, inputs, validate

UNSURE = {
    "unit": "The two deadlines share a number but not a unit.",
    "role_generic": "One side names a general role instead of one from the role list.",
    "condition": "One side carries a condition that may change the rule.",
    "actor_inferred": "One side's actor was inferred by the AI, not named.",
    "exception_path": "The values match, but the weaker document leaves out a condition the stronger one states.",
    "added_condition": "The values match, but the weaker document adds a condition the stronger one doesn't state.",
}


def ai_atom(clause_id, a, idx):
    d, s, c = idx[clause_id]
    attr = lexicon.L[a["attribute"]]
    sc = scope.clause_scope(c["text"], d["states"], d["lines"], scoped=attr.get("scoped", False))
    return {"clause": clause_id, "doc": d["key"], "doc_id": d["id"], "version": d["version"], "doc_type": d["type"],
            "effective": d["effective"], "attribute": a["attribute"], "value": validate.canonical(a["value"]),
            "value_text": a["quote"],
            "states": sc["states"], "lines": sc["lines"], "explicit": sc["explicit"] or bool(a.get("scope_quote")),
            "scope_text": sc["phrase"] or a.get("scope_quote"), "decided_by": "ai",
            "actor_inferred": bool(a.get("actor_inferred")), "condition": a.get("condition")}


def covers(a, b):
    """Whether statement a already states b's whole condition, so a leaves nothing of it out."""
    norm = lambda t: " ".join(str(t or "").lower().split())  # noqa: E731
    return norm(b.get("condition")) in norm(a.get("condition"))


def doubtful(x):
    """Whether one statement carries any of the doubts that keep code from settling it."""
    v = x["value"]
    return bool(x.get("condition") or (x.get("decided_by") == "ai" and x.get("actor_inferred"))
                or (v.get("type") == "role" and v.get("role") is None))


def certain_authority(x, current):
    """The strongest statement code can compare with x for certain that sets a different value, or None."""
    sure = [y for y in current if y["attribute"] == x["attribute"] and y["clause"] != x["clause"] and not doubtful(y)
            and y["value"] != x["value"] and scope.overlaps(x, y) and not scope.deliberate(x, y)
            and compare.standing(y) < compare.standing(x) and uncertain(y, x) is None]
    return min(sure, key=compare.standing) if sure else None


def uncertain(a, b):
    """The kind of doubt that keeps code from settling a comparison, or None when code can settle it."""
    va, vb = a["value"], b["value"]
    if va.get("type") == vb.get("type") == "duration" and va["n"] == vb["n"] and va["unit"] != vb["unit"]:
        return "unit"
    if any(x["value"].get("type") == "role" and x["value"].get("role") is None for x in (a, b)):
        return "role_generic"
    if any(x.get("condition") for x in (a, b)):
        return "condition"
    if any(x.get("decided_by") == "ai" and x.get("actor_inferred") for x in (a, b)):
        return "actor_inferred"
    return None


def review(result, ai_atoms=None, labels=None, decisions=None):
    """The combined review. ai_atoms is {clause: [atoms]} from the rule extractor, labels is {pair: label} from the
    classifier, and decisions is evals/decisions.json. Returns the findings, the classifier's queue, the pairs the specialist's
    decisions settled, and every AI decision with its reason."""
    ai_atoms, labels = ai_atoms or {}, labels or {}
    idx = inputs.clause_index(result)
    atoms = [dict(a) for a in result["atoms"]]
    code_read = {(a["clause"], a["attribute"]) for a in atoms}
    for cid in sorted(ai_atoms):
        atoms += [ai_atom(cid, a, idx) for a in ai_atoms[cid] if (cid, a["attribute"]) not in code_read]
    docs = result["documents"]
    found, variations = compare.conflicts(atoms, docs)
    older = compare.superseded(atoms, docs)
    live = decided.rule("older_version", decisions) == "conflict"
    for f in older:
        f["live"] = live
    by_clause = {}
    for a in atoms:
        by_clause.setdefault(a["clause"], []).append(a)

    def atom_of(cid, attr):
        return next(a for a in by_clause[cid] if a["attribute"] == attr)

    newest = compare.latest(docs)
    current = [a for a in atoms if a["version"] == newest[a["doc_id"]]]
    final, held = [], []
    for f in found:
        a, b = atom_of(f["clauses"][0], f["attribute"]), atom_of(f["clauses"][1], f["attribute"])
        kind = uncertain(a, b)
        if not kind:
            final.append(f)
            continue
        sure = certain_authority(b, current) if kind in ("condition", "actor_inferred") and not doubtful(b) else None
        if sure:
            final.append(dict(f, clauses=[sure["clause"], b["clause"]], authoritative=sure["clause"],
                              values=[sure["value"], b["value"]], texts=[sure["value_text"], b["value_text"]]))
        else:
            held.append((kind, a["clause"], b["clause"], f["attribute"]))
    seen = {inputs.pair_id(h[1], h[2]) for h in held}
    with_condition = [a for a in current if a.get("condition")]

    def same(a, b):
        return (a["attribute"] == b["attribute"] and a["clause"] != b["clause"] and a["value"] == b["value"]
                and not scope.deliberate(a, b))

    def hold(kind, stronger, weaker):
        pid = inputs.pair_id(stronger["clause"], weaker["clause"])
        if pid not in seen:
            seen.add(pid)
            held.append((kind, stronger["clause"], weaker["clause"], stronger["attribute"]))

    def authority_of(x):
        return min([y for y in current if same(x, y)] + [x], key=compare.standing)

    # A statement that leaves out the authority's condition is held once, against the authority.
    for y in current:
        top = authority_of(y)
        if top is not y and top.get("condition") and not covers(y, top):
            hold("exception_path", top, y)
    # A statement that adds a condition the authority doesn't state is held once, against the authority.
    for x in with_condition:
        top = authority_of(x)
        if top is not x and not covers(top, x):
            hold("added_condition", top, x)
    pairs, ruled = [], []
    for kind, a, b, attr in held:
        item = dict(inputs.classify_item(result, a, b, attr, lexicon.LABELS[attr], UNSURE[kind], idx), kind=kind)
        label = decided.rule(kind, decisions)
        if label:
            reason = decisions["decisions"][kind]["reason"]
            ruled.append(dict(item, label=label, rationale=reason))
            if label == "conflict":
                final.append({"type": "conflict", "attribute": attr, "clauses": [a, b], "authoritative": a,
                              "decided_by": "rule", "rationale": reason, "kind": kind,
                              "rule": "The specialist's decision for this group of disagreements"})
        else:
            pairs.append(item)
    decided_pairs = []
    for p in pairs:
        lab = labels.get(p["pair"])
        if not lab:
            continue
        decided_pairs.append(dict(p, label=lab["label"], rationale=lab["rationale"],
                                  quotes=[lab["quote_a"], lab["quote_b"]]))
        if lab["label"] == "conflict":
            final.append({"type": "conflict", "attribute": p["attribute"], "clauses": [p["a"]["clause"], p["b"]["clause"]],
                          "authoritative": p["a"]["clause"], "decided_by": "ai", "rationale": lab["rationale"],
                          "kind": p["kind"], "rule": "The classifier read the pair as a conflict"})
    waiting = [p for p in pairs if p["pair"] not in labels]
    return {"documents": docs, "atoms": atoms, "queue": result["queue"],
            "findings": final + older + [f for f in result["findings"] if f["type"] == "duplicate"],
            "variations": variations, "pairs": pairs, "ruled": ruled, "decided": decided_pairs, "waiting": waiting}
