"""README.md, written by the build from docs/README_TEMPLATE.md, so its results table and AI map come from the same
files and words as the page and never drift from them."""
import json
from pathlib import Path

from app import how
from evals import score_ai

HERE = Path(__file__).resolve().parent.parent
TEMPLATE = HERE.joinpath("docs", "README_TEMPLATE.md")
OUT = HERE.joinpath("README.md")


def results_table():
    code = json.loads(HERE.joinpath("evals", "code_only.json").read_text())["totals"]
    rows = [("Code alone on three held-out libraries", f"{code['caught']} of {code['planted']}",
             f"{code['false_alarms']} of {code['by_category']['V_alarms']['of'] + code['by_category']['N_alarms']['of']}")]
    scored = HERE.joinpath("evals", "ai_scored.json")
    run = score_ai.latest(json.loads(scored.read_text())["runs"]) if scored.exists() else None
    if run:
        for name, s in (("Code alone on three new held-out libraries", [x["code_only"] for x in run["seeds"].values()]),
                        ("Code with the AI steps on the same three libraries",
                         [x["combined"]["summary"] for x in run["seeds"].values()])):
            rows.append((name, f"{sum(x['caught'] for x in s)} of {sum(x['planted'] for x in s)}",
                         str(sum(x["false_alarms"] for x in s))))
    lines = ["| What ran | Planted problems caught | False alarms |", "|---|---|---|"]
    return "\n".join(lines + [f"| {a} | {b} | {c} |" for a, b, c in rows])


def ai_map_table(w):
    head = list(w.table("aimap.head").values())
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in how.ai_map(w)])


def write(w):
    site = json.loads(HERE.joinpath("config", "site.json").read_text(encoding="utf-8"))
    text = TEMPLATE.read_text(encoding="utf-8").format(
        site_url=site["url"], results=results_table(), ai_map=ai_map_table(w),
        limits="\n".join(f"- {x}" for x in w.table("limits.list").values()))
    OUT.write_text(text, encoding="utf-8")
    return OUT
