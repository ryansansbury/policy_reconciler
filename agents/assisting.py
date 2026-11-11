"""The assistant's items and the code that checks its answers.

An employee's question retrieves the five best clauses from the published index by keyword search. The assistant
answers from those clauses only and cites the ones it used. Code then checks every value in the answer against the
cited clauses, and when the cited clauses state different values the answer must say the sources disagree. The same
questions run before reconciliation, against the library as it is, and after, against the index with the approved
drafts in place.
"""
from agents import validate
from engine import lexicon, search, values

K = 5


def question_id(q):
    return f"q-{q['item']}"


def items(index, questions, k=K):
    ix = search.Index(index)
    out = []
    for q in questions:
        hits = ix.search(q["question"], k)
        out.append({"question": question_id(q), "text": q["question"], "type": lexicon.L[q["attribute"]]["type"],
                    "clauses": [{f: h.get(f) for f in ("id", "text", "title", "type", "version", "effective")}
                                for h in hits]})
    return out


def found(vtype, text):
    return {tuple(sorted(v.items())) for v, _ in values.find(vtype, text)} if vtype != "modal" else set()


def check(batch, reply):
    """(per-question answers, problems)."""
    try:
        data = validate.parse_json(reply)
    except ValueError as e:
        return {}, [f"the reply isn't valid JSON: {e}"]
    results = data.get("results")
    if not isinstance(results, list):
        return {}, ["the reply needs a results list"]
    by_id = {r.get("question"): r for r in results if isinstance(r, dict)}
    out, problems = {}, []
    for item in batch:
        r = by_id.get(item["question"])
        if r is None:
            problems.append(f"{item['question']}: no result")
            continue
        texts = {c["id"]: c["text"] for c in item["clauses"]}
        cited = r.get("citations") if isinstance(r.get("citations"), list) else []
        answer = str(r.get("answer") or "").strip()
        p = []
        if not answer or not cited:
            p.append("an answer needs its text and at least one citation")
        p += [f"{c} wasn't retrieved for this question" for c in cited if c not in texts]
        stated = [found(item["type"], texts[c]) for c in cited if c in texts]
        allowed = set().union(*stated) if stated else set()
        extra = found(item["type"], answer) - allowed
        if extra:
            p.append("the answer states a value no cited clause holds")
        disagree = len({frozenset(s) for s in stated if s}) > 1
        if disagree and r.get("sources_disagree") is not True:
            p.append("the cited clauses state different values, so the answer must say the sources disagree")
        p += [f"the answer has {w}" for w in validate.holding_problems(answer)]
        if p:
            problems += [f"{item['question']}: {x}" for x in p]
        else:
            out[item["question"]] = {"answer": answer, "citations": cited, "sources_disagree": bool(r.get("sources_disagree"))}
    return out, problems


def score(questions, answers, after=False, items_by_q=None):
    """Per question: whether search retrieved the gold clause, and whether the answer states the gold value, cites the
    gold clause or the draft that replaced it, and flags the disagreement before reconciliation when search retrieved
    the conflicting clause too. A question search couldn't answer counts against search and never against the model."""
    out = []
    for q in questions:
        qid = question_id(q)
        ids = {c["id"] for c in (items_by_q or {}).get(qid, {}).get("clauses", [])}
        found_gold = q["gold_citation"] in ids or any(i.startswith("draft:") for i in ids) if items_by_q else True
        must_flag = not after and (q["conflicting"] in ids if items_by_q else True)
        a = answers.get(qid)
        if a is None:
            out.append({"question": qid, "answered": False, "retrieved": found_gold})
            continue
        gold = tuple(sorted(q["gold_value"].items()))
        right = gold in found(lexicon.L[q["attribute"]]["type"], a["answer"]) or q["gold_text"] in a["answer"]
        cited = q["gold_citation"] in a["citations"] or any(c.startswith("draft:") for c in a["citations"])
        out.append({"question": qid, "answered": True, "retrieved": found_gold, "value_right": right, "cited": cited,
                    "flagged": a["sources_disagree"],
                    "ok": right and cited and (not must_flag or a["sources_disagree"])})
    return out
