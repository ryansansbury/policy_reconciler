"""The specialist's rulings on the judge's flags, which code applies the way it applies the decisions on the disputed groups.

A rule covers every flag on one criterion whose evidence is one of its words, like an added "Staff" that names who
carries out an instruction. A ruling on one draft covers that draft's exact text, keyed the way judging.draft_key
keys it, and names its library's seed, since group ids are only unique within one library. Each ruling says the flag
is harmless, that the gap is in the source policy itself, or that it's real. A real flag goes back to the drafter as a
specialist's note on its group, and the group is drafted again.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RULINGS = HERE.joinpath("evals", "flag_rulings.json")
VERDICTS = ("harmless", "source_gap", "real")


def load(path=None):
    path = Path(path or RULINGS)
    return json.loads(path.read_text()) if path.exists() else {"rules": {}, "drafts": {}}


def words(evidence):
    return str(evidence or "").strip().strip(".,\"'").lower()


def ruling(key, criterion, evidence, record=None):
    """The ruling that covers one failed criterion on one draft, or None. A ruling on the draft wins over a rule."""
    record = record if record is not None else load()
    d = record["drafts"].get(key)
    if d and d["criterion"] == criterion:
        return d
    return next((r for r in record["rules"].values() if r["criterion"] == criterion and words(evidence) in r["words"]),
                None)


def passes(key, grades, record=None):
    """Whether a draft passes the judge once the rulings apply: every criterion passed, or every failed one is covered
    by a harmless or source-gap ruling. A real flag still fails the draft."""
    record = record if record is not None else load()
    for c, v in grades.items():
        if not v["pass"]:
            r = ruling(key, c, v.get("evidence"), record)
            if r is None or r["verdict"] == "real":
                return False
    return True


def notes(seed, record=None):
    """{group: the specialist's note} for the groups of one library whose last draft had a flag ruled real."""
    record = record if record is not None else load()
    return {d["group"]: d["note"] for d in record["drafts"].values()
            if d["verdict"] == "real" and str(d["seed"]) == str(seed)}
