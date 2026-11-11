"""The CI gate: one command that fails a change before it can ship.

    python3 ci/run_gate.py            from the build folder

It runs every test, the build with its strip check
on every profile, a scan for anything shaped like an API key, and the regression thresholds in config/gate.json. It
prints one line per check and exits 1 when any check fails. The workflow in
.github/workflows/gate.yml runs the same thing on GitHub for every push.
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
DEMO_SEED = 2026

KEY_SHAPES = [re.compile(p) for p in (r"sk-ant-[A-Za-z0-9_-]{20,}", r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}",
                                       r"\bAIza[0-9A-Za-z_-]{35}\b", r"\bAKIA[0-9A-Z]{16}\b",
                                       r"-----BEGIN [A-Z ]*PRIVATE KEY-----")]
SCANNED = ("engine", "agents", "prompts", "app", "generate", "evals", "tests", "owner", "ci", "config",
           "docs", "data/ai_runs", "site")
SUFFIXES = (".py", ".js", ".css", ".md", ".sh", ".json", ".jsonl", ".yml", ".html", ".txt")


def key_shaped(root=HERE):
    """Every file under the scanned folders that holds something shaped like an API key."""
    out = []
    paths = [root.joinpath(n) for n in ("build.py", "WORDS.md", "README.md")]
    for folder in SCANNED:
        paths += sorted(root.joinpath(folder).rglob("*")) if root.joinpath(folder).exists() else []
    for p in paths:
        if p.is_file() and p.suffix in SUFFIXES and "__pycache__" not in p.parts:
            text = p.read_text(encoding="utf-8", errors="replace")
            if any(rx.search(text) for rx in KEY_SHAPES):
                out.append(p.relative_to(root).as_posix())
    return out


COMMA_SO = re.compile(r",\s+so\b", re.IGNORECASE)


def copy_files(root=HERE):
    """Every file of visible copy: the words, the README, the docs and each profile's words and docs."""
    root = Path(root)
    out = [root.joinpath("WORDS.md"), root.joinpath("README.md")]
    out += sorted(root.joinpath("docs").rglob("*.md")) + sorted(root.joinpath("profiles").glob("*/words.md"))
    out += sorted(root.joinpath("profiles").glob("*/docs/*.md"))
    return [p for p in out if p.exists()]


def comma_before_so(root=HERE):
    """Every copy file with a comma before "so," which the project's writing rules never allow."""
    return [p.relative_to(root).as_posix() for p in copy_files(root) if COMMA_SO.search(p.read_text(encoding="utf-8"))]


def thresholds(review, ai, cfg):
    """Every threshold the results miss, as sentences. review is the demo's review summary and ai the AI scores."""
    out = []
    planted = {c: review["score"]["per_category"][c] for c in ("C", "P")}
    caught = sum(v["caught"] for v in planted.values())
    total = sum(v["planted"] for v in planted.values())
    if total and caught / total < cfg["min_recall_cp"]:
        out.append(f"code caught {caught} of {total} planted contradictions, under {cfg['min_recall_cp']:.0%}")
    if review["score"]["summary"]["false_alarms"] > cfg["max_false_alarms"]:
        out.append(f"{review['score']['summary']['false_alarms']} false alarms on variations and look-alikes")
    if review["score"]["summary"]["unexplained"] > cfg["max_unexplained"]:
        out.append(f"{review['score']['summary']['unexplained']} conflict findings match no planted problem")
    for tag, d in (ai or {}).get("drafts", {}).items():
        if d["gate_pass_rate"] is not None and d["gate_pass_rate"] < cfg["min_gate_pass_rate"]:
            out.append(f"drafts for {tag} passed the gate at {d['gate_pass_rate']:.0%}")
    if len((ai or {}).get("audit_problems", [])) > cfg["max_audit_problems"]:
        out.append("the audit log and the recordings disagree")
    return out


def run(cmd):
    r = subprocess.run(cmd, cwd=str(HERE), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]


def main():
    from evals import score
    checks = []
    code, tail = run([sys.executable, "-m", "tests.run"])
    checks.append(("tests", code == 0, tail[0]))
    code, tail = run([sys.executable, "build.py"])
    checks.append(("build and strip check", code == 0, tail[0]))
    so = comma_before_so()
    checks.append(("no comma before so", not so, ", ".join(so) or "none found"))
    keys = key_shaped()
    checks.append(("no key-shaped strings", not keys, ", ".join(keys[:5]) or "none found"))
    review = json.loads(HERE.joinpath("data", "out", f"review_{DEMO_SEED}.json").read_text())
    review["score"] = score.score({"findings": review["findings"], "queue": review["queue"]}, score.load_key(DEMO_SEED))
    ai_path = HERE.joinpath("data", "out", "ai_scores.json")
    ai = json.loads(ai_path.read_text()) if ai_path.exists() else None
    missed = thresholds(review, ai, json.loads(HERE.joinpath("config", "gate.json").read_text()))
    checks.append(("regression thresholds", not missed, "; ".join(missed) or "all met"))
    for name, ok, detail in checks:
        print(f"{'pass' if ok else 'FAIL'}  {name}: {detail}")
    report = {"ran_at": datetime.now().isoformat(timespec="minutes"), "passed": all(ok for _, ok, _ in checks),
              "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks]}
    out = HERE.joinpath("data", "out", "ci_gate.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
