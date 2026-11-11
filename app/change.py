"""The "Change a rule" scenario on the Library tab, precomputed by the build.

It lowers one dollar limit in the policy that states it, reruns only what that touches through engine/incremental.py,
and records what reran, what was reused, how long it took against a full run, and the contradictions the change
created, since every other document still states the old limit.
"""
from engine import incremental, lexicon

PREFERRED = "fee_waiver_bm"


def pick(result):
    """The policy clause whose dollar limit the scenario lowers."""
    money = [a for a in result["atoms"] if a["doc_type"] == "policy" and a["value"]["type"] == "money"]
    return next((a for a in money if a["attribute"] == PREFERRED), money[0] if money else None)


def scenario(result):
    a = pick(result)
    if a is None:
        return None
    dollars = a["value"]["dollars"]
    new_words = f"${max(1, dollars - 10):,}"
    docs = incremental.change_clause(result["documents"], a["clause"], a["value_text"], new_words)
    r = incremental.rerun(result, docs)
    titles = {d["key"]: d["title"] for d in result["documents"]}
    r.update({"clause": a["clause"], "rule": lexicon.LABELS[a["attribute"]], "title": titles[a["doc"]],
              "old": a["value_text"], "new": new_words, "full_seconds": round(sum(result["timings"].values()), 3),
              "created_titles": sorted({titles[c.rsplit("/", 2)[0]] for pair in r["created"] for c in pair
                                        if not c.startswith(a["doc"])})})
    return r
