"""The code panel on How it works: the six files that matter most, each linked to its copy in this repo on GitHub.

The page carries no source. Each of the six files gets one line with its name, its path, and what it does, and each box
on the architecture diagram links the file behind it the same way. config/site.json gives the repo's address and branch.
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FEATURED = (("engine/gate.py", "gate"), ("engine/compare.py", "compare"), ("agents/routing.py", "routing"),
            ("agents/validate.py", "validate"), ("evals/score.py", "score"), ("agents/mask.py", "mask"))
BOXES = {"parse": "engine/parse.py", "extract": "engine/extract.py", "a1": "prompts/extract.md",
         "compare": "engine/compare.py", "a2": "prompts/classify.md", "decide": "agents/decisions.py",
         "a3": "prompts/draft.md", "gate": "engine/gate.py", "a4": "prompts/judge.md", "approve": "evals/approvals.json",
         "publish": "engine/publish.py", "a5": "prompts/assist.md", "store": "engine/store.py", "mask": "agents/mask.py"}
esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731


def blob(path):
    """The address of one file of this repo on GitHub."""
    site = json.loads(HERE.joinpath("config", "site.json").read_text(encoding="utf-8"))
    return f"{site['repo']}/blob/{site['branch']}/{path}"


def render(w):
    rows = "".join(f"<li><a href=\"{esc(blob(path))}\" target=\"_blank\" rel=\"noopener\"><strong>"
                   f"{esc(w['code.feat.' + key])}</strong><code>{esc(path)}</code><span>{esc(w['code.note.' + key])}"
                   f"</span></a></li>" for path, key in FEATURED)
    return (f"<section class=\"panel\" id=\"how-code\"><h3>{esc(w['code.title'])}</h3><p>{esc(w['code.text'])}</p>"
            f"<ul class=\"code-links\">{rows}</ul></section>")
