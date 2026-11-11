"""How far two sets of labels agree beyond chance, by Cohen's kappa.

kappa = (observed agreement - agreement expected by chance) / (1 - agreement expected by chance), where chance comes
from how often each labeler uses each label. 1 is full agreement and 0 is no better than chance. The Decisions tab
shows it for the two experts before the specialist's decisions and after them.
"""
from collections import Counter


def kappa(a, b):
    """Cohen's kappa over the items both label sets share, rounded to three places, or None when they share none."""
    ids = sorted(set(a) & set(b))
    if not ids:
        return None
    n = len(ids)
    observed = sum(a[i] == b[i] for i in ids) / n
    ca, cb = Counter(a[i] for i in ids), Counter(b[i] for i in ids)
    chance = sum(ca[k] * cb[k] for k in ca) / (n * n)
    return 1.0 if chance == 1 else round((observed - chance) / (1 - chance), 3)
