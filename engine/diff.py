"""The difference between the clauses a draft replaces and the draft itself, computed by code and never by the AI.

It compares word by word with the standard library's sequence matcher, so the page can show what each clause loses
and what the consolidated section adds.
"""
import difflib


def diff(old, new):
    """[(op, text)] with op "same", "del" or "add"."""
    a, b = old.split(), new.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(("same", " ".join(a[i1:i2])))
            continue
        if i2 > i1:
            out.append(("del", " ".join(a[i1:i2])))
        if j2 > j1:
            out.append(("add", " ".join(b[j1:j2])))
    return out
