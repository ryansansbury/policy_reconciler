"""The How it works tab: the architecture, the AI map, what each AI step may and may not do, the results read from
the results files, the known limits, the self-serve split, how an engagement would start, and the code itself.

The AI map lives once in WORDS.md as aimap.rows, and the page and the README read the same rows, so the three
never drift. Every result here is read from a file the build or a scored run wrote, and nothing is typed in.
"""
import json
from pathlib import Path

from app import code_view, routing_view
from evals import score_ai
from app.page import esc, icon

HERE = Path(__file__).resolve().parent.parent
KIND_CLASS = {"Code": "k-code", "People": "k-people"}
STEP_KEY = {"extract": "a1", "classify": "a2", "draft": "a3", "judge": "a4", "assist": "a5"}
# The diagram: (box, row, column, kind). Each box opens its file in the code view below it.
BOXES = [("parse", 0, 0, "code"), ("extract", 0, 1, "code"), ("a1", 0, 2, "ai"), ("compare", 0, 3, "code"),
         ("a2", 0, 4, "ai"), ("decide", 0, 5, "people"), ("a3", 1, 0, "ai"), ("gate", 1, 1, "code"),
         ("a4", 1, 2, "ai"), ("approve", 1, 3, "people"), ("publish", 1, 4, "code"), ("a5", 1, 5, "ai")]


def ai_map(w):
    """The AI map's rows as [step, done by, type, how it's kept honest]."""
    return [label.split(" | ") for label in w.table("aimap.rows").values()]


def diagram(w):
    bw, bh, gx, gy, x0, y0 = 170, 64, 26, 70, 10, 34
    out = []
    for key, row, col, kind in BOXES:
        x, y = x0 + col * (bw + gx), y0 + row * (bh + gy)
        label = w[f"arch.{key}"]
        out.append(f"<a class=\"box b-{kind}\" href=\"{esc(code_view.blob(code_view.BOXES[key]))}\" target=\"_blank\" rel=\"noopener\" "
                   f"aria-label=\"{esc(label)}\"><rect x=\"{x}\" y=\"{y}\" width=\"{bw}\" height=\"{bh}\" rx=\"10\"/>"
                   f"<text x=\"{x + bw / 2}\" y=\"{y + 28}\">{esc(label)}</text><text class=\"sub\" x=\"{x + bw / 2}\" "
                   f"y=\"{y + 47}\">{esc(w['arch.kind.' + kind])}</text></a>")
        if col < 5:
            ax = x + bw
            out.append(f"<path class=\"arrow\" marker-end=\"url(#ah)\" d=\"M{ax + 3} {y + bh / 2}h{gx - 8}\"/>")
    turn_x = x0 + 5 * (bw + gx) + bw / 2
    out.append(f"<path class=\"arrow\" marker-end=\"url(#ah)\" d=\"M{turn_x} {y0 + bh + 4}v{gy - 30}H{x0 + bw / 2}v{18}\"/>")
    width, height = x0 * 2 + 6 * bw + 5 * gx, y0 + 2 * bh + gy + 14
    lanes = (f"<text class=\"lane\" x=\"{x0}\" y=\"20\">{esc(w['arch.lane.review'])}</text>"
             f"<text class=\"lane\" x=\"{x0}\" y=\"{y0 + bh + gy - 14}\">{esc(w['arch.lane.fix'])}</text>")
    return (f"<svg class=\"arch\" viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"{esc(w['arch.title'])}\">"
            f"<defs><marker id=\"ah\" viewBox=\"0 0 8 8\" refX=\"7\" refY=\"4\" markerWidth=\"7\" markerHeight=\"7\" "
            f"orient=\"auto-start-reverse\"><path d=\"M0 0L8 4L0 8z\"/></marker></defs>{lanes}{''.join(out)}</svg>")


def diagram_list(w):
    """The diagram as one list per lane for a phone, where the wide picture would shrink past reading. app.css shows
    the list or the picture and never both, and each step links the same file as its box."""
    lanes = []
    for row, lane in ((0, "review"), (1, "fix")):
        items = "".join(f"<li class=\"b-{kind}\"><a href=\"{esc(code_view.blob(code_view.BOXES[key]))}\" "
                        f"target=\"_blank\" rel=\"noopener\"><strong>{esc(w['arch.' + key])}</strong>"
                        f"<span>{esc(w['arch.kind.' + kind])}</span></a></li>"
                        for key, r, _, kind in BOXES if r == row)
        lanes.append(f"<div class=\"arch-lane\"><p class=\"kicker\">{esc(w['arch.lane.' + lane])}</p>"
                     f"<ol>{items}</ol></div>")
    return f"<div class=\"arch-list\">{''.join(lanes)}</div>"


