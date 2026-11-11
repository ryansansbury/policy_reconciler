"""HTML for the page, rendered by the build from the view model. Every word comes from WORDS.md, every status pairs
an icon with a word, and every clause shown carries its document, version, date and scope.
"""
import html
import json

from agents.validate import plain
from app import readiness

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
ICONS = {
    "check": "<path d=\"M3 8.5l3 3 7-7\"/>",
    "alert": "<path d=\"M8 2l6.5 11.5h-13z\"/><path d=\"M8 6.5v3.2M8 11.6v.2\"/>",
    "info": "<circle cx=\"8\" cy=\"8\" r=\"6\"/><path d=\"M8 7.2v4M8 5v.2\"/>",
    "play": "<path d=\"M5 3.5l7 4.5-7 4.5z\" fill=\"currentColor\" stroke=\"none\"/>",
    "file": "<path d=\"M4 2h5l3 3v9H4z\"/><path d=\"M9 2v3h3\"/>",
    "spark": "<path d=\"M8 2l1.6 4.4L14 8l-4.4 1.6L8 14l-1.6-4.4L2 8l4.4-1.6z\"/>",
    "person": "<circle cx=\"8\" cy=\"5.5\" r=\"2.5\"/><path d=\"M3 14c.6-3 2.6-4.5 5-4.5s4.4 1.5 5 4.5\"/>",
    "split": "<path d=\"M2 3h5v10H2zM9 3h5v10H9z\"/>",
}
MARK = ("<svg viewBox=\"0 0 32 32\"><rect width=\"32\" height=\"32\" rx=\"8\" fill=\"currentColor\"/><path d=\"M9 11h14M9 16h9"
        "M9 21h14\" stroke=\"#fff\" stroke-width=\"2.6\" stroke-linecap=\"round\"/></svg>")
DECIDER_ICON = {"code": "check", "ai": "spark", "rule": "person"}


def esc(s):
    return html.escape(str(s), quote=True)


def icon(name):
    return f"<svg class=\"icon\" width=\"16\" height=\"16\" viewBox=\"0 0 16 16\" aria-hidden=\"true\">{ICONS[name]}</svg>"


def day(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m - 1]} {d}, {y}"


def shown(value, need, w):
    """A readiness value as the report prints it: a share as a percentage, a count as it is."""
    if value is None:
        return w["ready.unmeasured"]
    return f"{value:.1%}" if isinstance(need, float) and need <= 1 else str(value)


def marked(text, marks):
    """The clause with its values, stated scope and conditions highlighted."""
    out, at = [], 0
    for b, e, kind in marks:
        out.append(esc(text[at:b]) + f"<mark class=\"m-{kind}\">{esc(text[b:e])}</mark>")
        at = e
    return "".join(out) + esc(text[at:])


def scope_words(text):
    """A scope as it reads after "Applies to": a leading common word drops its capital ("all branches"), and a place
    name like Colorado keeps it."""
    first = text.split(" ", 1)[0]
    return text[:1].lower() + text[1:] if first in ("All", "Every", "Each", "Only") else text


