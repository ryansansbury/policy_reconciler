"""Words that must never ship, and the scan that enforces it.

A private build adds its own list from a client profile's never.txt. This public copy ships none, which leaves
the list empty, and a test plants a word to prove the scan still fails a build. A match is a whole word or
phrase without regard to case, so "cat" never matches "category."
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def words(profile_root=None):
    out = []
    root = Path(profile_root or HERE.joinpath("profiles"))
    for f in sorted(root.glob("*/never.txt")):
        out += [ln.strip().lower() for ln in f.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
    return tuple(dict.fromkeys(out))


def pattern(word_list):
    parts = [r"\b" + re.escape(w).replace(r"\ ", r"\s+") + r"\b" for w in word_list]
    return re.compile("|".join(parts), re.IGNORECASE) if parts else None


def hits(text, word_list=None):
    """Every never-word found in the text, lowercased and in order of first appearance."""
    pat = pattern(word_list if word_list is not None else words())
    if not pat:
        return []
    return list(dict.fromkeys(m.group(0).lower() for m in pat.finditer(text)))