def results_panel(w):
    code = json.loads(HERE.joinpath("evals", "code_only.json").read_text())["totals"]
    rows = [(w["how.res.code_only"], w.fill("how.res.caught", caught=code["caught"], planted=code["planted"]),
             w.fill("how.res.alarms", n=code["false_alarms"],
                    of=code["by_category"]["V_alarms"]["of"] + code["by_category"]["N_alarms"]["of"]))]
    scored = HERE.joinpath("evals", "ai_scored.json")
    run = score_ai.latest(json.loads(scored.read_text())["runs"]) if scored.exists() else None
    if run:
        code = [s["code_only"] for s in run["seeds"].values()]
        both = [s["combined"]["summary"] for s in run["seeds"].values()]
        for key, rs in (("how.res.code_only_new", code), ("how.res.combined", both)):
            rows.append((w[key], w.fill("how.res.caught", caught=sum(r["caught"] for r in rs),
                                        planted=sum(r["planted"] for r in rs)),
                         w.fill("how.res.alarms_only", n=sum(r["false_alarms"] for r in rs))))
    body = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in rows)
    pending = "" if run else f"<p class=\"muted\">{esc(w['how.res.pending'])}</p>"
    return (f"<section class=\"panel\" id=\"how-results\"><h3>{esc(w['how.res.title'])}</h3><p>{esc(w['how.res.text'])}</p>"
            f"<table class=\"results\"><thead><tr><th>{esc(w['how.res.col.what'])}</th><th>{esc(w['how.res.col.caught'])}"
            f"</th><th>{esc(w['how.res.col.alarms'])}</th></tr></thead><tbody>{body}</tbody></table>{pending}</section>")


def read(*parts):
    p = HERE.joinpath(*parts)
    return json.loads(p.read_text()) if p.exists() else None


def audit_lines():
    p = HERE.joinpath("data", "ai_runs", "audit.jsonl")
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def ran(w, record, ok_key="passed"):
    if not record:
        return w["kit.not_run"]
    status = record.get(ok_key, record.get("status") == "passed")
    return w.fill("kit.ran_ok" if status else "kit.ran_failed", date=record["ran_at"][:10])


def kit_panel(w):
    """The production kit: what's built, what ran and when, and the audit log with a filter by step."""
    lines = audit_lines()
    masked = {}
    for x in lines:
        for k, v in (x.get("masked") or {}).items():
            masked[k] = masked.get(k, 0) + v
    rows = [("gate", ran(w, read("data", "out", "ci_gate.json"))),
            ("audit", w.fill("kit.audit_n", n=len(lines))),
            ("masking", w.fill("kit.masked_n", n=sum(masked.values())) if lines else w["kit.masked_none"]),
            ("secrets", w["kit.secrets_state"]), ("roles", w["kit.roles_state"])]
    body = "".join(f"<tr><td><strong>{esc(w['kit.' + k])}</strong></td><td>{esc(w['kit.' + k + '.what'])}</td>"
                   f"<td>{esc(state)}</td></tr>" for k, state in rows)
    steps = sorted({x["step"] for x in lines})
    options = "".join(f"<option value=\"{esc(s)}\">{esc(s)}</option>" for s in steps)
    audit = "".join(f"<tr data-step=\"{esc(x['step'])}\"><td>{esc(x['time'][:16].replace('T', ' '))}</td><td>{esc(x['step'])}</td>"
                    f"<td>{esc(x['tag'])}</td><td>{esc(x['model'])}</td><td class=\"n\">{x.get('input_tokens') or 0:,}</td>"
                    f"<td class=\"n\">{x.get('output_tokens') or 0:,}</td><td class=\"n\">{x.get('problems', 0)}</td>"
                    f"<td>{esc(w['kit.repair'] if x.get('repair') else '')}</td></tr>" for x in lines[-300:])
    head = "".join(f"<th{' class=\"n\"' if k in ('tokens_in', 'tokens_out', 'problems') else ''}>{esc(h)}</th>"
                   for k, h in w.table("kit.audit.head").items())
    log = (f"<div class=\"controls\"><label>{esc(w['kit.audit.filter'])}<select id=\"audit-step\"><option value=\"\">"
           f"{esc(w['filter.all'])}</option>{options}</select></label></div><div class=\"list-wrap\"><table class=\"list\" "
           f"id=\"audit\"><thead><tr>{head}</tr></thead><tbody>{audit}</tbody></table></div>") if lines else (
           f"<p class=\"muted\">{esc(w['kit.audit_none'])}</p>")
    return (f"<section class=\"panel\" id=\"how-kit\"><h3>{esc(w['kit.title'])}</h3><p>{esc(w['kit.text'])}</p>"
            f"<table class=\"results kit\"><tbody>{body}</tbody></table><h4>{esc(w['kit.audit.title'])}</h4>{log}</section>")


