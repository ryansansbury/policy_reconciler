"""The Model routing panel. For each set of approved vendors it shows every model's quality against its cost with each
step's route ringed, the blended cost of one run, the steps whose quality drops against every vendor approved, and
the routes with their reasons, fallbacks and the cheaper models that missed their bar. Below them sits what the judge
caught in the comparison's drafts.

The chart is one small chart per step, since each step has its own measure, in emphasis color: the route in the
page's accent and every other model in one gray, with hollow marks for the models that miss the bar. Every dot has a
2px surface ring and a 24px hit area whose tooltip lists every model under it, and a table view carries every number.
The accent #4338CA and the gray #8A93A1 were checked by a palette validator on the white surface: contrast of at least
3:1, and a separation between them of 28 for normal vision and 24.7 under simulated color blindness. The gray fails
the validator's chroma floor by design, since it's the color for everything that isn't the route. The page has no
dark mode, so the chart has none.
"""
import json
import math
from pathlib import Path

from agents import routing
from app.page import esc

HERE = Path(__file__).resolve().parent.parent
STEPS = ("extract", "classify", "draft", "judge", "assist")
STEP_KEY = {"extract": "a1", "classify": "a2", "draft": "a3", "judge": "a4", "assist": "a5"}
W, H, LEFT, RIGHT, TOP, BOTTOM = 236, 206, 42, 14, 40, 30
X_LO, X_HI = math.log10(0.05), math.log10(100)
X_TICKS = ((0.1, "$0.10"), (1, "$1"), (10, "$10"), (100, "$100"))
NEAR = 6


def read(*parts):
    p = HERE.joinpath(*parts)
    return json.loads(p.read_text()) if p.exists() else None


def day(iso):
    """A date as the page writes it, like Jan 1, 2027."""
    y, m, d = (int(x) for x in iso.split("-"))
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{months[m - 1]} {d}, {y}"


def pct(v):
    return f"{v * 100:.1f}%".replace(".0%", "%")


def dollars(v):
    return f"${v:,.2f}" if v >= 0.1 or v == 0 else f"${v:.3f}"


def sx(per_thousand):
    return LEFT + (math.log10(max(per_thousand, 0.05)) - X_LO) / (X_HI - X_LO) * (W - LEFT - RIGHT)


def place(p, others, text, bar_y):
    """(dx, dy, anchor) for a route's label: the first of four places around its dot that stays inside the chart, and
    of those the one that covers no other dot and doesn't cross the bar line."""
    wide, tall = len(text) * 6.1, 11
    best = None
    for n, (dx, dy, anchor) in enumerate(((11, 21, "start"), (-11, 21, "end"), (11, -14, "start"), (-11, -14, "end"))):
        x = p["cx"] + dx
        x0, x1 = (x, x + wide) if anchor == "start" else (x - wide, x)
        y1 = p["cy"] + dy
        y0 = y1 - tall
        if x0 < 2 or x1 > W - 2 or y0 < TOP - 2 or y1 > H - BOTTOM - 2:
            continue
        hits = sum(1 for q in others if x0 - 6 <= q["cx"] <= x1 + 6 and y0 - 6 <= q["cy"] <= y1 + 6)
        score = (hits, y0 - 3 <= bar_y <= y1 + 3, n)
        best = min(best, (score, dx, dy, anchor)) if best else (score, dx, dy, anchor)
    if best:
        return best[1:]
    # Too wide for either side: pin it to the nearer edge, under or over the dot, wherever it covers fewer dots.
    dx, anchor = (W - 2 - p["cx"], "end") if p["cx"] > W * 0.5 else (2 - p["cx"], "start")
    x0, x1 = (W - 2 - wide, W - 2) if anchor == "end" else (2, 2 + wide)
    tries = []
    for n, dy in enumerate((21, -14)):
        y1 = p["cy"] + dy
        if TOP - 2 <= y1 - tall and y1 <= H - BOTTOM - 2:
            hits = sum(1 for q in others if x0 - 6 <= q["cx"] <= x1 + 6 and y1 - tall - 6 <= q["cy"] <= y1 + 6)
            tries.append((hits, n, dy))
    return (dx, min(tries)[2], anchor) if tries else (11, 21, "start")


