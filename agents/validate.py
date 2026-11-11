"""Check every AI reply with code before anything uses it.

The rule extractor's atoms must name a tracked attribute, carry a value of that attribute's type, and quote the
clause word for word, and the quote must hold the value when code reads it back. The classifier's labels must come
from the fixed list, its quotes must be in their clauses, and its rationale may use only numbers the pair's clauses
and documents hold, like a version or a date.
A reply that fails gets one repair request listing the problems. After that it's held with its reasons.
"""
import json
import re

from engine import lexicon, values

LABELS = ("conflict", "variation", "duplicate", "superseded", "consistent", "unrelated")
ROLE_IDS = set(values.ROLES.values())
STATES = {"TX", "OK", "KS", "CO"}
LINES = {"consumer", "small_business", "commercial"}
UNITS = {"days", "business_days", "months", "years"}
MODALS = {"must", "may", "must_not"}


TYPOGRAPHY = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
                            "\u00a0": " "})


def norm(text):
    """Lowercase with whitespace collapsed and typographic quotes and dashes made plain, so a quote copied with a curly
    apostrophe still matches its clause."""
    return " ".join(str(text).translate(TYPOGRAPHY).lower().split())


def quoted(quote, text):
    return bool(quote) and norm(quote) in norm(text)


def parse_json(reply):
    """The JSON object in a reply, allowing a code fence around it."""
    text = reply.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("the reply holds no JSON object")
    return json.loads(m.group(0))


def value_problems(value, attr_type):
    if not isinstance(value, dict) or value.get("type") != attr_type:
        return [f"the value must be a {attr_type} value"]
    t = value["type"]
    if t == "money" and not isinstance(value.get("dollars"), int):
        return ["money needs whole dollars"]
    if t == "time" and not (isinstance(value.get("minutes"), int) and 0 <= value["minutes"] < 1440):
        return ["a time needs minutes after midnight"]
    if t == "duration" and not (isinstance(value.get("n"), int) and value.get("unit") in UNITS):
        return ["a duration needs n and a unit of days, business_days, months or years"]
    if t == "count" and not isinstance(value.get("n"), int):
        return ["a count needs n"]
    if t == "percent" and not isinstance(value.get("bp"), int):
        return ["a percentage needs basis points"]
    if t == "role" and not (value.get("role") in ROLE_IDS or (value.get("role") is None and value.get("generic"))):
        return ["a role must be on the role list, or null with the general words in generic"]
    if t == "modal" and value.get("modal") not in MODALS:
        return ["a modal must be must, may or must_not"]
    return []


FIELDS = {"money": ("dollars",), "time": ("minutes",), "duration": ("n", "unit"), "count": ("n",), "percent": ("bp",),
          "role": ("role",), "modal": ("modal",)}


def canonical(value):
    """A validated value with only its type's fields, so it compares equal to code's reading of the same value."""
    out = {"type": value["type"], **{k: value.get(k) for k in FIELDS[value["type"]]}}
    if out["type"] == "role" and out["role"] is None:
        out["generic"] = value.get("generic")
    return out


def quote_holds_value(quote, value):
    """Whether code, reading the quote on its own, finds the same value. Spoken forms code can't read pass when the
    quote is in the clause, and the page marks the value as read by the AI."""
    t = value["type"]
    if t in ("modal", "role"):
        return True
    found = values.find(t, quote) if t != "count" else values.row_value("count", quote) or values.find("count", quote)
    if not found:
        return True
    return any(v == {k: value[k] for k in v} for v, _ in found)


