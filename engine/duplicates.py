"""Find steps copied from one document into another.

Clauses are compared by their word sets within a topic, and a duplicate is a run of at least three consecutive
clauses that match, in order, in two different documents. One or two shared sentences aren't a duplicate, since
standard lines like "Document the request in the account notes" belong in many procedures. Two versions of the same document
are left to the superseded check.
"""
import re

MIN_SIM = 0.72
MIN_RUN = 3


def words(text):
    return frozenset(re.findall(r"[a-z0-9$,.']+", text.lower().replace(",", "")))


def similarity(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def topic_of(doc):
    parts = doc["id"].split("-")
    return parts[1] if len(parts) > 2 else parts[0]


def find(docs):
    newest = {}
    for d in docs:
        newest[d["id"]] = max(newest.get(d["id"], 0), d["version"])
    sections = {}
    for d in docs:
        if d["version"] != newest[d["id"]]:
            continue
        for s in d["sections"]:
            if len(s["clauses"]) >= MIN_RUN:
                sections.setdefault(topic_of(d), []).append((d, s, [words(c["text"]) for c in s["clauses"]]))
    out = []
    for topic in sorted(sections):
        group = sections[topic]
        for i, (da, sa, wa) in enumerate(group):
            for db, sb, wb in group[i + 1:]:
                if da["id"] == db["id"]:
                    continue
                for run in runs(wa, wb):
                    (a0, b0, n) = run
                    ca = [c["id"] for c in sa["clauses"][a0:a0 + n]]
                    cb = [c["id"] for c in sb["clauses"][b0:b0 + n]]
                    exact = all(sa["clauses"][a0 + k]["text"] == sb["clauses"][b0 + k]["text"] for k in range(n))
                    out.append({"type": "duplicate", "clauses": ca + cb, "first": ca, "second": cb,
                                "docs": [da["key"], db["key"]], "exact": exact, "decided_by": "code",
                                "rule": f"{n} consecutive clauses match in two documents"})
    return out


def runs(wa, wb):
    """Maximal runs of consecutive matching clauses: (start in a, start in b, length) with length >= MIN_RUN."""
    match = [[similarity(x, y) >= MIN_SIM for y in wb] for x in wa]
    out = []
    used = set()
    for i in range(len(wa)):
        for j in range(len(wb)):
            if (i, j) in used or not match[i][j]:
                continue
            n = 0
            while i + n < len(wa) and j + n < len(wb) and match[i + n][j + n]:
                used.add((i + n, j + n))
                n += 1
            if n >= MIN_RUN:
                out.append((i, j, n))
    return out