def scale(values):
    """(low, high, ticks) for a facet's quality axis, with room above 100% for the ring."""
    lo = math.floor((min(values) - 0.02) * 20) / 20
    lo = min(lo, 0.95)
    step = 0.05 if 1 - lo <= 0.15 else 0.1
    ticks, t = [], 1.0
    while t >= lo - 1e-9:
        ticks.append(round(t, 2))
        t -= step
    return lo, 1 + (1 - lo) * 0.1, sorted(ticks)


def states(step, plan, results, vendors, drafter_vendor):
    """{model: (state, why)} for one step under one plan. A model from an unapproved vendor isn't drawn."""
    r = plan[step]
    pool = {m: v for m, v in results.items() if v["vendor"] in vendors}
    others = {m: v for m, v in pool.items() if not (step == "judge" and drafter_vendor and v["vendor"] == drafter_vendor)}
    best = max((v["quality"] for v in others.values() if v.get("quality") is not None), default=0)
    out = {}
    for m, v in pool.items():
        if m == r["model"]:
            out[m] = ("held" if r["reason"] == "hold" else "route", "")
        elif m not in others:
            out[m] = ("out", "")
        else:
            ok, why = routing.clears(step, v, best)
            out[m] = ("clears", "") if ok else ("misses", why)
    return out, best


def facet(w, step, plan, results, names, vendors, drafter_vendor):
    """One step's chart: each approved model's measure against its cost per 1,000 items on a log axis."""
    st, best = states(step, plan, results, vendors, drafter_vendor)
    level = routing.bar(step, best)
    pts = []
    for m, (state, why) in st.items():
        y = routing.measure(step, results[m])
        if y is not None and results[m].get("cost_per_item") is not None:
            pts.append({"m": m, "state": state, "why": why, "y": y, "cost": results[m]["cost_per_item"] * 1000})
    if not pts:
        return ""
    lo, hi, ticks = scale([p["y"] for p in pts] + [level])

    def sy(v):
        return TOP + (hi - v) / (hi - lo) * (H - TOP - BOTTOM)

    x1, y1 = W - RIGHT, H - BOTTOM
    out = [f"<text class=\"ft\" x=\"{LEFT - 34}\" y=\"14\">{esc(w['steps.' + STEP_KEY[step] + '.name'])}</text>",
           f"<text class=\"fs\" x=\"{LEFT - 34}\" y=\"28\">{esc(w['route.metric.' + step])}</text>",
           f"<rect class=\"zone\" x=\"{LEFT}\" y=\"{TOP}\" width=\"{x1 - LEFT}\" height=\"{max(0, sy(level) - TOP):.1f}\"/>"]
    for t in ticks:
        out.append(f"<line class=\"grid\" x1=\"{LEFT}\" x2=\"{x1}\" y1=\"{sy(t):.1f}\" y2=\"{sy(t):.1f}\"/>"
                   f"<text class=\"tick\" x=\"{LEFT - 5}\" y=\"{sy(t) + 3.5:.1f}\" text-anchor=\"end\">{pct(t)}</text>")
    for v, label in X_TICKS:
        out.append(f"<line class=\"grid\" x1=\"{sx(v):.1f}\" x2=\"{sx(v):.1f}\" y1=\"{TOP}\" y2=\"{y1}\"/>"
                   f"<text class=\"tick\" x=\"{sx(v):.1f}\" y=\"{y1 + 14}\" text-anchor=\"middle\">{label}</text>")
    out.append(f"<line class=\"axis\" x1=\"{LEFT}\" x2=\"{x1}\" y1=\"{y1}\" y2=\"{y1}\"/>"
               f"<line class=\"bar\" x1=\"{LEFT}\" x2=\"{x1}\" y1=\"{sy(level):.1f}\" y2=\"{sy(level):.1f}\"/>")
    for p in pts:
        p["cx"], p["cy"] = sx(p["cost"]), sy(p["y"])
        held = " " + w["route.state.held_short"] if p["state"] == "held" else ""
        state = w["route.state." + p["state"]] + (". " + w["route.why." + p["why"]] if p["why"] else "")
        p["row"] = {"v": f"{pct(p['y'])} at {dollars(p['cost'])}", "n": names[p["m"]] + held, "s": state,
                    "k": "route" if p["state"] == "held" else p["state"]}
    order = {"out": 0, "misses": 1, "clears": 2, "route": 3, "held": 3}
    for p in sorted(pts, key=lambda q: (order[q["state"]], q["cost"])):
        rows = [q["row"] for q in sorted(pts, key=lambda q: q is not p)
                if math.hypot(q["cx"] - p["cx"], q["cy"] - p["cy"]) <= NEAR]
        aria = ". ".join(f"{r['n']} {r['v']} per 1,000 items. {r['s']}" for r in rows)
        ring = (f"<circle class=\"ring\" cx=\"{p['cx']:.1f}\" cy=\"{p['cy']:.1f}\" r=\"9\"/>"
                if p["state"] in ("route", "held") else "")
        out.append(f"<g class=\"pt s-{'route' if p['state'] == 'held' else p['state']}\" tabindex=\"0\" role=\"img\" "
                   f"aria-label=\"{esc(aria)}\" data-tip=\"{esc(json.dumps(rows))}\">"
                   f"<circle class=\"hit\" cx=\"{p['cx']:.1f}\" cy=\"{p['cy']:.1f}\" r=\"12\"/>{ring}"
                   f"<circle class=\"dot\" cx=\"{p['cx']:.1f}\" cy=\"{p['cy']:.1f}\" r=\"{4 if p['state'] in ('misses', 'out') else 5}\"/></g>")
        if p["state"] in ("route", "held"):
            text = names[p["m"]] + (" " + w["route.state.held_short"] if p["state"] == "held" else "")
            dx, dy, anchor = place(p, [q for q in pts if q is not p], text, sy(level))
            out.append(f"<text class=\"lbl\" x=\"{p['cx'] + dx:.1f}\" y=\"{p['cy'] + dy:.1f}\" "
                       f"text-anchor=\"{anchor}\">{esc(text)}</text>")
    label = w.fill("route.chart.aria", step=w["steps." + STEP_KEY[step] + ".name"])
    return (f"<svg class=\"facet\" viewBox=\"0 0 {W} {H}\" width=\"{W}\" height=\"{H}\" role=\"group\" "
            f"aria-label=\"{esc(label)}\">{''.join(out)}</svg>")


