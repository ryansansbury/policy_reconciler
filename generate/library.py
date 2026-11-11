"""The base library: every document with its sections and clauses, every rule stated the way the bank intends.

Nothing here is wrong yet. catalog.py plants the contradictions, duplicates, outdated versions, variations and
decoys afterward, so the clean library and the plants stay separate and the answer key knows exactly what changed.

A clause is a dict with its text, its kind (rule, step, text, row or question) and, for rules, its gold atoms: the
attribute it sets, the value, the actor, and the scope it applies to. The engine never sees gold atoms. They exist
only for the answer key.
"""
from datetime import date, timedelta

from generate import bank, content, taxonomy
from generate.values import STYLES, render

DEPOSIT_TOPICS = {"acct_open", "fees", "overdraft", "holds", "disputes", "dormant"}
FORMATS = {"policy": (("docx", 7), ("html", 3)), "procedure": (("docx", 6), ("html", 3), ("md", 1)),
           "job_aid": (("docx", 5), ("md", 5)), "faq": (("html", 6), ("md", 4)), "bulletin": (("html", 6), ("md", 4)),
           "addendum": (("docx", 1),)}
TYPE_CODES = {"policy": "POL", "procedure": "PRO", "job_aid": "JA", "faq": "FAQ", "bulletin": "BUL", "addendum": "ADD"}


def weighted(rng, pairs):
    total = sum(w for _, w in pairs)
    r = rng.uniform(0, total)
    for item, w in pairs:
        r -= w
        if r <= 0:
            return item
    return pairs[-1][0]


def doc_lines(topic, title):
    """The business lines a document applies to, from its topic and title."""
    if "Commercial" in title:
        return ["commercial"]
    if "Small Business" in title:
        return ["small_business"]
    if "Consumer" in title:
        return ["consumer"]
    return list(taxonomy.DEPOSIT_LINES if topic in DEPOSIT_TOPICS else taxonomy.ALL_LINES)


def effective(rng, kind):
    """An effective date on or before the library's as-of date."""
    end = date.fromisoformat(bank.AS_OF)
    span = {"policy": 900, "procedure": 700, "job_aid": 500, "faq": 400, "bulletin": 600, "addendum": 300}[kind]
    return (end - timedelta(days=rng.randint(30, span))).isoformat()


def new_doc(rng, kind, topic, title, number, states=None):
    code = taxonomy.TOPIC_CODES.get(topic, "") if topic else ""
    doc_id = f"{TYPE_CODES[kind]}-{code}-{number:02d}" if code else f"{TYPE_CODES[kind]}-{states[0]}-01"
    version = rng.randint(2, 6) if kind == "policy" else rng.randint(1, 4)
    lines = doc_lines(topic, title) if topic else list(taxonomy.ALL_LINES)
    return {"id": doc_id, "version": version, "key": f"{doc_id}@v{version}", "type": kind, "title": title,
            "topic": topic, "dept": taxonomy.TOPICS[topic]["dept"] if topic else "Compliance",
            "owner": rng.choice(bank.OWNERS), "effective": effective(rng, kind),
            "states": list(states or bank.STATES), "lines": lines, "format": weighted(rng, FORMATS[kind]),
            "status": "current", "sections": []}


def section(heading, clauses=None, table=False):
    return {"heading": heading, "clauses": clauses or [], "table": table}


def text_clause(text, kind="step"):
    return {"text": text, "kind": kind, "atoms": [], "plants": []}


def lowercase_first(s):
    return s[0].lower() + s[1:] if s and s[0].isupper() and not s[:2].isupper() else s


def render_rule(attr, value, family, style, lines, scope_prefix=None):
    """A rule's sentence: the template for its family with the value written in the given style."""
    if attr["type"] == "modal":
        text = attr["templates"][value["modal"]][family]
        value_text = None
    else:
        value_text = render(value, style)
        text = attr["templates"][family].format(v=value_text, line=taxonomy.line_phrase(lines))
    if scope_prefix:
        text = scope_prefix + " " + lowercase_first(text)
    return text, value_text


def actor_stated(attr, text):
    if not attr["actor"]:
        return None
    name = bank.ROLES[attr["actor"]]
    return name in text.lower()


def rule_clause(attr, value, family, style, doc, lines=None, scope_prefix=None, states=None, scope_text=None):
    """A rule clause with its gold atom. lines and states default to the document's scope."""
    eff_lines = list(lines) if lines else [x for x in doc["lines"] if x in attr["lines"]] or list(doc["lines"])
    text, value_text = render_rule(attr, value, family, style, eff_lines, scope_prefix)
    stated = actor_stated(attr, text)
    atom = {"attribute": attr["id"], "topic": attr["topic"], "value": value, "value_text": value_text,
            "actor": attr["actor"] or (value["role"] if value["type"] == "role" else None),
            "actor_inferred": stated is False, "lines": eff_lines, "states": list(states or doc["states"]),
            "scope_source": "clause" if (attr["scoped"] or scope_prefix) else "document",
            "scope_text": scope_text, "family": family, "style": style}
    return {"text": text, "kind": "rule", "atoms": [atom], "plants": []}