def check_atoms(clause_text, atoms):
    problems = []
    if not isinstance(atoms, list):
        return ["atoms must be a list"]
    for i, a in enumerate(atoms, 1):
        where = f"atom {i}"
        attr = a.get("attribute") if isinstance(a, dict) else None
        if attr not in lexicon.L:
            problems.append(f"{where}: {attr!r} isn't a tracked attribute")
            continue
        spec = lexicon.L[attr]
        problems += [f"{where}: {p}" for p in value_problems(a.get("value"), spec["type"])]
        if not quoted(a.get("quote"), clause_text):
            problems.append(f"{where}: the quote isn't in the clause")
        elif isinstance(a.get("value"), dict) and not quote_holds_value(a["quote"], a["value"]):
            problems.append(f"{where}: the quote doesn't hold the value")
        actor = a.get("actor")
        if actor is not None and actor not in ROLE_IDS:
            problems.append(f"{where}: the actor must be on the role list or null")
        for k in ("scope_quote", "condition"):
            if a.get(k) and not quoted(a[k], clause_text):
                problems.append(f"{where}: the {k} isn't in the clause")
    return problems


def check_extract(batch, reply):
    """(per-clause atoms, problems). Atoms are kept only for clauses whose atoms all pass."""
    try:
        data = parse_json(reply)
    except ValueError as e:
        return {}, [f"the reply isn't valid JSON: {e}"]
    results = data.get("results")
    if not isinstance(results, list):
        return {}, ["the reply needs a results list"]
    by_id = {r.get("clause"): r for r in results if isinstance(r, dict)}
    out, problems = {}, []
    for item in batch:
        r = by_id.get(item["clause"])
        if r is None:
            problems.append(f"{item['clause']}: no result")
            continue
        p = check_atoms(item["text"], r.get("atoms"))
        if p:
            problems += [f"{item['clause']}: {x}" for x in p]
        else:
            out[item["clause"]] = r.get("atoms") or []
    return out, problems


def numbers_in(text):
    return set(re.findall(r"\d+(?:[.,]\d+)*", str(text)))


WRITING = [(re.compile(r",\s+so\b", re.IGNORECASE), "a comma before so. End the sentence there and start the next one"),
           (re.compile(r";|(?<!\d):(?!\d)"), "a colon or semicolon"), (re.compile(r"\s[—–-]\s|—"), "a dash")]


def writing_problems(text):
    """Every writing rule a sentence breaks. The specialist's own sentences must pass all of them."""
    return [why for pat, why in WRITING if pat.search(text)]


def holding_problems(text):
    """The writing rules that hold an AI step's answer. A comma before so isn't one, since plain() fixes it."""
    return [why for pat, why in WRITING[1:] if pat.search(text)]


COMMA_SO = re.compile(r",\s+so\s+(\w)")


def plain(text):
    """Model prose as the page shows it: a comma before so becomes a full stop and a new sentence."""
    return COMMA_SO.sub(lambda m: ". So " + m.group(1), str(text))


def check_classify(batch, reply):
    """(per-pair labels, problems)."""
    try:
        data = parse_json(reply)
    except ValueError as e:
        return {}, [f"the reply isn't valid JSON: {e}"]
    results = data.get("results")
    if not isinstance(results, list):
        return {}, ["the reply needs a results list"]
    by_id = {r.get("pair"): r for r in results if isinstance(r, dict)}
    out, problems = {}, []
    for item in batch:
        r = by_id.get(item["pair"])
        if r is None:
            problems.append(f"{item['pair']}: no result")
            continue
        p = []
        if r.get("label") not in LABELS:
            p.append(f"the label must be one of {', '.join(LABELS)}")
        if not quoted(r.get("quote_a"), item["a"]["text"]):
            p.append("quote_a isn't in clause a")
        if not quoted(r.get("quote_b"), item["b"]["text"]):
            p.append("quote_b isn't in clause b")
        why = str(r.get("rationale") or "")
        if not why or len(why) > 500:
            p.append("the rationale must be one or two sentences")
        given = set().union(*(numbers_in(item[s]["text"]) | numbers_in(json.dumps(item[s].get("document") or {}))
                               for s in ("a", "b")))
        extra = numbers_in(why) - given
        if extra:
            p.append(f"the rationale uses numbers that aren't in either clause or its document: {', '.join(sorted(extra))}")
        p += [f"the rationale has {w}" for w in holding_problems(why)]
        if p:
            problems += [f"{item['pair']}: {x}" for x in p]
        else:
            out[item["pair"]] = {k: r[k] for k in ("label", "quote_a", "quote_b", "rationale")}
    return out, problems
