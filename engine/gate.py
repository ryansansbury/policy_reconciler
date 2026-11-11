"""The gate: a draft may state a value only through a citation, so every value in it traces to a clause.

The drafter writes each value as a placeholder like {clause:POL-FEE-01@v2/s3/c2#value}, where the part after # names
which of the clause's values it means: "value" is the rule's own, and v2, v3 and so on are any other values the
kept clause states, like an exception's deadline. The draft's input lists every placeholder it may use with the words
code fills in. The gate fails a draft that uses any other placeholder, that cites no clause at all, or that shows any
value code can find outside a placeholder. A draft that passes is rendered by filling each placeholder with its words.
"""
import re

from engine import values

PLACEHOLDER = re.compile(r"\{clause:([^#{}]+#[a-z0-9]+)\}")
KINDS = ("money", "time", "duration", "percent", "count")
MODAL_WORDS = re.compile(r"\b(?:must not|must|may not|may|shall|should|required|optional|never|cannot)\b", re.IGNORECASE)


def placeholders(text):
    return PLACEHOLDER.findall(text)


def bare(text):
    """The text with each placeholder blanked to spaces, so every other span keeps its offsets."""
    return PLACEHOLDER.sub(lambda m: " " * len(m.group(0)), text)


def spans(text, rule_type=None):
    """Every value code finds in a text, as {kind, text, span}, in reading order. A rule whose value is a role or a
    modal word also counts every role or every modal word, since those are its values."""
    kinds = KINDS + (("role",) if rule_type == "role" else ())
    out = [{"kind": k, "text": text[b:e], "span": [b, e]} for k in kinds for _, (b, e) in values.find(k, text)]
    if rule_type == "modal":
        out += [{"kind": "modal", "text": m.group(0), "span": list(m.span())} for m in MODAL_WORDS.finditer(text)]
    return sorted(out, key=lambda u: u["span"])


def untraced(text, rule_type=None):
    """Every value code finds outside the placeholders."""
    return spans(bare(text), rule_type)


def check(text, allowed, rule_type=None):
    """(problems, rendered text or None). allowed maps each placeholder the draft may use, like "<clause>#value", to
    the words code fills in. The drafter's input carries the same map, so a recorded draft can be checked again on
    its own."""
    problems = []
    used = placeholders(text)
    if not used:
        problems.append("the draft cites no clause for its value")
    problems += [f"{{clause:{p}}} isn't a placeholder this draft may use" for p in used if p not in allowed]
    problems += [f"the value \"{u['text']}\" isn't traced to a clause" for u in untraced(text, rule_type)]
    return problems, (None if problems else render(text, allowed))


def render(text, allowed):
    return PLACEHOLDER.sub(lambda m: allowed[m.group(1)], text)
