"""Turn clauses into rule atoms with plain code, and say honestly which clauses code can't read.

An atom is one rule a clause sets: the attribute, the value with the exact words it came from, the actor and the
scope. A clause is certain when exactly one attribute matches with exactly one value and the actor it names. It's
uncertain when the cues match but the value is missing, doubled or conditional, or the actor isn't the one the rule
belongs to. Uncertain clauses go to the AI extractor's queue, and so does any clause that reads like a rule (it holds
a value, names a role or uses modal language) when no tracked rule's cue words match it. Code never guesses.
"""
from engine import lexicon, scope, values


def has(text, phrase):
    return phrase in text


def candidates(text):
    """Attributes whose every cue group appears in the clause and none of whose exclusions do."""
    low = text.lower()
    out = []
    for attr, spec in lexicon.L.items():
        if any(has(low, n) for n in spec.get("not", [])):
            continue
        if all(any(has(low, p) for p in group) for group in spec["cues"]):
            out.append(attr)
    return out


def conditional(text):
    low = " " + text.lower() + " "
    return any(m in low for m in lexicon.EXCEPTION_MARKERS)


def read_attribute(attr, text, roles_found, cells=None):
    """(value, span, reason) for one attribute in one clause. value is None with a reason when it's uncertain."""
    spec = lexicon.L[attr]
    if spec.get("actor") and spec["actor"] not in roles_found:
        return None, None, "the rule's actor isn't named"
    if spec["type"] == "role":
        found = values.find("role", cells[-1] if cells else text)
        if not found:
            return None, None, "a general role, not one from the role list" if values.generic_roles(text) else "no role"
        if len(found) > 1:
            return None, None, "more than one role"
        return found[0][0], found[0][1], None
    found = values.row_value(spec["type"], cells[-1]) if cells else values.find(spec["type"], text)
    if not found:
        return None, None, f"no {spec['type']} value"
    if len(found) > 1:
        return None, None, f"{len(found)} {spec['type']} values"
    if conditional(text) and spec["type"] != "modal":
        return None, None, "a condition that may change the value"
    return found[0][0], found[0][1], None


def value_text(clause, value, span, vtype):
    """The exact words the value came from: the value cell for a table row, or the matched span of the sentence."""
    if vtype == "modal":
        return clause["cells"][-1] if clause.get("cells") else value["modal"]
    source = clause["cells"][-1] if clause.get("cells") else clause["text"]
    return source[span[0]:span[1]]


def extract_clause(clause, doc):
    """(atoms, uncertain) for one clause. uncertain lists (attribute, reason) for the AI extractor's queue."""
    text = clause["text"]
    cands = candidates(text)
    if not cands:
        return [], []
    roles_found = {v["role"] for v, _ in values.find("role", text)}
    by_type = {}
    for attr in cands:
        by_type.setdefault(lexicon.L[attr]["type"], []).append(attr)
    atoms, uncertain = [], []
    for vtype, group in sorted(by_type.items()):
        readable = []
        for attr in group:
            value, span, reason = read_attribute(attr, text, roles_found, clause.get("cells"))
            if value is None:
                uncertain.append((attr, reason))
            else:
                readable.append((attr, value, span))
        if len(readable) > 1:
            best = max(len(lexicon.L[a]["cues"]) for a, _, _ in readable)
            top = [r for r in readable if len(lexicon.L[r[0]]["cues"]) == best]
            if len(top) > 1:
                uncertain += [(a, "two rules match equally") for a, _, _ in top]
                continue
            readable = top
        for attr, value, span in readable:
            sc = scope.clause_scope(text, doc["states"], doc["lines"], scoped=lexicon.L[attr].get("scoped", False))
            atoms.append({"clause": clause["id"], "doc": doc["key"], "doc_id": doc["id"], "version": doc["version"],
                          "doc_type": doc["type"], "effective": doc["effective"], "attribute": attr,
                          "value": value, "value_text": value_text(clause, value, span, vtype),
                          "states": sc["states"], "lines": sc["lines"],
                          "explicit": sc["explicit"], "scope_text": sc["phrase"], "decided_by": "code"})
    claimed = {a["attribute"] for a in atoms}
    uncertain = [(a, r) for a, r in uncertain if a not in claimed]
    if atoms and uncertain:
        uncertain = [(a, r) for a, r in uncertain if lexicon.L[a]["type"] not in {lexicon.L[x["attribute"]]["type"] for x in atoms}]
    return atoms, uncertain


def prepare(doc):
    """Add the document's type and scope, read from its id and its "Applies to" line."""
    doc["type"] = scope.doc_type(doc)
    doc["states"], doc["lines"] = scope.doc_scope(doc["applies_to"])
    return doc


def extract(docs):
    """(atoms, queue) across a library. The queue holds every uncertain clause with its reasons."""
    atoms, queue = [], []
    for doc in docs:
        prepare(doc)
        for sec in doc["sections"]:
            for cl in sec["clauses"]:
                got, unsure = extract_clause(cl, doc)
                atoms += got
                if not values.rule_like(cl["text"]):
                    continue
                if unsure:
                    queue.append({"clause": cl["id"], "doc": doc["key"], "text": cl["text"],
                                  "reasons": sorted({f"{a}: {r}" for a, r in unsure})})
                elif not got:
                    queue.append({"clause": cl["id"], "doc": doc["key"], "text": cl["text"],
                                  "reasons": ["it reads like a rule, but no tracked rule's cue words match"]})
    return atoms, queue
