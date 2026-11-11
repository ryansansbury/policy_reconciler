"""Every AI step the recorder runs, in one place: the field that names each item, the list the items travel in, how
many go in one call, and the code that checks the reply. The page and the replay read the same table, so a step
can't be recorded one way and checked another.
"""
import json

from agents import assisting, drafting, judging, validate

STEPS = {
    "extract": {"key": "clause", "many": "clauses", "batch": 10, "check": validate.check_extract},
    "classify": {"key": "pair", "many": "pairs", "batch": 8, "check": validate.check_classify},
    "draft": {"key": "group", "many": "groups", "batch": 3, "check": drafting.check},
    "judge": {"key": "draft", "many": "drafts", "batch": 5, "check": judging.check},
    "assist": {"key": "question", "many": "questions", "batch": 1, "check": assisting.check},
}
REPAIR_NOTE = "Your earlier reply had these problems. Answer again for these items only, fixing them:"


def key(step):
    return STEPS[step]["key"]


def check(step):
    return STEPS[step]["check"]


def user_message(step, batch):
    return json.dumps({STEPS[step]["many"]: batch}, indent=1, ensure_ascii=False)


def repair_message(step, batch, problems):
    return user_message(step, batch) + "\n\n" + REPAIR_NOTE + "\n- " + "\n- ".join(problems)
