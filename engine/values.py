"""Find values in policy text: dollar amounts, clock times, durations, counts, percentages, roles and modals.

Each finder returns every match with its span, so an atom can always point at the exact words it came from. Number
words ("fifty dollars," "two business days") are read the same as digits.
"""
import re

UNITS = {"business day": "business_days", "business days": "business_days", "calendar day": "days",
         "calendar days": "days", "day": "days", "days": "days", "month": "months", "months": "months",
         "year": "years", "years": "years"}
SMALL = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
NUMBER_WORD = r"(?:(?:" + "|".join(sorted(list(SMALL) + list(TENS) + ["hundred", "thousand"], key=len, reverse=True)) \
              + r")(?:[\s-](?:" + "|".join(sorted(list(SMALL) + list(TENS) + ["hundred", "thousand", "and"],
                                                    key=len, reverse=True)) + r"))*)"
NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+|" + NUMBER_WORD + r")"

ROLES = {
    "card services specialist": "card_services_specialist", "customer care representative": "customer_care_representative",
    "operations specialist": "operations_specialist", "operations manager": "operations_manager",
    "compliance officer": "compliance_officer", "records custodian": "records_custodian",
    "regional manager": "regional_manager", "branch manager": "branch_manager", "personal banker": "personal_banker",
    "wire specialist": "wire_specialist", "lending officer": "lending_officer", "head teller": "head_teller",
    "teller": "teller",
}
ROLES_BY_ID = {rid: name for name, rid in ROLES.items()}
ROLE_RE = re.compile(r"\b(" + "|".join(sorted(ROLES, key=len, reverse=True)) + r")s?\b", re.IGNORECASE)
GENERIC_ROLE_RE = re.compile(r"\b(a manager|management|an operations employee|a supervisor)\b", re.IGNORECASE)


def number(text):
    """An integer from digits or number words."""
    t = text.lower().replace(",", "").strip()
    if t.isdigit():
        return int(t)
    total, current = 0, 0
    for w in re.split(r"[\s-]+", t):
        if w in SMALL:
            current += SMALL[w]
        elif w in TENS:
            current += TENS[w]
        elif w == "hundred":
            current = (current or 1) * 100
        elif w == "thousand":
            total += (current or 1) * 1000
            current = 0
        elif w == "and":
            continue
        else:
            return None
    return total + current


MONEY_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{2}))?|\b(" + NUMBER_WORD + r")\s+dollars?\b", re.IGNORECASE)
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.m\.|p\.m\.|am|pm)(?![a-z])", re.IGNORECASE)
DUR_RE = re.compile(r"\b(" + NUM + r")\s+(business days?|calendar days?|days?|months?|years?)\b", re.IGNORECASE)
PCT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?%|\b(\d+)\s+basis points\b", re.IGNORECASE)
COUNT_RE = re.compile(r"\b(" + NUM + r")\b(?!\s*(?:business|calendar|days?|months?|years?|dollars?|%|percent|basis|"
                      r"a\.m\.|p\.m\.|am\b|pm\b|:\d))", re.IGNORECASE)


def money(text):
    out = []
    for m in MONEY_RE.finditer(text):
        if m.group(1):
            n = int(m.group(1).replace(",", ""))
        else:
            n = number(m.group(3))
        if n is not None:
            out.append(({"type": "money", "dollars": n}, m.span()))
    return out


def times(text):
    out = []
    for m in TIME_RE.finditer(text):
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        pm = m.group(3).lower().startswith("p")
        if pm and h != 12:
            h += 12
        if not pm and h == 12:
            h = 0
        out.append(({"type": "time", "minutes": h * 60 + mi}, m.span()))
    return out


def durations(text):
    out = []
    for m in DUR_RE.finditer(text):
        n = number(m.group(1))
        unit = UNITS.get(m.group(2).lower())
        if n is not None and unit:
            out.append(({"type": "duration", "n": n, "unit": unit}, m.span()))
    return out


def percents(text):
    out = []
    for m in PCT_RE.finditer(text):
        if m.group(1):
            bp = round(float(m.group(1)) * 100)
        else:
            bp = int(m.group(2))
        out.append(({"type": "percent", "bp": bp}, m.span()))
    return out


COUNTED = re.compile(r"^\s+(?:[a-z-]+\s+){0,2}?(?:[a-z-]+s|per)\b", re.IGNORECASE)


def counts(text):
    """Numbers that count something: followed within a few words by a plural noun or "per," and not part of money,
    a time, a duration or a percentage. "two forms of identification" counts, and "for one account" doesn't."""
    taken = [span for _, span in money(text) + times(text) + durations(text) + percents(text)]
    out = []
    for m in COUNT_RE.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        if not COUNTED.match(text[m.end():]):
            continue
        n = number(m.group(1))
        if n is not None and n < 1000:
            out.append(({"type": "count", "n": n}, m.span()))
    return out


def roles(text):
    return [({"type": "role", "role": ROLES[m.group(1).lower()]}, m.span()) for m in ROLE_RE.finditer(text)]


def generic_roles(text):
    return [m.group(1).lower() for m in GENERIC_ROLE_RE.finditer(text)]


RELAXED = ("single employee may", "one employee may", "single opener may", "when time allows", "if time is short",
           "may be documented", "may open", "may unlock")
FORBIDDEN = ("must not", "may not", "never destroy", "not be destroyed")


REQUIRED = ("must", "required", "never", "together", "every pricing exception", "record the reason")
MODAL_ROWS = {"required": "must", "optional": "may", "not allowed": "must_not"}


def modal(text):
    """must, may or must_not, as the clause sets it, or None when the clause has no modal language at all."""
    t = text.lower()
    if t.strip() in MODAL_ROWS:
        return {"type": "modal", "modal": MODAL_ROWS[t.strip()]}
    if "|" in t:
        cell = t.split("|")[-1].strip()
        if cell in MODAL_ROWS:
            return {"type": "modal", "modal": MODAL_ROWS[cell]}
    if any(p in t for p in FORBIDDEN):
        return {"type": "modal", "modal": "must_not"}
    if any(p in t for p in RELAXED):
        return {"type": "modal", "modal": "may"}
    if any(p in t for p in REQUIRED):
        return {"type": "modal", "modal": "must"}
    return None


FINDERS = {"money": money, "time": times, "duration": durations, "percent": percents, "count": counts, "role": roles}


def find(vtype, text):
    """Every value of one type in the text, deduplicated by value, each with its first span."""
    if vtype == "modal":
        m = modal(text)
        return [(m, (0, len(text)))] if m else []
    seen, out = set(), []
    for v, span in FINDERS[vtype](text):
        k = tuple(sorted(v.items()))
        if k not in seen:
            seen.add(k)
            out.append((v, span))
    return out


def same(a, b):
    return a is not None and b is not None and a == b


def rule_like(text):
    """Whether a clause reads like a rule at all: it holds a value, names a role, or uses modal language."""
    if any(FINDERS[t](text) for t in ("money", "time", "duration", "percent", "count", "role")):
        return True
    return modal(text) is not None or bool(generic_roles(text))


ROW_COUNT = re.compile(r"^\s*(" + NUM + r")\s*$", re.IGNORECASE)


def row_value(vtype, cell):
    """The value in a quick-reference table's value cell, where a count can stand alone ("two")."""
    if vtype == "count":
        m = ROW_COUNT.match(cell)
        n = number(m.group(1)) if m else None
        return [({"type": "count", "n": n}, (0, len(cell)))] if n is not None else []
    return find(vtype, cell)
