"""Read back what the AI steps recorded, and check every reply again before anything uses it.

Recordings live in data/ai_runs/<step>/<tag>/, one file per batch, where the tag is a seed or an evaluation set.
Only recordings made with the current prompt count, and only from the models asked for. Each reply is validated
again against the exact input the model saw. When the caller passes today's items, a recorded answer is used only
if the model saw exactly what code would send today, so a regenerated library never reuses an old answer. Every
call also has a line in data/ai_runs/audit.jsonl, and audit_problems() checks that the two agree.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from agents import mask, prompts, steps

HERE = Path(__file__).resolve().parent.parent
RUNS = HERE.joinpath("data", "ai_runs")


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def recordings(step, tag, root=None, models=None, prompt_hash=None):
    """The recordings for one step and tag, oldest first, made with today's prompt by the models asked for."""
    folder = Path(root or RUNS).joinpath(step, str(tag))
    want = prompt_hash or prompts.prompt_hash(step)
    out = []
    for p in sorted(folder.glob("*.json")) if folder.exists() else []:
        rec = json.loads(p.read_text())
        if rec.get("prompt_hash") == want and (not models or rec.get("model") in models):
            out.append(rec)
    return sorted(out, key=lambda r: r.get("recorded_at", ""))


def reasons(problems, ids):
    """Each item's reasons from one reply's problems. A problem with the whole reply counts for every item."""
    general = [p for p in problems if not any(p.startswith(i + ": ") for i in ids)]
    return {i: [p[len(i) + 2:] for p in problems if p.startswith(i + ": ")] or general or ["no reply passed"]
            for i in ids}


def accepted(rec):
    """({item: output}, {item: reasons}) for one recording, validated again. Each item comes from the first reply
    when it passes there, or else from the repair."""
    key, check = steps.key(rec["step"]), steps.check(rec["step"])
    batch = rec["input"]
    ok, last = check(batch, rec["attempts"][0]["reply"])
    if len(rec["attempts"]) > 1:
        retry_ids = set(rec["attempts"][1].get("items") or [])
        ok2, last = check([i for i in batch if i[key] in retry_ids], rec["attempts"][1]["reply"])
        ok.update(ok2)
    held_ids = [i[key] for i in batch if i[key] not in ok]
    return ok, reasons(last, held_ids)


def load(step, tag, root=None, models=None, items=None):
    """What one step recorded for one tag, validated again, with the newest recording of an item winning.

    Returns accepted {item: output}, held {item: reasons}, stale (items whose recorded input differs from today's),
    missing (today's items with no recording) and used (the recordings that supplied an answer)."""
    key = steps.key(step)
    want = None if items is None else {i[key]: mask.mask_payload(i)[0] for i in items}
    final, stale = {}, set()
    recs = recordings(step, tag, root, models)
    for n, rec in enumerate(recs):
        ok, held = accepted(rec)
        for i in rec["input"]:
            iid = i[key]
            if want is not None and iid not in want:
                continue
            if want is not None and want[iid] != i:
                stale.add(iid)
                continue
            final[iid] = (n, "ok", ok[iid]) if iid in ok else (n, "held", held[iid])
    out = {"accepted": {i: v for i, (_, s, v) in final.items() if s == "ok"},
           "held": {i: v for i, (_, s, v) in final.items() if s == "held"},
           "stale": sorted(stale - set(final)),
           "missing": [] if want is None else [i for i in want if i not in final and i not in stale],
           "used": [recs[n] for n in sorted({n for n, _, _ in final.values()})]}
    return out


def client_context():
    """The client context each recorded Claude call carries beyond the prompt and items (config/models.json)."""
    return json.loads(HERE.joinpath("config", "models.json").read_text()).get("client_context_tokens", 0)


def totals(used, context=None):
    """Calls, tokens, dollars and seconds across a list of recordings. dollars is what each backend reported, and
    api_input_tokens leaves out the client context on every recorded Claude call, as the API would bill a client."""
    context = client_context() if context is None else context
    calls = tokens_in = tokens_out = api_in = 0
    dollars = seconds = 0.0
    for rec in used:
        carries = bool((rec.get("backend") or {}).get("client_context"))
        for a in rec["attempts"]:
            m = a.get("meta") or {}
            calls += 1
            tokens_in += m.get("input_tokens") or 0
            api_in += max(0, (m.get("input_tokens") or 0) - (context if carries else 0))
            tokens_out += m.get("output_tokens") or 0
            dollars += m.get("cost_usd") or 0.0
            seconds += (m.get("ms") or 0) / 1000
    return {"calls": calls, "input_tokens": tokens_in, "api_input_tokens": api_in, "output_tokens": tokens_out,
            "dollars": round(dollars, 4), "seconds": round(seconds, 1)}


def audit_problems(root=None):
    """Every recorded reply has its audit line and every audit line has its reply, replaced recordings included."""
    root = Path(root or RUNS)
    path = root.joinpath("audit.jsonl")
    lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
    logged = Counter((x["step"], x["tag"], x["input_hash"], x["output_hash"]) for x in lines)
    recorded = Counter()
    for p in sorted(root.rglob("*.json")):
        rec = json.loads(p.read_text())
        for a in rec["attempts"]:
            recorded[(rec["step"], rec["tag"], rec["input_hash"][:16], sha(a["reply"])[:16])] += 1
    return ([f"no audit line for {' '.join(k)}" for k in recorded - logged]
            + [f"an audit line with no recording: {' '.join(k)}" for k in logged - recorded])
