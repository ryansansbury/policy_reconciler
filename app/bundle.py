"""Build the page: the view model, the HTML, the data the script reads, and the strip check.

    site/index.html   the page, with app.css and app.js beside it
    site/data.js      window.PR, everything the script shows

The strip check runs on every build. The public profile is rendered too, and the build fails if any never-word
reaches it. The client's own build is checked against every never-word except the ones its own profile uses on
purpose, like the client's name in the footer.
"""
import json
import shutil
from pathlib import Path

from agents import decisions, flow, items
from app import change, drafts, how, never, page, view
from app import words as words_mod
from engine import pipeline
from evals import score

HERE = Path(__file__).resolve().parent.parent
SITE = HERE.joinpath("site")
UI = HERE.joinpath("app", "ui")
NAV = ("library", "findings", "decisions", "drafts", "assistant", "readiness", "how")
UI_KEYS = ("strip.run", "strip.replay", "findings.where", "findings.count",
           "drafts.approved_demo", "hours.manual", "hours.review", "hours.saved")


class StripCheckFailed(SystemExit):
    pass


SITE_CONFIG = HERE.joinpath("config", "site.json")
PREVIEW = HERE.joinpath("docs", "images", "preview.png")


def site_tags():
    """The page's address and its link preview from config/site.json. Without an address the head carries neither."""
    site = json.loads(SITE_CONFIG.read_text(encoding="utf-8")) if SITE_CONFIG.exists() else {}
    url = site.get("url")
    if not url:
        return ""
    tags = [f"<link rel=\"canonical\" href=\"{page.esc(url)}\">", f"<meta property=\"og:url\" content=\"{page.esc(url)}\">"]
    if site.get("image"):
        tags += [f"<meta property=\"og:image\" content=\"{page.esc(url + site['image'])}\">",
                 f"<meta property=\"og:image:width\" content=\"{int(site['image_width'])}\">",
                 f"<meta property=\"og:image:height\" content=\"{int(site['image_height'])}\">",
                 f"<meta property=\"og:image:alt\" content=\"{page.esc(site['image_alt'])}\">",
                 "<meta name=\"twitter:card\" content=\"summary_large_image\">"]
    return "".join(tags)


def view_model(seed, models):
    data = HERE.joinpath("data")
    result = items.library(seed, data)
    dec = decisions.load()
    combined = flow.run(result, str(seed), models=models, decisions=dec)
    kd = data.joinpath("key", str(seed))
    vm = view.View(result, combined, score.load_key(seed), json.loads(kd.joinpath("experts.json").read_text()), dec,
                   eval_pairs=json.loads(kd.joinpath("evals.json").read_text())["pairs"]).build()
    vm["drafts"] = drafts.build(seed)
    vm["change"] = change.scenario(result)
    vm["hours"] = json.loads(HERE.joinpath("config", "hours.json").read_text())
    scores = HERE.joinpath("data", "out", "ai_scores.json")
    if scores.exists():
        s = json.loads(scores.read_text())
        extra = [s["drafts"].get(str(seed), {}).get("totals"), s["judge"].get(str(seed), {}).get("totals"),
                 s["assist"].get(f"before-{seed}", {}).get("totals"), s["assist"].get(f"after-{seed}", {}).get("totals")]
        for t in filter(None, extra):
            vm["ai_totals"]["calls"] += t["calls"]
            vm["ai_totals"]["dollars"] += t["dollars"]
    return vm, combined


def ui_words(w):
    out = {k: w[k] for k in UI_KEYS}
    out.update({f"cat.{k}": v for k, v in w.table("labels.category").items()})
    out.update({f"decider.{k}": v for k, v in w.table("labels.decider").items()})
    return out


def render(w, vm, combined, results, files=None):
    p = page.Page(w, vm)
    body = p.body(NAV, results, {"how": lambda: how.render(w, files)})
    head = (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            f"content=\"width=device-width, initial-scale=1\"><meta name=\"robots\" content=\"index, follow\">"
            f"<meta name=\"referrer\" content=\"no-referrer\"><title>{page.esc(w['page.title'])}</title>"
            f"<meta name=\"description\" content=\"{page.esc(w['page.description'])}\">"
            f"<meta property=\"og:title\" content=\"{page.esc(w['page.title'])}\">"
            f"<meta property=\"og:description\" content=\"{page.esc(w['page.description'])}\">"
            f"<meta property=\"og:type\" content=\"website\">{site_tags()}"
            f"<link rel=\"icon\" href=\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAzMiAzMic+PHJlY3Qgd2lkdGg9JzMyJyBoZWlnaHQ9JzMyJyByeD0nOCcgZmlsbD0nIzQzMzhDQScvPjxwYXRoIGQ9J005IDExaDE0TTkgMTZoOU05IDIxaDE0JyBzdHJva2U9JyNmZmYnIHN0cm9rZS13aWR0aD0nMi42JyBzdHJva2UtbGluZWNhcD0ncm91bmQnLz48L3N2Zz4=\">"
            f"<link rel=\"stylesheet\" href=\"app.css\"></head><body>")
    html = head + body + ("<script src=\"data.js\"></script>"
                          "<script src=\"app.js\"></script></body></html>\n")
    fields = ("id", "type", "topic", "topic_name", "label", "decided_by", "breadth", "keep", "change", "live")
    data = {"ui": ui_words(w), "findings": [{k: f[k] for k in fields} for f in vm["findings"]],
            "detail_html": {f["id"]: p.detail(f) for f in vm["findings"]}, "titles": vm["titles"], "risk": vm["risk"]}
    return html, page.js_assign("PR", data)


def allowed_words(profile):
    """Never-words a profile's own words file uses on purpose."""
    text = HERE.joinpath("profiles", profile, "words.md").read_text(encoding="utf-8")
    return {x for x in never.words() if never.hits(text, [x])}


def strip_check(texts, profile):
    hits = [h for h in never.hits("\n".join(texts)) if h not in allowed_words(profile)]
    if hits:
        raise StripCheckFailed(f"The {profile} build contains never-words: {', '.join(hits)}")
    return []


def build(profile, seed, models, results, out=SITE):
    vm, combined = view_model(seed, models)
    css, js = UI.joinpath("app.css").read_text(), UI.joinpath("app.js").read_text()
    for name in words_mod.profiles():
        html, data = render(words_mod.load(name), vm, combined, results)
        strip_check([html, data, css, js], name)
        if name == profile:
            out.mkdir(parents=True, exist_ok=True)
            out.joinpath("index.html").write_text(html, encoding="utf-8")
            out.joinpath("data.js").write_text(data, encoding="utf-8")
            for f in ("app.css", "app.js"):
                shutil.copyfile(UI.joinpath(f), out.joinpath(f))
            if PREVIEW.exists():
                shutil.copyfile(PREVIEW, out.joinpath("preview.png"))
    return {"findings": len(vm["findings"]), "bytes": out.joinpath("data.js").stat().st_size}