def cost_panel(w):
    """Cost and time at scale, from data/out/scale.json."""
    data = read("data", "out", "scale.json")
    if not data:
        return ""
    sc = data["scale"]
    code = w.fill("cost.code", documents=f"{sc['documents']:,}", clauses=f"{sc['clauses']:,}", seconds=sc["seconds"])
    rows = []
    for step, e in data["ai"].items():
        if e["estimate"] is None:
            rows.append(f"<tr><td>{esc(w['steps.' + STEP_KEY[step] + '.name'])}</td><td class=\"n\">{e['items']:,}</td>"
                        f"<td>{esc(e['model'])}</td><td colspan=\"2\" class=\"muted\">{esc(w['cost.waiting'])}</td></tr>")
        else:
            rows.append(f"<tr><td>{esc(w['steps.' + STEP_KEY[step] + '.name'])}</td><td class=\"n\">{e['items']:,}</td>"
                        f"<td>{esc(e['model'])}</td><td class=\"n\">{e['tokens_in']:,} and {e['tokens_out']:,}</td>"
                        f"<td class=\"n\">${e['estimate']:,.2f}</td></tr>")
    head = "".join(f"<th{' class=\"n\"' if k in ('items', 'tokens', 'estimate') else ''}>{esc(h)}</th>"
                   for k, h in w.table("cost.head").items())
    total = [e["estimate"] for e in data["ai"].values()]
    note = (w.fill("cost.total", dollars=f"{sum(total):,.2f}") if all(t is not None for t in total)
            else w["cost.partial"])
    chk = data.get("sample_check")
    sample = ""
    if chk:
        off = f"{chk['off_by']:+.0%}"
        sample = f"<p>{esc(w.fill('cost.sample', n=chk['sample'], off=off))}</p>"
    return (f"<section class=\"panel\" id=\"how-cost\"><h3>{esc(w['cost.title'])}</h3><p>{esc(code)}</p>"
            f"<table class=\"results\"><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
            f"<p class=\"muted\">{esc(note)}</p>{sample}</section>")


def embed_panel(w, data=None):
    """Do embeddings earn their place? The experiment's arms and the choice code made, from evals/embeddings.json."""
    e = data or read("evals", "embeddings.json")
    head = f"<section class=\"panel\" id=\"how-embed\"><h3>{esc(w['embed.title'])}</h3><p>{esc(w['embed.text'])}</p>"
    if not e:
        return head + f"<p class=\"muted\">{esc(w['embed.waiting'])}</p></section>"
    c, n = e["cost_per_library"], e["pairing"]["code"]["of"]
    cost = {"code": (0.0, 0.0), "embeddings": (c["embeddings"], c["embeddings_seconds"]),
            "extractor": (c["extractor"], c["extractor_seconds"]),
            "all": (c["embeddings"] + c["extractor"], c["embeddings_seconds"] + c["extractor_seconds"])}
    def usd(v):
        return "$0" if not v else f"${v:.4f}" if v < 0.01 else f"${v:.2f}"
    pair = "".join(f"<tr><td>{esc(w['embed.arm.' + a])}</td><td class=\"n\">{e['pairing'][a]['paired']} of {n}</td>"
                   f"<td class=\"n\">{e['pairing'][a]['wrong']}</td><td class=\"n\">{usd(cost[a][0])}</td>"
                   f"<td class=\"n\">{cost[a][1]:.0f} s</td></tr>" for a in ("code", "embeddings", "extractor", "all"))
    s, q = e["search"], e["search"]["questions"]
    arms = ("bm25", "bm25_wide", "hybrid") + tuple(a for a in e.get("exploratory", []) if a in s)
    found = "".join(f"<tr{' class=\"muted\"' if a in e.get('exploratory', []) else ''}><td>{esc(w['embed.search.' + a])}"
                    f"</td><td class=\"n\">{s[a]['gold']} of {q}</td><td class=\"n\">{s[a]['both']} of {q}</td></tr>"
                    for a in arms)
    explore = (f"<p>{esc(w.fill('embed.explore', both=s['hybrid_wide']['both'], q=q, base=s['bm25_wide']['both'], lost=s['lost_wide'] or w['embed.none']))}</p>"
               if "hybrid_wide" in e.get("exploratory", []) and "hybrid_wide" in s else "")

    def table(key, rows):
        cells = "".join(f"<th{' class=\"n\"' if i else ''}>{esc(v)}</th>" for i, v in enumerate(w.table(key).values()))
        return f"<table class=\"results\"><thead><tr>{cells}</tr></thead><tbody>{rows}</tbody></table>"
    note = w.fill("embed.note", model=e["model"], threshold=e["threshold"], libraries=len(e["held"]),
                  dev=" and ".join(e["dev"]))
    return (head + f"<h4>{esc(w['embed.pair.title'])}</h4>{table('embed.pair.head', pair)}"
            f"<p class=\"verdict-line\">{esc(w['embed.choice.pairing.' + e['choice']['pairing']])}</p>"
            f"<h4>{esc(w['embed.search.title'])}</h4>{table('embed.search.head', found)}"
            f"<p class=\"verdict-line\">{esc(w['embed.choice.search.' + e['choice']['search']])}</p>{explore}"
            f"<p class=\"muted\">{esc(note)}</p></section>")