def row_clause(attr, value, doc, lines=None):
    """A quick-reference table row: the rule's label and its value, the way job aids write them."""
    eff_lines = list(lines) if lines else [x for x in doc["lines"] if x in attr["lines"]] or list(doc["lines"])
    label = attr["label"]
    if attr["scoped"]:
        label = f"{label} ({taxonomy.line_phrase(eff_lines)})"
    if attr["type"] == "modal":
        value_text = {"must": "Required", "may": "Optional", "must_not": "Not allowed"}[value["modal"]]
    else:
        value_text = render(value)
        if attr["type"] == "time":
            value_text += " Central"
    atom = {"attribute": attr["id"], "topic": attr["topic"], "value": value, "value_text": value_text,
            "actor": attr["actor"] or (value["role"] if value["type"] == "role" else None),
            "actor_inferred": bool(attr["actor"]), "lines": eff_lines, "states": list(doc["states"]),
            "scope_source": "clause" if attr["scoped"] else "document", "scope_text": None, "family": "row",
            "style": None}
    return {"text": f"{label} | {value_text}", "cells": [label, value_text], "kind": "row", "atoms": [atom],
            "plants": []}


def pick_family(rng, attr, value):
    fams = list(attr["templates"][value["modal"]]) if attr["type"] == "modal" else list(attr["templates"])
    plain = [f for f in fams if f not in ("inverse", "words")] or fams
    return rng.choice(plain)


def pick_style(rng, attr, family):
    if family == "words":
        return "words"
    return rng.choice(STYLES.get(attr["type"], (None,))[:2]) if attr["type"] != "modal" else None


def canonical_for(attr, lines):
    """The canonical (lines, value) entries a document with these lines should state."""
    return [(ls, v) for ls, v in attr["canonical"] if set(ls) & set(lines)]


def build(rng, scale=1):
    """The clean library for one seed. Returns the list of documents."""
    docs = []
    for edition in range(scale):
        suffix = f" ({edition + 1})" if scale > 1 else ""
        for topic in taxonomy.TOPICS:
            docs += topic_documents(rng, topic, edition, suffix)
        for state in bank.STATES:
            doc = new_doc(rng, "addendum", None, content.ADDENDA[state] + suffix, 1, states=[state])
            if scale > 1:
                doc["id"] = f"ADD-{state}-{edition + 1:02d}"
                doc["key"] = f"{doc['id']}@v{doc['version']}"
            doc["sections"] = [section("Purpose", [text_clause(content.ADDENDUM_PURPOSE.format(
                state=bank.STATE_NAMES[state]), "text")]), section(f"{bank.STATE_NAMES[state]} requirements")]
            docs.append(doc)
    return docs


