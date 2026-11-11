"""The AI steps' system prompts, with the rule vocabulary and role list appended from the code that checks them, so
the prompt and the validator can never disagree about what's allowed. Each prompt's hash identifies it in every
recording, and a scored run refuses a prompt whose hash changed after its freeze.
"""
import hashlib
from pathlib import Path

from engine import lexicon, values

HERE = Path(__file__).resolve().parent.parent
FILES = {"extract": "extract.md", "classify": "classify.md", "draft": "draft.md", "judge": "judge.md", "assist": "assist.md"}


def vocabulary():
    lines = []
    for attr in sorted(lexicon.L):
        spec = lexicon.L[attr]
        actor = f", the rule belongs to the {values.ROLES_BY_ID[spec['actor']]}" if spec.get("actor") else ""
        lines.append(f"- {attr}: {lexicon.LABELS[attr]} ({spec['type']} value{actor})")
    return "\n".join(lines)


def role_list():
    return "\n".join(f"- {rid}: {name}" for name, rid in sorted(values.ROLES.items(), key=lambda x: x[1]))


def system(step):
    text = HERE.joinpath("prompts", FILES[step]).read_text(encoding="utf-8").strip()
    if step == "extract":
        text += "\n\n## The vocabulary\n\n" + vocabulary() + "\n\n## The role list\n\n" + role_list()
    return text + "\n"


def prompt_hash(step):
    return hashlib.sha256(system(step).encode()).hexdigest()
