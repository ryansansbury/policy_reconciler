"""Do embeddings earn their place?

Pairing puts two statements of one rule in front of the comparison. Code pairs the clauses whose rule its cue words
read, and every other clause waits in the AI queue. The question is whether embeddings could pair a queued clause by
giving it the rule of its most similar clause among those code read. Four arms run on the held-out libraries:

    code alone              the cue words only
    code and embeddings     a queued clause takes its nearest read neighbor's rule above a similarity threshold
    code and the extractor  the rule extractor reads the queue, as the pipeline ships
    all three               embeddings fill in only what the extractor left unread

Each arm reports the paraphrase contradictions it pairs (the planted P items), the rules it gives queued clauses
that the generator's own record says they don't state, and what it adds in cost and time per library. The threshold
is tuned on the development libraries only.

Search is the second question. The assistant ranks clauses by BM25, and the hybrid here also ranks by embedding
similarity and fuses the two by reciprocal rank. Each preset question counts when its own clause and the clause that
contradicts it both reach the assistant's top five, before reconciliation. BM25's top ten is the third arm, since a
longer list might find as much without embeddings, at the cost of more for the assistant to read. The hybrid is kept
only if it beats both and loses no question BM25 answered. That rule was set before any result. The hybrid's top ten
was added after the results were seen, so it's reported as exploratory and decides nothing.

The vectors were recorded once and aren't part of this repo. This module wrote evals/embeddings.json with the
numbers and the choice they lead to, and the page reads that file.
"""
import json
import math
from pathlib import Path

from agents import assisting, inputs, items, replay
from engine import publish, search
from generate import world

HERE = Path(__file__).resolve().parent.parent
VECTORS = HERE.joinpath("data", "embeddings")
OUT = HERE.joinpath("evals", "embeddings.json")
DEV = [str(s) for s in world.SEEDS["dev"]]
HELD = [str(s) for g in ("heldout_b", "heldout_c") for s in world.SEEDS[g]]
ARMS = ("code", "embeddings", "extractor", "all")
FUSE = 60


def unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def truth(seed):
    """{clause: the rules the generator wrote into it}."""
    plan = json.loads(HERE.joinpath("data", "key", seed, "plan.json").read_text())
    return {c["id"]: {a["attribute"] for a in c["atoms"]} for d in plan["documents"] for s in d["sections"]
            for c in s["clauses"]}


def paraphrases(seed):
    key = json.loads(HERE.joinpath("data", "key", seed, "key.json").read_text())
    return [(i["target"], i["attribute"], i["conflicts_with"]) for i in key["items"] if i["category"] == "P"]


def nearest(vectors, queue, read):
    """{queued clause: (similarity, its most similar read clause)}."""
    pool = [(c, unit(vectors[c])) for c in read if c in vectors]
    out = {}
    for q in queue:
        if q in vectors and pool:
            v = unit(vectors[q])
            out[q] = max(((sum(a * b for a, b in zip(v, u)), c) for c, u in pool if c != q), default=(0.0, None))
    return out


def arms(code, extracted, near, tau):
    """{arm: {clause: rules}} with the arm's additions on top of code's own readings."""
    def lend(base, only=None):
        out = {c: set(s) for c, s in base.items()}
        for q, (sim, c) in near.items():
            if c and sim >= tau and (only is None or q in only) and code.get(c):
                out.setdefault(q, set()).update(code[c])
        return out
    with_ext = {c: set(s) for c, s in code.items()}
    for c, s in extracted.items():
        with_ext.setdefault(c, set()).update(s)
    unread = {q for q in near if not extracted.get(q)}
    return {"code": code, "embeddings": lend(code), "extractor": with_ext, "all": lend(with_ext, unread)}


def measure(rules, code, truth_rules, items_p):
    added = [(c, a) for c, s in rules.items() for a in s if a not in code.get(c, set())]
    wrong = sum(1 for c, a in added if a not in truth_rules.get(c, set()))
    paired = sum(1 for t, a, others in items_p
                 if a in rules.get(t, ()) and any(a in rules.get(o, ()) for o in others if o != t))
    return {"paired": paired, "of": len(items_p), "added": len(added), "wrong": wrong}


def library(seed, vectors_dir=None):
    """Everything one library's arms need, or None when its vectors aren't recorded."""
    path = Path(vectors_dir or VECTORS).joinpath(f"{seed}.json")
    if not path.exists():
        return None
    vectors = json.loads(path.read_text())["vectors"]
    result = items.library(seed)
    code = {}
    for a in result["atoms"]:
        code.setdefault(a["clause"], set()).add(a["attribute"])
    queue = [q["clause"] for q in result["queue"]]
    its = inputs.extract_items(result)
    model = json.loads(HERE.joinpath("config", "models.json").read_text())["steps"]["extract"]
    rec = replay.load("extract", seed, None, [model], items=its)
    extracted = {c: {a["attribute"] for a in atoms} for c, atoms in rec["accepted"].items()}
    t = replay.totals(rec["used"])
    return {"seed": seed, "vectors": vectors, "result": result, "code": code, "extracted": extracted,
            "near": nearest(vectors, queue, list(code)), "truth": truth(seed), "p": paraphrases(seed),
            "extractor_seconds": t["seconds"], "extractor_tokens": (t["api_input_tokens"], t["output_tokens"])}


