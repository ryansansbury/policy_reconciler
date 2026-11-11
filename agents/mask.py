"""Mask customer details before any text leaves the machine.

Patterns catch account numbers, identification numbers, phone numbers and email addresses, and a short rule catches
a customer name written right before "account". Every masked span becomes a labeled placeholder, and the count goes
into the audit log. A production deployment would add a dedicated detector for names and addresses, and the
known-limits page says so.
"""
import re

PATTERNS = [
    ("ACCOUNT", re.compile(r"\b[A-Z]{2}-\d{4}-\d{4}-\d{4}\b|\b\d{4}-\d{4}-\d{4}(?:-\d{4})?\b")),
    ("ID", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"\b(?:\(\d{3}\)\s?|\d{3}-)?\d{3}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("NAME", re.compile(r"(?<=: )[A-Z][a-z]+ [A-Z][a-z]+(?=, account)")),
]


def mask(text):
    """(masked text, {label: count})."""
    counts = {}
    for label, pat in PATTERNS:
        text, n = pat.subn(f"[{label}]", text)
        if n:
            counts[label] = counts.get(label, 0) + n
    return text, counts


def mask_payload(obj):
    """Mask every string inside a JSON-ready payload. Returns (payload, total counts)."""
    totals = {}

    def walk(x):
        if isinstance(x, str):
            masked, c = mask(x)
            for k, v in c.items():
                totals[k] = totals.get(k, 0) + v
            return masked
        if isinstance(x, list):
            return [walk(i) for i in x]
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        return x

    return walk(obj), totals
