"""The drafter's items and the code that checks its drafts.

There's one group per contradicted rule: the clause code named as the authority and every clause that disagrees with
it, which the consolidated section replaces. The drafter writes every value only as a placeholder, and the gate in
engine/gate.py checks each one. A draft may cite the rule's kept value in the authority or any current clause that
states the same value, and any other value the authority states, like an exception's deadline. The item lists each
placeholder with the words code fills in.
"""
import hashlib
import json

from agents import inputs, validate
from engine import compare, gate, lexicon

MAX_WORDS = 120
MODAL_WORDS = {"must": "must", "may": "may", "must_not": "must not"}


def words_for(atom):
    """The words a placeholder fills in. A modal rule's words are the plain verb, since code records the modal itself
    and a table row's cell reads "Required" or "Optional"."""
    v = atom["value"]
    return MODAL_WORDS[v["modal"]] if v.get("type") == "modal" else atom["value_text"]


def group_id(attribute, keep):
    return "g-" + hashlib.sha256(f"{attribute}|{keep}".encode()).hexdigest()[:8]


def groups(review, result):
    """The drafter's items from a combined review's contradictions, one per rule and kept value. Findings that keep
    the same value under different authorities share one group, kept by the strongest of those authorities, so a rule
    never gets two drafts that say the same thing."""
    idx = inputs.clause_index(result)
    newest = compare.latest(result["documents"])
    current = [a for a in review["atoms"] if a["version"] == newest[a["doc_id"]]]
    atom = {(a["clause"], a["attribute"]): a for a in current}
    found, keeps = {}, {}
    for f in review["findings"]:
        if f["type"] != "conflict" or (f["authoritative"], f["attribute"]) not in atom:
            continue
        top = atom[(f["authoritative"], f["attribute"])]
        k = (f["attribute"], json.dumps(top["value"], sort_keys=True))
        keeps.setdefault(k, []).append(top)
        g = found.setdefault(k, [])
        other = next(c for c in f["clauses"] if c != f["authoritative"])
        if other not in g:
            g.append(other)
    items = []
    for k, change in sorted(found.items()):
        attr, keep = k[0], min(keeps[k], key=compare.standing)["clause"]
        change = [c for c in change if c != keep]
        kept = next(a for a in current if a["clause"] == keep and a["attribute"] == attr)
        allowed = {f"{a['clause']}#value": words_for(a) for a in current
                   if a["attribute"] == attr and a["value"] == kept["value"]}
        others = [u["text"] for u in gate.spans(idx[keep][2]["text"]) if u["text"] != kept["value_text"]]
        allowed.update({f"{keep}#v{n}": t for n, t in enumerate(dict.fromkeys(others), 2)})
        items.append({"group": group_id(attr, keep), "rule": lexicon.LABELS[attr], "attribute": attr,
                      "type": lexicon.L[attr]["type"], "keep": inputs.clause_item(idx, keep),
                      "change": [inputs.clause_item(idx, c) for c in sorted(change)],
                      "allowed": dict(sorted(allowed.items())), "placeholder": f"{{clause:{keep}#value}}"})
    return items


def check(batch, reply):
    """(per-group drafts, problems). A draft is kept only when the gate and the writing rules pass."""
    try:
        data = validate.parse_json(reply)
    except ValueError as e:
        return {}, [f"the reply isn't valid JSON: {e}"]
    results = data.get("results")
    if not isinstance(results, list):
        return {}, ["the reply needs a results list"]
    by_id = {r.get("group"): r for r in results if isinstance(r, dict)}
    out, problems = {}, []
    for item in batch:
        r = by_id.get(item["group"])
        if r is None:
            problems.append(f"{item['group']}: no result")
            continue
        title, text = str(r.get("title") or "").strip(), str(r.get("text") or "").strip()
        p = []
        if not title or not text:
            p.append("a draft needs a title and a text")
        if len(text.split()) > MAX_WORDS:
            p.append(f"the text must stay under {MAX_WORDS} words")
        found, rendered = gate.check(text, item["allowed"], item["type"])
        p += found
        p += [f"the draft has {w}" for w in validate.holding_problems(title + " " + gate.bare(text))]
        if p:
            problems += [f"{item['group']}: {x}" for x in p]
        else:
            out[item["group"]] = {"title": title, "text": text, "rendered": rendered}
    return out, problems