def tune(libs, grid=None):
    """The threshold that does best on the development libraries, counting each right rule a queued clause gets once
    and each wrong one twice, since a wrong rule pairs statements that can turn into a false alarm."""
    best = None
    for tau in grid or [round(0.30 + 0.01 * i, 2) for i in range(66)]:
        score = 0
        for lib in libs:
            m = measure(arms(lib["code"], {}, lib["near"], tau)["embeddings"], lib["code"], lib["truth"], lib["p"])
            score += (m["added"] - m["wrong"]) - m["wrong"]
        if best is None or score > best[0]:
            best = (score, tau)
    return best[1]


def ranked(lib, question, qid, k):
    """{arm: top ids} for one question over the library's index before reconciliation: BM25's top k, BM25's top 2k
    (a longer list the assistant would have to read), and the hybrid's top k."""
    index = publish.before(lib["result"])
    bm25 = [h["id"] for h in search.Index(index).search(question, len(index))]
    qv = lib["vectors"].get("q:" + qid)
    if qv is None:
        return {"bm25": bm25[:k], "bm25_wide": bm25[:2 * k], "hybrid": bm25[:k], "hybrid_wide": bm25[:2 * k]}
    qv = unit(qv)
    by_sim = sorted((i["id"] for i in index if i["id"] in lib["vectors"]),
                    key=lambda c: -sum(a * b for a, b in zip(qv, unit(lib["vectors"][c]))))
    fused = {}
    for ranking in (bm25, by_sim):
        for r, c in enumerate(ranking):
            fused[c] = fused.get(c, 0) + 1 / (FUSE + r + 1)
    best = sorted(fused, key=lambda c: (-fused[c], c))
    return {"bm25": bm25[:k], "bm25_wide": bm25[:2 * k], "hybrid": best[:k], "hybrid_wide": best[:2 * k]}


SEARCH = ("bm25", "bm25_wide", "hybrid", "hybrid_wide")


def search_arm(lib, k=assisting.K):
    out = dict({a: {"gold": 0, "both": 0} for a in SEARCH}, questions=0, lost=0, lost_wide=0)
    questions = json.loads(HERE.joinpath("data", "key", lib["seed"], "evals.json").read_text())["assistant"]
    for q in questions:
        out["questions"] += 1
        tops = ranked(lib, q["question"], assisting.question_id(q), k)
        for name, top in tops.items():
            out[name]["gold"] += q["gold_citation"] in top
            out[name]["both"] += q["gold_citation"] in top and q["conflicting"] in top
        out["lost"] += q["gold_citation"] in tops["bm25"] and q["gold_citation"] not in tops["hybrid"]
        out["lost_wide"] += q["gold_citation"] in tops["bm25_wide"] and q["gold_citation"] not in tops["hybrid_wide"]
    return out


def run(vectors_dir=None, runs_path=None, out=OUT):
    dev = [x for x in (library(s, vectors_dir) for s in DEV) if x]
    held = [x for x in (library(s, vectors_dir) for s in HELD) if x]
    if not dev or not held:
        return None
    tau = tune(dev)
    pairing = {a: {"paired": 0, "of": 0, "added": 0, "wrong": 0} for a in ARMS}
    found = dict({a: {"gold": 0, "both": 0} for a in SEARCH}, questions=0, lost=0, lost_wide=0)
    for lib in held:
        for a, rules in arms(lib["code"], lib["extracted"], lib["near"], tau).items():
            for k, v in measure(rules, lib["code"], lib["truth"], lib["p"]).items():
                pairing[a][k] += v
        s = search_arm(lib)
        for name in SEARCH:
            for k in ("gold", "both"):
                found[name][k] += s[name][k]
        for k in ("questions", "lost", "lost_wide"):
            found[k] += s[k]
    runs = json.loads(Path(runs_path or HERE.joinpath("evals", "embeddings_runs.json")).read_text())
    cfg = json.loads(HERE.joinpath("config", "models.json").read_text())
    ext = next(m for m in cfg["models"] if m["id"] == cfg["steps"]["extract"])
    n = len(held)
    cost = {"embeddings": round(sum(runs["seeds"][x["seed"]]["dollars"] or 0 for x in held) / n, 4),
            "embeddings_seconds": round(sum(runs["seeds"][x["seed"]]["seconds"] for x in held) / n, 1),
            "extractor": round(sum(x["extractor_tokens"][0] * ext["price_in"] + x["extractor_tokens"][1] * ext["price_out"]
                                   for x in held) / 1e6 / n, 4),
            "extractor_seconds": round(sum(x["extractor_seconds"] for x in held) / n, 1)}
    p, ex = pairing["all"], pairing["extractor"]
    if p["paired"] > ex["paired"] and p["wrong"] <= ex["wrong"]:
        pair_choice = "adds"
    elif pairing["embeddings"]["paired"] >= ex["paired"] and pairing["embeddings"]["wrong"] <= ex["wrong"]:
        pair_choice = "replaces"
    else:
        pair_choice = "no_gain"
    better = (found["hybrid"]["both"] > max(found["bm25"]["both"], found["bm25_wide"]["both"])
              and not found["lost"])
    result = {"model": runs["model"], "threshold": tau, "dev": DEV, "held": [x["seed"] for x in held],
           "pairing": pairing, "search": found, "cost_per_library": cost,
           "choice": {"pairing": pair_choice, "search": "keep" if better else "no_gain"},
           "exploratory": ["hybrid_wide"]}
    Path(out).write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
