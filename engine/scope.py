"""Who a rule applies to: which states and which business lines, and whether a clause narrows its document on purpose.

A document's scope comes from its "Applies to" line. A clause can narrow it ("In Colorado branches," or "For
commercial accounts,"), and a rule that differs only inside a narrower scope it states is a deliberate variation,
never a conflict.
"""
import re

STATES = {"texas": "TX", "oklahoma": "OK", "kansas": "KS", "colorado": "CO"}
ALL_STATES = ("CO", "KS", "OK", "TX")
LINES = {"consumer": "consumer", "small business": "small_business", "commercial": "commercial"}
ALL_LINES = ("commercial", "consumer", "small_business")
TYPES = {"POL": "policy", "PRO": "procedure", "JA": "job_aid", "FAQ": "faq", "BUL": "bulletin", "ADD": "addendum"}

STATE_WORDS = "|".join(w.capitalize() for w in STATES)
LINE_WORDS = "consumer|small business|commercial"
STATE_PREFIX = re.compile(rf"\bIn ((?:{STATE_WORDS})(?:(?:,| and)\s+(?:{STATE_WORDS}))*) branches\b")
LINE_PREFIX = re.compile(rf"\bFor ((?:{LINE_WORDS})(?:(?:,| and)\s+(?:{LINE_WORDS}))*) accounts\b", re.IGNORECASE)
LINE_ANY = re.compile(rf"\b({LINE_WORDS})\b", re.IGNORECASE)


def doc_type(doc):
    return TYPES.get(doc["id"].split("-")[0], "other")


def lines_in(text):
    return sorted({LINES[m.group(1).lower()] for m in LINE_ANY.finditer(text)})


def doc_scope(applies_to):
    """(states, lines) from an "Applies to" line like "All branches. Consumer and small business accounts.\""""
    text = applies_to.lower()
    states = sorted({code for name, code in STATES.items() if name in text}) or list(ALL_STATES)
    if "all business lines" in text or not lines_in(applies_to):
        lines = list(ALL_LINES)
    else:
        lines = lines_in(applies_to)
    return states, lines


def clause_scope(text, doc_states, doc_lines, scoped=False):
    """The clause's own scope: the document's, unless the clause states a narrower one."""
    states, lines, explicit, phrase = list(doc_states), list(doc_lines), False, None
    m = STATE_PREFIX.search(text)
    if m:
        states = sorted(STATES[w.lower()] for w in re.split(r",\s*|\s+and\s+", m.group(1)))
        explicit, phrase = True, m.group(0)
    m = LINE_PREFIX.search(text)
    if m:
        lines = lines_in(m.group(1))
        explicit, phrase = True, m.group(0)
    elif scoped:
        found = lines_in(text)
        if found:
            lines = found
    return {"states": states, "lines": lines, "explicit": explicit, "phrase": phrase}


def overlaps(a, b):
    return bool(set(a["states"]) & set(b["states"])) and bool(set(a["lines"]) & set(b["lines"]))


def narrower(a, b):
    """True when a's scope sits strictly inside b's on states or lines."""
    sa, sb, la, lb = set(a["states"]), set(b["states"]), set(a["lines"]), set(b["lines"])
    return (sa <= sb and la <= lb) and (sa < sb or la < lb)


def narrower_somewhere(a, b):
    """True when a's states or a's lines sit strictly inside b's."""
    return set(a["states"]) < set(b["states"]) or set(a["lines"]) < set(b["lines"])


def deliberate(a, b):
    """A difference between a and b is a deliberate variation when their scopes don't overlap, or when one states a
    narrower scope on purpose, in its own words or as a state addendum. An addendum usually applies to every business
    line, so narrowing on either states or lines is enough."""
    if not overlaps(a, b):
        return True
    for x, y in ((a, b), (b, a)):
        if (x["explicit"] or x["doc_type"] == "addendum") and narrower_somewhere(x, y):
            return True
    return False