def routing_panel(w):
    """The Model routing panel, built in app/routing_view.py."""
    return routing_view.panel(w)


def bullets(w, key):
    return "<ul class=\"plain\">" + "".join(f"<li>{esc(x)}</li>" for x in w.table(key).values()) + "</ul>"


def render(w, files):
    rows = ai_map(w)
    head = "".join(f"<th>{esc(h)}</th>" for h in w.table("aimap.head").values())
    body = "".join("<tr>" + "".join(f"<td class=\"{KIND_CLASS.get(c, '')}\">{esc(c)}</td>" if i == 1 else f"<td>{esc(c)}</td>"
                                    for i, c in enumerate(r)) + "</tr>" for r in rows)
    steps = "".join(f"<div class=\"step-card\"><h4>{icon('spark')}{esc(w['steps.' + k + '.name'])}</h4><p><strong>"
                    f"{esc(w['steps.may'])}</strong> {esc(w['steps.' + k + '.may'])}</p><p><strong>{esc(w['steps.never'])}"
                    f"</strong> {esc(w['steps.' + k + '.never'])}</p></div>" for k in ("a1", "a2", "a3", "a4", "a5"))
    split = "".join(f"<div><h4>{esc(w['split.' + k + '.title'])}</h4>{bullets(w, 'split.' + k)}</div>"
                    for k in ("alone", "engineer", "guardrails"))
    weeks = "".join(f"<li><strong>{esc(w['start.' + k + '.title'])}</strong> {esc(w['start.' + k])}</li>"
                    for k in ("w1", "w2", "w3", "w4"))
    return (f"<section class=\"tab\" id=\"t-how\" role=\"tabpanel\" aria-labelledby=\"tab-how\">"
            f"<section class=\"panel\" id=\"how-arch\"><h2>{esc(w['arch.title'])}</h2><p>{esc(w['arch.text'])}</p>"
            f"{diagram(w)}{diagram_list(w)}</section>"
            f"<section class=\"panel\" id=\"how-map\"><h3>{esc(w['aimap.title'])}</h3><p>{esc(w['aimap.text'])}</p>"
            f"<table class=\"aimap\"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></section>"
            f"<section class=\"panel\" id=\"how-steps\"><h3>{esc(w['steps.title'])}</h3><div class=\"step-cards\">{steps}"
            f"</div></section>{results_panel(w)}{routing_panel(w)}{embed_panel(w)}{cost_panel(w)}"
            f"<section class=\"panel\" id=\"how-split\"><h3>{esc(w['split.title'])}</h3><p>{esc(w['split.text'])}</p>"
            f"<div class=\"grid3\">{split}</div></section>"
            f"<section class=\"panel\" id=\"how-limits\"><h3>{esc(w['limits.title'])}</h3>{bullets(w, 'limits.list')}</section>"
            f"<section class=\"panel\" id=\"how-start\"><h3>{esc(w['start.title'])}</h3><p>{esc(w['start.text'])}</p>"
            f"<ol class=\"weeks\">{weeks}</ol></section>{kit_panel(w)}{code_view.render(w)}</section>")