def topic_documents(rng, topic, edition, suffix):
    t = taxonomy.TOPICS[topic]
    attrs = [a for a in taxonomy.ATTRIBUTES if a["topic"] == topic]
    rules = [a for a in attrs if not a["decoy_of"]]
    decoys = [a for a in attrs if a["decoy_of"]]
    offset = edition * 20
    docs = []

    for i, title in enumerate(content.POLICIES[topic], 1):
        doc = new_doc(rng, "policy", topic, title + suffix, offset + i)
        lines_txt = taxonomy.line_phrase(doc["lines"])
        scope = content.POLICY_SCOPE_ALL if len(doc["lines"]) == 3 else content.POLICY_SCOPE_LINES.format(lines=lines_txt)
        statements = []
        for attr in rules:
            for ls, value in canonical_for(attr, doc["lines"]):
                if i > 1 and rng.random() < 0.5:
                    continue
                fam = pick_family(rng, attr, value)
                statements.append(rule_clause(attr, value, fam, pick_style(rng, attr, fam), doc,
                                              lines=ls if attr["scoped"] else None))
        rng.shuffle(statements)
        half = max(1, len(statements) // 2)
        doc["sections"] = [
            section("Purpose", [text_clause(content.POLICY_PURPOSE.format(bank=bank.BANK_NAME, topic=t["name"].lower()), "text")]),
            section("Scope", [text_clause(scope, "text")]),
            section("Policy statements", statements[:half]),
            section("Additional requirements", statements[half:]),
            section("Exceptions", [text_clause(content.POLICY_EXCEPTIONS.format(dept=t["dept"]), "text")]),
            section("Roles and responsibilities", [text_clause(content.POLICY_RESPONSIBILITIES.format(dept=t["dept"]), "text")]),
            section("Review", [text_clause(content.POLICY_REVIEW.format(dept=t["dept"]), "text")]),
        ]
        docs.append(doc)

    for i, title in enumerate(content.PROCEDURES[topic], 1):
        doc = new_doc(rng, "procedure", topic, title + suffix, offset + i)
        chosen = [a for a in rules if rng.random() < 0.45]
        if decoys and rng.random() < 0.35:
            chosen.append(rng.choice(decoys))
        steps = [text_clause(s) for s in rng.sample(content.STEPS[topic], k=min(5, len(content.STEPS[topic])))]
        steps += [text_clause(rng.choice(content.GENERIC))]
        for attr in chosen:
            for ls, value in canonical_for(attr, doc["lines"]):
                fam = pick_family(rng, attr, value)
                pos = rng.randint(0, len(steps))
                steps.insert(pos, rule_clause(attr, value, fam, pick_style(rng, attr, fam), doc,
                                              lines=ls if attr["scoped"] else None))
        doc["sections"] = [
            section("Purpose", [text_clause(content.PROCEDURE_PURPOSE.format(task=lowercase_first(title)), "text")]),
            section("Before you begin", [text_clause(content.PROCEDURE_BEFORE, "text")]),
            section("Steps", steps),
            section("Exceptions and escalation", [text_clause(rng.choice(content.GENERIC))]),
        ]
        docs.append(doc)

    for i, title in enumerate(content.JOB_AIDS[topic], 1):
        doc = new_doc(rng, "job_aid", topic, title + suffix, offset + i)
        chosen = [a for a in rules if rng.random() < 0.6]
        if len(chosen) < 2:
            chosen = rng.sample(rules, k=min(2, len(rules)))
        rows = []
        for attr in chosen:
            for ls, value in canonical_for(attr, doc["lines"]):
                rows.append(row_clause(attr, value, doc, lines=ls if attr["scoped"] else None))
        rng.shuffle(rows)
        checklist = [text_clause(s) for s in rng.sample(content.STEPS[topic], k=min(3, len(content.STEPS[topic])))]
        doc["sections"] = [section("Quick reference", rows, table=True), section("Checklist", checklist)]
        docs.append(doc)

    for i, title in enumerate(content.FAQS[topic], 1):
        doc = new_doc(rng, "faq", topic, title + suffix, offset + i)
        chosen = [a for a in rules if a["question"] and rng.random() < 0.5] or [rules[0]]
        secs = []
        for attr in chosen:
            for ls, value in canonical_for(attr, doc["lines"])[:1]:
                fam = pick_family(rng, attr, value)
                answer = rule_clause(attr, value, fam, pick_style(rng, attr, fam), doc,
                                     lines=ls if attr["scoped"] else None)
                extra = text_clause(rng.choice(content.STEPS[topic] + content.GENERIC))
                secs.append(section(attr["question"], [answer, extra]))
        doc["sections"] = secs
        docs.append(doc)

    for i in range(1, 3 if topic not in ("branch_ops", "records") else 2):
        attr = rng.choice(rules)
        year = 2025 if i == 1 else 2026
        title = f"Branch Bulletin {year}-{rng.randint(1, 40):02d}: {attr['label']}{suffix}"
        doc = new_doc(rng, "bulletin", topic, title, offset + i)
        clauses = [text_clause("This bulletin reminds branch staff of a requirement that applies to their daily work.", "text")]
        for ls, value in canonical_for(attr, doc["lines"])[:1]:
            fam = pick_family(rng, attr, value)
            clauses.append(rule_clause(attr, value, fam, pick_style(rng, attr, fam), doc,
                                       lines=ls if attr["scoped"] else None))
        clauses.append(text_clause(rng.choice(content.GENERIC)))
        doc["sections"] = [section("What branches need to know", clauses)]
        docs.append(doc)
    return docs


def assign_ids(docs):
    """Stable clause ids: <document key>/s<section>/c<clause>."""
    for doc in docs:
        for si, sec in enumerate(doc["sections"], 1):
            for ci, cl in enumerate(sec["clauses"], 1):
                cl["id"] = f"{doc['key']}/s{si}/c{ci}"
    return docs


def rule_instances(docs, include_decoys=True):
    """Every (document, clause, atom) for rule clauses, in a fixed order."""
    out = []
    for doc in docs:
        for sec in doc["sections"]:
            for cl in sec["clauses"]:
                for atom in cl["atoms"]:
                    if include_decoys or not taxonomy.BY_ID[atom["attribute"]]["decoy_of"]:
                        out.append((doc, cl, atom))
    return out