class Page:
    def __init__(self, words, vm):
        self.w, self.vm = words, vm
        self.types = words.table("labels.doc_type")
        self.cats = words.table("labels.category")
        self.deciders = words.table("labels.decider")
        self.kinds = words.table("labels.kind")

    # ------------------------------------------------------------------ pieces
    def pill(self, cls, ico, text):
        return f"<span class=\"pill {cls}\">{icon(ico)}{esc(text)}</span>"

    def decider(self, who):
        return self.pill(f"d-{who}", DECIDER_ICON[who], self.deciders[who])

    def side(self, s, role=""):
        w = self.w
        meta = w.fill("side.meta", type=self.types.get(s["type"], s["type"]), version=s["version"],
                      date=day(s["effective"]))
        atoms = "".join(f"<li>{self.decider(a['decided_by'])}<span>{esc(a['label'])}</span>"
                        f"<q>{esc(a['value_text'])}</q></li>" for a in s["atoms"])
        role_html = f"<p class=\"side-role\">{esc(role)}</p>" if role else ""
        return (f"<div class=\"side\">{role_html}<h4>{esc(s['title'])}</h4><p class=\"side-meta\">{esc(meta)}</p>"
                f"<p class=\"side-scope\">{esc(w['side.applies'])} {esc(scope_words(s['applies_to']))}</p>"
                f"<p class=\"side-head\">{esc(s['heading'])}</p><blockquote>{marked(s['text'], s['marks'])}</blockquote>"
                f"<p class=\"side-id\"><code>{esc(s['clause'])}</code></p>"
                f"{'<ul class=atoms>' + atoms + '</ul>' if atoms else ''}</div>")

    def resolution(self, f):
        t = self.vm["titles"]
        return self.w.fill(f"resolution.{f['type']}", keep=t[f["keep"]], change=t[f["change"]])

    def detail(self, f):
        """One finding opened: the verdict, then both sources side by side."""
        w, d = self.w, self.vm["details"][f["id"]]
        if f["type"] == "conflict":
            keep = next(i for i, s in enumerate(d["sides"]) if s["doc"] == f["keep"])
            roles = [w["side.keep"] if i == keep else w["side.change"] for i in range(2)]
            body = "".join(self.side(s, r) for s, r in zip(d["sides"], roles))
            why = esc(plain(f["rationale"]) if f["rationale"] else f["rule"])
        elif f["type"] == "duplicate":
            body = "".join(f"<div class=\"side run\"><h4>{esc(run[0]['title'])}</h4><p class=\"side-meta\">"
                           f"{esc(w.fill('side.meta', type=self.types.get(run[0]['type'], ''), version=run[0]['version'], date=day(run[0]['effective'])))}"
                           f"</p><ol>{''.join('<li>' + esc(s['text']) + '</li>' for s in run)}</ol></div>"
                           for run in d["runs"])
            why = esc(f["rule"])
        else:
            body = "".join(self.side(ch["old"], w["side.old"]) + self.side(ch["current"], w["side.current"])
                           for ch in d["changes"][:1])
            why = esc(w["finding.live"] if f.get("live") else f["rule"])
        head = (f"<div class=\"detail-head\"><div>{self.pill('c-' + f['type'], 'alert', self.cats[f['type']])}"
                f"<h3>{esc(f['label'] or self.cats[f['type']])}</h3><p class=\"muted\">{esc(f['topic_name'])}</p></div>"
                f"<div class=\"detail-who\">{self.decider(f['decided_by'])}</div></div>"
                f"<p class=\"detail-why\">{why}</p>")
        return (f"{head}<div class=\"sides\">{body}</div><p class=\"resolution\">{icon('check')}"
                f"<span>{esc(self.resolution(f))}</span></p>")

    # ------------------------------------------------------------------ the header and the run strip
    def strip(self):
        s, w = self.vm["strip"], self.w
        steps = [("ingested", {"documents": s["documents"], "clauses": f"{s['clauses']:,}"}),
                 ("extracted", {"atoms": s["code_atoms"], "queued": s["queued"]}),
                 ("paired", {"comparisons": f"{s['comparisons']:,}"}),
                 ("compared", {"conflicts": s["code_conflicts"], "variations": s["variations"]}),
                 ("classified", {"pairs": s["to_classifier"], "waiting": s["waiting"]} if s["waiting"]
                  else {"pairs": s["to_classifier"]}),
                 ("ready", {"findings": s["findings"]})]
        out = []
        for n, (key, vals) in enumerate(steps, 1):
            detail_key = f"strip.{key}.detail" + ("_waiting" if key == "classified" and s["waiting"] else "")
            out.append(f"<li class=\"step\" data-step=\"{n}\"><span class=\"dot\">{icon('check')}</span>"
                       f"<span class=\"st\">{esc(w['strip.' + key])}</span>"
                       f"<span class=\"sd\">{esc(w.fill(detail_key, **vals))}</span></li>")
        run = (f"<li class=\"run-cell\"><button type=\"button\" id=\"run\" class=\"run-card\">"
               f"<span class=\"dot\">{icon('play')}</span><span class=\"run-label\">{esc(w['strip.run'])}</span>"
               f"</button></li>")
        return f"<ol class=\"steps\">{run}{''.join(out)}</ol>"

    def header(self, nav):
        w = self.w
        tabs = "".join(f"<li><button type=\"button\" role=\"tab\" id=\"tab-{k}\" data-tab=\"{k}\" aria-controls=\"t-{k}\">"
                       f"{esc(w['tab.' + k])}</button></li>" for k in nav)
        bank = w.fill("header.bank", bank=self.vm["library"]["bank"])
        return (f"<a class=\"skip\" href=\"#main\">{esc(w['page.skip'])}</a>"
                f"<header class=\"top\"><div class=\"bar\"><div class=\"brand\"><span class=\"mark\" aria-hidden=\"true\">"
                f"{MARK}</span><div><h1>{esc(w['page.title'])}</h1><p class=\"line\">{esc(w['page.line'])}</p></div></div>"
                f"<div class=\"bar-right\"><p>{esc(bank)}</p></div></div></header>"
                f"<nav class=\"tabs\" aria-label=\"{esc(w['tab.label'])}\"><ul role=\"tablist\">{tabs}</ul></nav>"
                f"<div class=\"strip\">{self.strip()}</div>")

    # ------------------------------------------------------------------ Library
    def tiles(self):
        w, t = self.w, self.vm["tiles"]
        out = "".join(f"<div class=\"tile t-{k}\"><span class=\"tile-label\">{esc(w['tile.' + k])}</span>"
                      f"<span class=\"tile-value\" data-value=\"{t[k]}\">{t[k]}</span>"
                      f"<span class=\"tile-note\">{esc(self.tile_note(k))}</span></div>"
                      for k in ("conflicts", "duplicates", "superseded", "variations", "decisions", "held"))
        return f"<div class=\"tiles\">{out}</div>"

    def tile_note(self, k):
        """Each tile's note. The contradictions tile says how many code found and how many rules and the AI settled."""
        if k != "conflicts":
            return self.w["tile." + k + ".note"]
        code = self.vm["strip"]["code_conflicts"]
        return self.w.fill("tile.conflicts.note", code=code, rest=self.vm["tiles"]["conflicts"] - code)

    def breakdown(self, title, counts, labels=None):
        total = sum(counts.values()) or 1
        rows = "".join(f"<li><span class=\"bk-label\">{esc((labels or {}).get(k, k))}</span><span class=\"bk-bar\">"
                       f"<span style=\"width:{100 * v / total:.1f}%\"></span></span><span class=\"bk-n\">{v}</span></li>"
                       for k, v in counts.items())
        return f"<div class=\"panel breakdown\"><h3>{esc(title)}</h3><ul>{rows}</ul></div>"

    def hours(self):
        """Hours and cost: the review against an editable manual estimate. The page script does the arithmetic."""
        w, h = self.w, self.vm["hours"]
        fields = "".join(f"<label><span>{esc(w['hours.' + k])}</span><input type=\"number\" min=\"0\" step=\"1\" "
                         f"data-hours=\"{k}\" value=\"{h[k]}\"></label>"
                         for k in ("minutes_per_document", "minutes_per_finding", "hourly_rate"))
        return (f"<section class=\"panel hours\" id=\"hours\" data-documents=\"{self.vm['library']['documents']}\" "
                f"data-findings=\"{len(self.vm['findings'])}\" data-seconds=\"{round(sum(self.vm['timings'].values()), 2)}\" "
                f"data-ai=\"{self.vm['ai_totals']['dollars']}\"><h3>{esc(w['hours.title'])}</h3>"
                f"<div class=\"hours-grid\"><div><p>{esc(w['hours.text'])}</p><div class=\"hours-out\">"
                f"<p id=\"hours-manual\"></p><p id=\"hours-review\"></p><p id=\"hours-saved\" class=\"strong\"></p></div>"
                f"<p class=\"muted\">{esc(w['hours.note'])}</p></div><div class=\"hours-inputs\">{fields}</div></div>"
                f"</section>")

    def change(self):
        w, c = self.w, self.vm.get("change")
        if not c:
            return ""
        text = w.fill("change.text", rule=c["rule"].lower(), title=c["title"], old=c["old"], new=c["new"])
        result = w.fill("change.result", sections=len(c["changed_sections"]), total=c["sections_total"],
                        clauses=c["clauses_reread"], rules=len(c["rules_recompared"]), reused=c["findings_reused"],
                        ms=round(c["seconds"] * 1000, 1), full=round(c["full_seconds"] * 1000))
        created = w.fill("change.created", n=len(c["created"]), old=c["old"])
        titles = "".join(f"<li>{esc(t)}</li>" for t in c["created_titles"])
        return (f"<section class=\"panel change\" id=\"change\"><div class=\"panel-head\"><h3>{esc(w['change.title'])}</h3>"
                f"<button type=\"button\" class=\"btn\" data-reveal=\"change\">{icon('play')}"
                f"<span>{esc(w['change.button'])}</span></button></div><p>{esc(text)}</p>"
                f"<p class=\"muted\">{esc(w['change.who'])}</p><div id=\"change-result\" hidden><p>{esc(result)}</p>"
                f"<p>{esc(created)}</p><ul class=\"plain\">{titles}</ul></div></section>")

    def library(self):
        w, lib = self.w, self.vm["library"]
        intro = w.fill("library.intro", bank=lib["bank"], documents=lib["documents"], clauses=f"{lib['clauses']:,}",
                       older=lib["older"])
        return (f"<section class=\"tab\" id=\"t-library\" role=\"tabpanel\" aria-labelledby=\"tab-library\">"
                f"<div class=\"panel lead\"><h2>{esc(w['library.title'])}</h2><p>{esc(intro)}</p>"
                f"<p class=\"pre-only muted\">{esc(w['library.before'])}</p></div>"
                f"<div class=\"post-only\">{self.tiles()}{self.hours()}{self.change()}</div>"
                f"<div class=\"grid3\">{self.breakdown(w['library.by_type'], lib['by_type'], self.types)}"
                f"{self.breakdown(w['library.by_topic'], lib['by_topic'])}"
                f"{self.breakdown(w['library.by_format'], lib['by_format'], w.table('labels.format'))}</div></section>")

    # ------------------------------------------------------------------ Findings
    def findings(self):
        w = self.w
        cfg = self.vm["risk"]
        weights = "".join(f"<label>{esc(self.cats[c])}<input type=\"number\" min=\"0\" max=\"9\" step=\"1\" "
                          f"data-weight=\"category.{c}\" value=\"{v}\"></label>" for c, v in cfg["category"].items())
        weights += (f"<label>{esc(w['risk.customer'])}<input type=\"number\" min=\"0\" max=\"9\" step=\"1\" "
                    f"data-weight=\"customer_weight\" value=\"{cfg['customer_weight']}\"></label>"
                    f"<label>{esc(w['risk.breadth'])}<input type=\"number\" min=\"0\" max=\"9\" step=\"1\" "
                    f"data-weight=\"breadth_weight\" value=\"{cfg['breadth_weight']}\"></label>")
        options = lambda name, pairs: (f"<label>{esc(w['filter.' + name])}<select data-filter=\"{name}\"><option value=\"\">"
                                       f"{esc(w['filter.all'])}</option>"
                                       + "".join(f"<option value=\"{esc(k)}\">{esc(v)}</option>" for k, v in pairs)
                                       + "</select></label>")
        topics = sorted({(f["topic"], f["topic_name"]) for f in self.vm["findings"]}, key=lambda x: x[1])
        filters = (options("type", self.cats.items()) + options("topic", topics)
                   + options("decided_by", [(k, v) for k, v in self.deciders.items()
                                            if any(f["decided_by"] == k for f in self.vm["findings"])]))
        head = "".join(f"<th>{esc(w['findings.col.' + c])}</th>" for c in ("rank", "type", "rule", "where", "who", "risk"))
        return (f"<section class=\"tab\" id=\"t-findings\" role=\"tabpanel\" aria-labelledby=\"tab-findings\">"
                f"<div class=\"pre-only panel empty\"><p>{esc(w['findings.before'])}</p></div>"
                f"<div class=\"post-only\"><div class=\"controls\">{filters}<span class=\"spacer\"></span>"
                f"<p class=\"count\" id=\"f-count\"></p></div>"
                f"<details class=\"panel weights\"><summary>{esc(w['risk.title'])}</summary><p>{esc(w['risk.formula'])}</p>"
                f"<div class=\"weight-row\">{weights}</div></details>"
                f"<div class=\"list-wrap\"><table class=\"list\" id=\"f-list\"><thead><tr>{head}</tr></thead><tbody>"
                f"</tbody></table></div><article class=\"panel detail\" id=\"f-detail\" aria-live=\"polite\"></article>"
                f"{self.not_flagged()}</div></section>")

    def not_flagged(self):
        w, vm = self.w, self.vm
        t = vm["titles"]
        rows = []
        for v in vm["variations"]:
            d = vm["variation_sides"][v["clause"]]
            names = sorted({t[o.split('/')[0]] for o in v["others"]})
            others = " and ".join(names) if len(names) < 3 else ", ".join(names[:-1]) + ", and " + names[-1]
            rows.append(f"<details class=\"nf\" id=\"v-{esc(v['clause'])}\"><summary><span class=\"pill c-variation\">"
                        f"{icon('info')}{esc(w['nf.variation'])}</span><span>{esc(v['label'])}</span>"
                        f"<q>{esc(v['value_text'])}</q><span class=\"muted\">{esc(d['title'])}</span></summary>"
                        f"<p>{esc(v['reason'])} {esc(w.fill('nf.variation.others', others=others))}</p>"
                        f"{self.side(d)}</details>")
        decoys = []
        for x in vm["decoys"]:
            why = (w.fill("nf.decoy.read", read=x["read"], near=x["near"]) if x["read"]
                   else w.fill("nf.decoy.none", near=x["near"]))
            decoys.append(f"<li><q>{esc(x['text'])}</q><span class=\"muted\">{esc(x['title'])}</span>"
                          f"<p>{esc(why)}</p></li>")
        return (f"<section class=\"panel not-flagged\" id=\"not-flagged\"><h3>{esc(w['nf.title'])}</h3>"
                f"<p>{esc(w.fill('nf.intro', variations=len(vm['variations']), decoys=len(vm['decoys'])))}</p>"
                f"<div class=\"nf-list\">{''.join(rows)}</div><h4>{esc(w['nf.decoys'])}</h4>"
                f"<p class=\"muted\">{esc(w['nf.decoys.note'])}</p><ul class=\"decoys\">{''.join(decoys)}</ul></section>")

    # ------------------------------------------------------------------ Decisions
    def decisions(self):
        w, dv = self.w, self.vm["decisions"]
        cards = []
        for g in dv["groups"]:
            ex = "".join(f"<div class=\"ex\"><p class=\"side-meta\">{esc(s['title'])}, "
                         f"{esc(self.types.get(s['type'], s['type']))} {esc(w.fill('side.version', version=s['version']))}</p>"
                         f"<blockquote>{esc(s['text'])}</blockquote></div>" for s in (g["example"]["a"], g["example"]["b"]))
            experts = "".join(f"<div class=\"expert\"><p class=\"who\">{icon('person')}<strong>{esc(e['name'])}</strong>"
                              f"<span class=\"muted\">{esc(e['role'])}</span></p><p>{self.pill('l-' + e['label'], 'info', e['label'])}</p>"
                              f"<p>{esc(w.get('expert.' + g['kind'] + '.' + e['key'], e['rationale']))}</p></div>"
                              for e in g["experts"])
            d = g["decision"]
            if d:
                outcome = (f"<div class=\"decided\">{self.pill('s-ok', 'check', w['decision.made'])}<p><strong>"
                           f"{esc(w.table('labels.decided')[d['label']])}</strong> {esc(d['reason'])}</p>"
                           f"<p class=\"muted\">{esc(w.fill('decision.changed', version=dv['version']))}</p></div>")
            else:
                outcome = f"<div class=\"decided open\">{self.pill('s-open', 'alert', w['decision.open'])}</div>"
            cards.append(f"<article class=\"panel group\" id=\"g-{g['kind']}\"><div class=\"panel-head\"><h3>"
                         f"{esc(self.kinds[g['kind']])}</h3><span class=\"muted\">{esc(w.fill('decision.count', n=g['count']))}"
                         f"</span></div><p>{esc(w['decision.q.' + g['kind']])}</p><div class=\"examples\">{ex}</div>"
                         f"<div class=\"experts\">{experts}</div>{outcome}</article>")
        before, after = dv["kappa_before"], dv["kappa_after"]
        kappa = w.fill("decision.kappa", before=before, after=after, decided=dv["decided"], groups=len(dv["groups"]))
        return (f"<section class=\"tab\" id=\"t-decisions\" role=\"tabpanel\" aria-labelledby=\"tab-decisions\">"
                f"<div class=\"panel lead\"><h2>{esc(w['decision.title'])}</h2><p>{esc(w['decision.intro'])}</p>"
                f"<p class=\"kappa\">{esc(kappa)}</p></div>{''.join(cards)}</section>")

    # ------------------------------------------------------------------ Readiness
    def readiness(self, results):
        """The report, written by code from the results files. Its recommendation comes from app/readiness.py."""
        w, lib, vm = self.w, self.vm["library"], self.vm
        rows = []
        for cat in ("C", "P", "D", "S", "V_alarms", "N_alarms"):
            r = results["by_category"][cat]
            rows.append(f"<tr><td>{esc(w['ready.cat.' + cat])}</td><td class=\"n\">{r['hit']} of {r['of']}</td></tr>")
        reviewed = w.fill("ready.reviewed", documents=lib["documents"], clauses=f"{lib['clauses']:,}",
                          formats=len(lib["by_format"]), topics=len(lib["by_topic"]))
        rec = readiness.recommend(vm)
        m = rec["measured"]
        dv = vm["decisions"]
        agreement = w.fill("ready.agreement", before=dv["kappa_before"], after=dv["kappa_after"], decided=dv["decided"],
                           groups=len(dv["groups"]))
        cal = (vm.get("drafts") or {}).get("calibration")
        judge = (w.fill("ready.judge", trusted=m["judge_trusted"], of=len(cal["by_criterion"])) if cal
                 else w["ready.judge_none"])
        seconds = round(sum(vm["timings"].values()), 1)
        ai = vm["ai_totals"]
        cost = w.fill("ready.cost", seconds=seconds) + (" " + w.fill("ready.cost_ai", dollars=f"{ai['dollars']:.2f}",
                                                                     calls=ai["calls"]) if ai["calls"] else "")
        if rec["ready"]:
            verdict = f"<p class=\"verdict ok\">{icon('check')}<span>{esc(w['ready.rec.ready'])}</span></p>"
        else:
            unmet = "".join(f"<li>{esc(w.fill('ready.unmet', about=u['about'], value=shown(u['value'], u['need'], w), need=shown(u['need'], u['need'], w)))}</li>"
                            for u in rec["unmet"])
            verdict = (f"<p class=\"verdict\">{icon('alert')}<span>{esc(w['ready.rec.not'])}</span></p>"
                       f"<ul class=\"plain\">{unmet}</ul>")
        limits = "<ul class=\"plain\">" + "".join(f"<li>{esc(x)}</li>" for x in w.table("limits.list").values()) + "</ul>"
        return (f"<section class=\"tab\" id=\"t-readiness\" role=\"tabpanel\" aria-labelledby=\"tab-readiness\">"
                f"<article class=\"panel report\"><p class=\"kicker\">{esc(w['ready.kicker'])}</p><h2>{esc(w['ready.title'])}</h2>"
                f"<p class=\"muted\">{esc(w['ready.by_code'])}</p>{verdict}"
                f"<h3>{esc(w['ready.s1'])}</h3><p>{esc(reviewed)}</p>"
                f"<h3>{esc(w['ready.s2'])}</h3><p>{esc(w['ready.checked'])}</p><h3>{esc(w['ready.s3'])}</h3>"
                f"<p>{esc(w.fill('ready.results', caught=results['caught'], planted=results['planted']))}</p>"
                f"<table class=\"results\"><thead><tr><th>{esc(w['ready.col.cat'])}</th><th class=\"n\">"
                f"{esc(w['ready.col.result'])}</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
                f"<h3>{esc(w['ready.s4'])}</h3><p>{esc(agreement)}</p><h3>{esc(w['ready.s5'])}</h3><p>{esc(judge)}</p>"
                f"<h3>{esc(w['ready.s6'])}</h3><p>{esc(cost)}</p><h3>{esc(w['ready.s7'])}</h3>{limits}"
                f"<h3>{esc(w['ready.s8'])}</h3>{verdict}</article></section>")

    # ------------------------------------------------------------------ Drafts
    def draft_text(self, rendered, allowed):
        """The rendered draft with each filled-in value marked."""
        out = esc(rendered)
        for words in sorted(set(allowed.values()), key=len, reverse=True):
            out = out.replace(esc(words), f"<mark class=\"m-value\">{esc(words)}</mark>", 1)
        return out

    def draft_card(self, g, trusted):
        w = self.w
        d = g["draft"]
        if d:
            gate_pill = self.pill("s-ok", "check", w["drafts.gate.pass"])
        elif g["held"]:
            gate_pill = self.pill("c-conflict", "alert", w["drafts.gate.held"])
        else:
            gate_pill = self.pill("s-open", "info", w["drafts.waiting"])
        if g["approved"]:
            approval = self.pill("s-ok", "person", w.fill("drafts.approved", by=g["approved"].get("by", "")))
        elif g["hold"]:
            approval = self.pill("s-open", "alert", w["drafts.on_hold"])
        else:
            approval = self.pill("s-open", "person", w["drafts.needs_approval"]) if d else ""
        body = ""
        if d and not g["approved"]:
            approval += (f"<button type=\"button\" class=\"btn\" data-approve=\"{g['group']}\">"
                         f"{icon('person')}<span>{esc(w['drafts.approve_demo'])}</span></button>")
        if d:
            diff = "".join(f"<span class=\"df-{op}\">{esc(t)}</span> " for op, t in g["diff"])
            inj = g["injected"]
            problems = "".join(f"<li>{icon('alert')}<span>{esc(x)}</span></li>" for x in inj["problems"])
            grades = ""
            if g["grades"]:
                grades = "".join(
                    f"<li class=\"{'pass' if v['pass'] else 'fail'}\">{icon('check' if v['pass'] else 'alert')}"
                    f"<span>{esc(w['judge.' + c])}</span><span class=\"muted\">"
                    f"{esc(w['judge.trusted'] if trusted.get(c) else w['judge.person'])}</span>"
                    + (f"<q>{esc(v['evidence'])}</q>" if v["evidence"] else "")
                    + (f"<span class=\"ruling\">{esc(w['drafts.ruling.' + v['ruling']['verdict']])} "
                       f"{esc(plain(v['ruling']['reason']))}</span>" if v.get("ruling") else "")
                    + "</li>" for c, v in g["grades"].items())
                grades = f"<h4>{esc(w['drafts.grades'])}</h4><ul class=\"grades\">{grades}</ul>"
            body = (f"<h4 class=\"dr-title\">{esc(d['title'])}</h4><p class=\"dr-text\">"
                    f"{self.draft_text(plain(d['rendered']), g['allowed'])}</p>"
                    f"<details class=\"gate-test\"><summary>{esc(w['drafts.inject'])}</summary>"
                    f"<p class=\"muted\">{esc(w['drafts.inject.note'])}</p><p class=\"dr-text\">{esc(inj['text'])}</p>"
                    f"<ul class=\"problems\">{problems}</ul></details>"
                    f"<details><summary>{esc(w['drafts.diff'])}</summary><p class=\"diff\">{diff}</p></details>{grades}")
        elif g["held"]:
            body = "<ul class=\"problems\">" + "".join(f"<li>{icon('alert')}<span>{esc(x)}</span></li>"
                                                     for x in g["held"]) + "</ul>"
        sources = "".join(f"<li><span class=\"muted\">{esc(c['document']['title'])}</span> {esc(c['text'])}</li>"
                          for c in [g["keep"]] + g["change"])
        return (f"<article class=\"panel draft\" id=\"d-{g['group']}\"><div class=\"panel-head\"><h3>{esc(g['rule'])}</h3>"
                f"<span class=\"pills\">{gate_pill}{approval}</span></div>{body}"
                f"<details><summary>{esc(w.fill('drafts.sources', n=1 + len(g['change'])))}</summary>"
                f"<ul class=\"sources\">{sources}</ul></details></article>")

    def drafts(self):
        w, dv = self.w, self.vm["drafts"]
        cal = dv["calibration"]
        trusted = {c: v["trusted"] for c, v in cal["by_criterion"].items()} if cal else {}
        if cal:
            rows = "".join(f"<tr><td>{esc(w['judge.' + c])}</td><td class=\"n\">{v['agree']} of {v['of']}</td><td>"
                           f"{esc(w['judge.trusted'] if v['trusted'] else w['judge.person'])}</td></tr>"
                           for c, v in cal["by_criterion"].items())
            calib = (f"<table class=\"results\"><thead><tr><th>{esc(w['judge.col.criterion'])}</th><th class=\"n\">"
                     f"{esc(w['judge.col.agree'])}</th><th>{esc(w['judge.col.who'])}</th></tr></thead><tbody>{rows}"
                     f"</tbody></table>")
        else:
            calib = f"<p class=\"muted\">{esc(w['judge.waiting'])}</p>"
        done = sum(1 for g in dv["groups"] if g["draft"])
        intro = w.fill("drafts.intro", groups=len(dv["groups"]), done=done)
        return (f"<section class=\"tab\" id=\"t-drafts\" role=\"tabpanel\" aria-labelledby=\"tab-drafts\">"
                f"<div class=\"panel lead\"><h2>{esc(w['drafts.title'])}</h2><p>{esc(intro)}</p>"
                f"<p class=\"muted\">{esc(w['drafts.rule'])}</p></div>"
                f"<div class=\"panel\" id=\"drafts-judge\"><h3>{esc(w['judge.title'])}</h3><p>{esc(w['judge.intro'])}</p>"
                f"{calib}</div>" + self.draft_cards(dv["groups"], trusted) + "</section>")

    def draft_cards(self, groups, trusted):
        """Every group's card once any draft is recorded, and until then one panel listing the rules waiting."""
        w = self.w
        if any(g["draft"] or g["held"] for g in groups):
            return "".join(self.draft_card(g, trusted) for g in groups)
        rules = "".join(f"<li>{esc(g['rule'])} <span class=\"muted\">{esc(g['keep']['document']['title'])}</span></li>"
                        for g in groups)
        return (f"<div class=\"panel\"><h3>{esc(w['drafts.waiting_title'])}</h3><p class=\"muted\">"
                f"{esc(w['drafts.waiting_text'])}</p><ul class=\"plain cols\">{rules}</ul></div>")

    # ------------------------------------------------------------------ Assistant
    def answer(self, a, when):
        w = self.w
        if not a:
            return f"<div class=\"ans empty\"><p class=\"muted\">{esc(w['assist.waiting'])}</p></div>"
        flag = self.pill("c-conflict", "alert", w["assist.disagree"]) if a["sources_disagree"] else ""
        cites = "".join(f"<li><code>{esc(c['id'])}</code> <span class=\"muted\">{esc(c['title'])}</span></li>"
                        for c in a["cited"])
        return f"<div class=\"ans\">{flag}<p>{esc(plain(a['answer']))}</p><ul class=\"cites\">{cites}</ul></div>"

    def assistant(self):
        w, av = self.w, self.vm["drafts"]["assistant"]
        rows = "".join(f"<article class=\"panel question\"><h3>{esc(q['text'])}</h3><div class=\"ba\">"
                       f"<div><p class=\"kicker\">{esc(w['assist.before'])}</p>{self.answer(q['before'], 'before')}</div>"
                       f"<div><p class=\"kicker\">{esc(w['assist.after'])}</p>{self.answer(q['after'], 'after')}</div>"
                       f"</div></article>" for q in av["questions"])
        return (f"<section class=\"tab\" id=\"t-assistant\" role=\"tabpanel\" aria-labelledby=\"tab-assistant\">"
                f"<div class=\"panel lead\"><h2>{esc(w['assist.title'])}</h2><p>{esc(w['assist.intro'])}</p></div>"
                f"{rows}</section>")

    # ------------------------------------------------------------------ the whole page
    def body(self, nav, results, extra=None):
        w = self.w
        sections = {"library": self.library, "findings": self.findings, "decisions": self.decisions,
                    "drafts": self.drafts, "assistant": self.assistant, "readiness": lambda: self.readiness(results)}
        sections.update(extra or {})
        return (self.header(nav) + f"<main id=\"main\" tabindex=\"-1\">{''.join(sections[k]() for k in nav)}</main>"
                f"<footer><div class=\"wrap\"><p>{esc(w['page.footer'])}</p><p>{esc(w['page.recorded'])}</p>"
                f"<p><a href=\"https://www.{esc(w['page.site'])}/\">{esc(w['page.site'])}</a>"
                f"<span aria-hidden=\"true\"> &middot; </span>"
                f"<a href=\"https://{esc(w['page.repo'])}\">{esc(w['page.source'])}</a></p></div></footer>")


def js_assign(name, obj):
    return f"window.{name} = " + json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + ";\n"