def legend(w):
    keys = (("route", "<circle class=\"ring\" cx=\"9\" cy=\"8\" r=\"6.5\"/><circle class=\"dot\" cx=\"9\" cy=\"8\" r=\"3.5\"/>"),
            ("clears", "<circle class=\"dot\" cx=\"9\" cy=\"8\" r=\"4\"/>"),
            ("misses", "<circle class=\"dot\" cx=\"9\" cy=\"8\" r=\"3.5\"/>"),
            ("out", "<circle class=\"dot\" cx=\"9\" cy=\"8\" r=\"3.5\"/>"),
            ("bar", "<rect class=\"zone\" x=\"0\" y=\"0\" width=\"18\" height=\"8\"/><line class=\"bar\" x1=\"0\" x2=\"18\" y1=\"8\" y2=\"8\"/>"))
    items = "".join(f"<li class=\"s-{k}\"><svg width=\"18\" height=\"16\" viewBox=\"0 0 18 16\" aria-hidden=\"true\">{svg}</svg>"
                    f"<span>{esc(w['route.legend.' + k])}</span></li>" for k, svg in keys)
    return f"<ul class=\"legend\">{items}</ul>"


def table_view(w, plan, comparison, names, vendors):
    rows = []
    drafter = plan.get("draft", {}).get("model")
    dv = comparison["steps"].get("draft", {}).get(drafter, {}).get("vendor") if drafter else None
    for step in STEPS:
        results = comparison["steps"].get(step, {})
        st, _ = states(step, plan, results, vendors, dv)
        for m, (state, why) in sorted(st.items(), key=lambda kv: results[kv[0]]["cost_per_item"] or 0):
            y = routing.measure(step, results[m])
            result = w["route.state." + state] + (". " + w["route.why." + why] if why else "")
            rows.append(f"<tr><td>{esc(w['steps.' + STEP_KEY[step] + '.name'])}</td><td>{esc(names[m])}</td>"
                        f"<td class=\"n\">{pct(y) if y is not None else ''}</td>"
                        f"<td class=\"n\">{dollars(results[m]['cost_per_item'] * 1000)}</td><td>{esc(result)}</td></tr>")
    head = "".join(f"<th{' class=\"n\"' if k in ('measure', 'cost') else ''}>{esc(v)}</th>"
                   for k, v in w.table("route.table.head").items())
    return (f"<details class=\"table-view\"><summary>{esc(w['route.table'])}</summary><table class=\"results\">"
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></details>")


def routes_table(w, plan, comparison, names, counts):
    reasons = json.loads(HERE.joinpath("config", "client_policy.json").read_text()).get("hold_reasons", {})
    rows = []
    for step in STEPS:
        r = plan.get(step)
        if not r:
            continue
        results = comparison["steps"][step]
        why = w["route.reason." + r["reason"]]
        if r["reason"] == "hold" and reasons.get(step):
            why += " " + reasons[step]
        if r.get("unheld"):
            why += " " + w.fill("route.unheld", model=names[r["unheld"]])
        chosen = results.get(r["model"], {}).get("cost_per_item") if r["model"] else None
        cheaper = [m for m in results if m != r["model"] and m in r["rejected"] and
                   (chosen is None or results[m]["cost_per_item"] < chosen)]
        cheaper = "".join(f"<li><strong>{esc(names[m])}</strong> <span class=\"muted\">{esc(w['route.why.' + r['rejected'][m]])}"
                          f"</span></li>" for m in sorted(cheaper, key=lambda m: results[m]["cost_per_item"]))
        if step in counts and r["model"]:
            cost = dollars(counts[step] * chosen)
        elif step == "assist" and r["model"]:
            cost = w.fill("route.per_question", dollars=dollars(chosen * 1000))
        else:
            cost = w["route.none"]
        rows.append(f"<tr><td>{esc(w['steps.' + STEP_KEY[step] + '.name'])}</td>"
                    f"<td>{esc(names.get(r['model'], w['route.none']))}</td><td>{esc(why)}</td>"
                    f"<td>{esc(', '.join(names.get(m, m) for m in r['fallbacks']) or w['route.no_fallback'])}</td>"
                    f"<td>{'<ul class=\"plain\">' + cheaper + '</ul>' if cheaper else esc(w['route.no_fallback'])}</td>"
                    f"<td class=\"n\">{esc(cost)}</td></tr>")
    head = "".join(f"<th{' class=\"n\"' if k == 'scale' else ''}>{esc(v)}</th>" for k, v in w.table("route.head").items())
    return (f"<table class=\"results routes\"><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>")


def blend_line(w, cost, base, documents):
    """What one review of the scale library costs on these routes against the models each step started with, as a
    share. The dollar estimate lives in the cost panel, built from the demo's own tokens, so the page has one figure."""
    if not documents or not base:
        return ""
    change = round(100 * (cost - base) / base)
    key = "route.blend.same" if abs(change) < 2 else "route.blend.less" if change < 0 else "route.blend.more"
    return w.fill(key, documents=f"{documents:,}", pct=abs(change)) if key != "route.blend.same" else \
        w.fill(key, documents=f"{documents:,}")


def moves(w, plan, later, when, names, priced_later):
    """One line for each step whose route changes once a scheduled price change takes effect."""
    out = []
    for s in STEPS:
        now, then = (plan.get(s) or {}).get("model"), (later.get(s) or {}).get("model")
        if when and now and then and now != then:
            cause = now if now in priced_later else priced_later[0]
            out.append(w.fill("route.after", step=w["steps." + STEP_KEY[s] + ".name"], new=names[then],
                              date=day(when), model=names[cause]))
    return out


def changes(w, plan, full, comparison):
    """Each step whose quality drops against the plan with every vendor approved, or goes to a person."""
    out = []
    for step in STEPS:
        r, f = plan.get(step), full.get(step)
        if not r or not f:
            continue
        name = w["steps." + STEP_KEY[step] + ".name"]
        if r["model"] is None and f["model"] is not None:
            out.append(w.fill("route.person", step=name))
        elif r["model"] and f["model"]:
            was = routing.measure(step, comparison["steps"][step][f["model"]])
            now = routing.measure(step, comparison["steps"][step][r["model"]])
            if None not in (was, now) and now < was - 1e-9:
                out.append(w.fill("route.drop", step=name, was=pct(was), now=pct(now)))
    return out


def caught(w, comparison, names):
    """What the judge caught in every model's comparison drafts, the drafts the gate had passed."""
    rows, ruled = [], 0
    for m, r in sorted(comparison["steps"].get("draft", {}).items(), key=lambda kv: kv[1]["cost_per_item"]):
        ruled += r.get("ruled", 0)
        for f in r.get("judge_failed", []):
            for c, ev in f["flags"].items():
                rows.append(f"<tr><td>{esc(names[m])}</td><td>{esc(f['rule'])}</td><td>{esc(w['judge.' + c])}</td>"
                            f"<td><q>{esc(ev)}</q></td></tr>")
    if not rows:
        return ""
    head = "".join(f"<th>{esc(v)}</th>" for v in w.table("route.caught.head").values())
    note = f"<p class=\"muted\">{esc(w.fill('route.caught.ruled', n=ruled))}</p>" if ruled else ""
    return (f"<h4>{esc(w['route.caught.title'])}</h4><p>{esc(w['route.caught.text'])}</p>"
            f"<table class=\"results\"><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>{note}")


def panel(w):
    c = read("evals", "model_comparison.json")
    if not c or not c.get("routes"):
        return (f"<section class=\"panel\" id=\"how-routing\"><h3>{esc(w['route.title'])}</h3><p>{esc(w['route.text'])}</p>"
                f"<p class=\"muted\">{esc(w['route.waiting'])}</p></section>")
    cfg = json.loads(HERE.joinpath("config", "models.json").read_text())
    names = {m["id"]: m["label"] for m in cfg["models"]}
    scale_out = read("data", "out", "scale.json")
    counts = dict(scale_out["scale"]["items"], judge=scale_out["scale"]["items"]["draft"]) if scale_out else {}
    documents = scale_out["scale"]["documents"] if scale_out else None
    start = {s: m for s, m in cfg["steps"].items()}
    base, _ = routing.blend(c, {s: {"model": m} for s, m in start.items()}, counts)
    combos = sorted(c["routes"], key=lambda k: (-len(k.split(" + ")), k))
    priced_later = [m["id"] for m in cfg["models"] if m.get("price_after")]
    full_key = combos[0]
    options = "".join(f"<option value=\"{esc(k)}\">{esc(k)}</option>" for k in combos)
    views = []
    for n, combo in enumerate(combos):
        plan = c["routes"][combo]
        vendors = set(combo.split(" + "))
        drafter = plan.get("draft", {}).get("model")
        dv = c["steps"].get("draft", {}).get(drafter, {}).get("vendor") if drafter else None
        facets = "".join(facet(w, s, plan, c["steps"][s], names, vendors, dv) for s in STEPS if s in c["steps"])
        cost, people = routing.blend(c, plan, counts)
        blend = blend_line(w, cost, base, documents)
        drops = changes(w, plan, c["routes"][full_key], c)
        later = c.get("after") or {}
        moved = moves(w, plan, later.get("routes", {}).get(combo, {}), later.get("from"), names, priced_later)
        drops_html = "" if combo == full_key else (
            f"<h4>{esc(w['route.drops.title'])}</h4>"
            + ("<ul class=\"plain drops\">" + "".join(f"<li>{esc(x)}</li>" for x in drops) + "</ul>" if drops
               else f"<p class=\"muted\">{esc(w['route.no_drops'])}</p>"))
        views.append(f"<div class=\"route-view\" data-vendors=\"{esc(combo)}\"{'' if n == 0 else ' hidden'}>"
                     f"<p class=\"blend\">{esc(blend)}</p>"
                     + "".join(f"<p class=\"muted\">{esc(x)}</p>" for x in moved) + drops_html +
                     f"<figure class=\"route-chart\"><figcaption><strong>{esc(w['route.chart.title'])}</strong> "
                     f"<span class=\"muted\">{esc(w['route.chart.text'])}</span></figcaption>"
                     f"<div class=\"facets\">{facets}</div>{legend(w)}"
                     f"<p class=\"axis-note muted\">{esc(w['route.chart.x'])}</p>"
                     f"{table_view(w, plan, c, names, vendors)}</figure>"
                     f"{routes_table(w, plan, c, names, counts)}</div>")
    pricing = c.get("pricing", {})
    note = (f"<p class=\"muted\">{esc(w.fill('route.pricing', tokens=f'{pricing['client_context_tokens']:,}'))}</p>"
            if pricing.get("client_context_tokens") else "")
    return (f"<section class=\"panel\" id=\"how-routing\"><h3>{esc(w['route.title'])}</h3><p>{esc(w['route.text'])}</p>"
            f"<div class=\"controls\"><label>{esc(w['route.vendors'])}<select id=\"vendors\">"
            f"{options}</select></label></div>{''.join(views)}{note}{caught(w, c, names)}"
            f"<div class=\"viz-tip\" id=\"viz-tip\" role=\"status\" hidden></div></section>")
