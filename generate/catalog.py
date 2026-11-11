"""The planted catalog: every problem placed in the clean library, and the answer key that records it.

    C  value contradictions, phrased like the clause they contradict
    P  paraphrase contradictions, phrased differently, so pairing them takes real reading
    D  duplicated steps copied from one document into another
    S  superseded versions still published beside their replacements
    V  deliberate variations with a stated narrower scope, which must never be flagged
    N  decoys that share words and value types with a rule but govern something else
    A  ambiguous items the two experts label differently
    X  conflicts implied across three documents, out of scope for this build

The catalog is frozen with a hash before any comparator, prompt or threshold exists, and every item records exactly
which clauses it touched, so scoring is a lookup.
"""
import copy
from datetime import date, timedelta

from generate import bank, library, taxonomy
from generate.values import key as vkey
from generate.values import make

COUNTS = {"C": 36, "P": 14, "D": 25, "S": 15, "V_state": 12, "V_line": 8, "N": 20, "A": 18, "X": 3}
TYPE_RANK = {"addendum": 0, "policy": 1, "procedure": 2, "job_aid": 3, "faq": 3, "bulletin": 3}

STATE_VARIABLE = ["dormant_notice", "complaint_resolve", "records_retention", "fee_refund_window", "dormant_fee",
                  "combo_change", "dispute_window", "ao_new_account_window", "od_chargeoff"]
LINE_VARIABLE = {"od_fee": "small_business", "fee_waivers_per_year": "small_business",
                 "dispute_review_threshold": "small_business", "wire_callback": "commercial",
                 "cash_review_threshold": "commercial", "complaint_ack": "commercial",
                 "records_retention": "commercial", "lend_rate_bm": "commercial"}

EXCEPTION_PATHS = {
    "fee_waiver_pb": (", or up to {v2} with branch manager approval noted in the account", make("money", 50)),
    "ao_id_count": (", or one form plus a verified bank reference when the branch manager approves", None),
    "hold_new_account": (", or up to {v2} for deposits above the large deposit threshold", make("duration", 9, "business_days")),
    "complaint_resolve": (", or within {v2} when another department has to investigate", make("duration", 30, "business_days")),
    "dispute_window": (", or longer when the customer was traveling or hospitalized", None),
    "wire_callback": (", unless the wire goes to an account the customer has used in the past year", None),
}
GENERIC_ROLES = {"ao_exception_approver": "a manager", "records_destroy_role": "a manager",
                 "complaint_escalation_role": "management", "wire_callback_role": "an operations employee"}
SYNONYMS = [("customer", "client"), ("Confirm", "Verify"), ("Make sure", "Ensure"), ("right away", "immediately"),
            ("Tell", "Let"), ("before", "prior to")]

X_TRIPLES = [
    ("wires",
     "Outgoing wires of $10,000 or more require a callback that a wire specialist completes.",
     "Branches without a wire specialist on site may release outgoing wires up to $25,000 after the teller's own review.",
     "Wire specialists work only at the regional operations center and are not assigned to branches."),
    ("cash",
     "Cash transactions of $7,500 or more go to the large-cash review queue the same day.",
     "The large-cash review queue is worked by the operations specialist assigned to the branch.",
     "Branches in rural markets share one operations specialist, who visits each branch once a week."),
    ("disputes",
     "Disputes over $500 are reviewed by a card services specialist before credit is issued.",
     "Card services specialists review disputes in the order they arrive.",
     "Provisional credit is issued within 10 business days of receiving a completed dispute, whatever its review status."),
]

FIXTURES = [("Pat Example", "LH-4471-2093-5518", "555-0142", "999-12-3456"),
            ("Jordan Sample", "LH-8810-7765-0021", "555-0177", "999-48-2210"),
            ("Casey Placeholder", "LH-3026-5591-7743", "555-0119", "999-07-9934"),
            ("Morgan Testcase", "LH-6152-0480-3367", "555-0163", "999-61-4405")]


def group_of(atom):
    """The rule group an instance belongs to: the attribute and the canonical scope it falls under."""
    attr = taxonomy.BY_ID[atom["attribute"]]
    for ls, _ in attr["canonical"]:
        if set(ls) & set(atom["lines"]):
            return (attr["id"], tuple(ls))
    return (attr["id"], tuple(attr["canonical"][0][0]))


def canonical_value(group):
    attr = taxonomy.BY_ID[group[0]]
    for ls, v in attr["canonical"]:
        if tuple(ls) == group[1]:
            return v
    return attr["canonical"][0][1]


def rerender(cl, doc, attr, value, family, style, lines=None, scope_prefix=None, states=None, scope_text=None):
    """Replace a clause's text and gold atom in place, keeping its id and plants."""
    if cl["kind"] == "row":
        new = library.row_clause(attr, value, doc, lines=lines)
        cl.update(text=new["text"], cells=new["cells"], atoms=new["atoms"])
    else:
        new = library.rule_clause(attr, value, family, style, doc, lines=lines, scope_prefix=scope_prefix,
                                  states=states, scope_text=scope_text)
        cl.update(text=new["text"], atoms=new["atoms"])


def precedence(doc_a, doc_b):
    """Which document controls: an addendum for its state, then policy, procedure, other; then the newer one."""
    ra, rb = TYPE_RANK[doc_a["type"]], TYPE_RANK[doc_b["type"]]
    if ra != rb:
        return doc_a if ra < rb else doc_b
    return doc_a if doc_a["effective"] >= doc_b["effective"] else doc_b


def plant(rng, docs, scale=1):
    counts = {k: v * scale for k, v in COUNTS.items()}
    docs_by_key = {d["key"]: d for d in docs}
    items, used_clauses, group_plants = [], set(), {}

    def instances():
        return [(d, c, a) for d, c, a in library.rule_instances(docs, include_decoys=False)]

    def groups():
        g = {}
        for d, c, a in instances():
            g.setdefault(group_of(a), []).append((d, c, a))
        return g

    def add(item):
        item["id"] = f"{item['category']}-{sum(1 for i in items if i['category'] == item['category']) + 1:02d}"
        for cid in item.get("touched", []):
            for d in docs:
                for s in d["sections"]:
                    for c in s["clauses"]:
                        if c.get("id") == cid:
                            c["plants"].append(item["id"])
        items.append(item)

    library.assign_ids(docs)

    # C and P: contradictions. At most two plants per group, never on the same clause twice.
    for category, n in (("C", counts["C"]), ("P", counts["P"])):
        made = 0
        tries = 0
        while made < n and tries < n * 40:
            tries += 1
            g = groups()
            keys = sorted(k for k, v in g.items() if len(v) >= 2 and group_plants.get(k, 0) < 2
                          and taxonomy.BY_ID[k[0]]["alts"])
            if not keys:
                break
            gk = rng.choice(keys)
            members = g[gk]
            canon = canonical_value(gk)
            consistent = [m for m in members if vkey(m[2]["value"]) == vkey(canon) and m[1]["id"] not in used_clauses]
            if len(consistent) < 2:
                continue
            ranked = sorted(consistent, key=lambda m: (TYPE_RANK[m[0]["type"]], m[1]["id"]))
            anchor = ranked[0]
            pool = [m for m in ranked[1:] if m[0]["type"] != "policy" or len(ranked) == 2]
            if category == "P":
                pool = [m for m in pool if m[1]["kind"] == "rule"]
            if not pool:
                continue
            target_doc, target_cl, target_atom = rng.choice(pool)
            attr = taxonomy.BY_ID[gk[0]]
            alts = [a for a in attr["alts"] if vkey(a) != vkey(canon)]
            if not alts:
                continue
            wrong = rng.choice(alts)
            a_fam = anchor[2]["family"]
            if attr["type"] == "modal":
                fams = list(attr["templates"][wrong["modal"]])
            else:
                fams = list(attr["templates"])
            if category == "C":
                family = a_fam if a_fam in fams else fams[0]
                style = anchor[2].get("style") or library.pick_style(rng, attr, family)
            else:
                others = [f for f in fams if f != a_fam]
                if not others:
                    continue
                preferred = [f for f in others if f in ("inverse", "words")]
                family = rng.choice(preferred or others)
                style = library.pick_style(rng, attr, family)
            lines = list(gk[1]) if attr["scoped"] else None
            rerender(target_cl, target_doc, attr, wrong, family, style, lines=lines)
            used_clauses.add(target_cl["id"])
            group_plants[gk] = group_plants.get(gk, 0) + 1
            same = [m[1]["id"] for m in members if m[1]["id"] != target_cl["id"]
                    and vkey(m[2]["value"]) == vkey(canon)]
            ctrl = precedence(anchor[0], target_doc)
            add({"category": category, "label": "conflict", "attribute": attr["id"], "group": list(gk[1]),
                 "target": target_cl["id"], "anchor": anchor[1]["id"], "conflicts_with": same,
                 "values": {"target": wrong, "canonical": canon}, "touched": [target_cl["id"]],
                 "authoritative": anchor[1]["id"] if ctrl is anchor[0] else target_cl["id"],
                 "resolution": f"Keep the value in {anchor[0]['id']} and update {target_doc['id']}."})
            made += 1

    # V: deliberate variations. State addenda first, then narrower business lines.
    addenda = {d["states"][0]: d for d in docs if d["type"] == "addendum"}
    g = groups()
    state_attrs = [a for a in STATE_VARIABLE if any(k[0] == a for k in g)]
    for i in range(counts["V_state"]):
        attr = taxonomy.BY_ID[state_attrs[i % len(state_attrs)]]
        state = bank.STATES[i % len(bank.STATES)]
        add_doc = addenda[state] if scale == 1 else rng.choice([d for d in docs if d["type"] == "addendum" and d["states"] == [state]])
        gk = next(k for k in sorted(g) if k[0] == attr["id"])
        canon = canonical_value(gk)
        alt = rng.choice([a for a in attr["alts"] if vkey(a) != vkey(canon)])
        fam = library.pick_family(rng, attr, alt)
        prefix = f"In {bank.STATE_NAMES[state]} branches,"
        cl = library.rule_clause(attr, alt, fam, library.pick_style(rng, attr, fam), add_doc, lines=list(gk[1]),
                                 scope_prefix=prefix, states=[state], scope_text=prefix.rstrip(","))
        add_doc["sections"][-1]["clauses"].append(cl)
        library.assign_ids([add_doc])
        general = sorted(g[gk], key=lambda m: (TYPE_RANK[m[0]["type"]], m[1]["id"]))[0]
        add({"category": "V", "label": "variation", "attribute": attr["id"], "origin": "state",
             "target": cl["id"], "anchor": general[1]["id"], "values": {"target": alt, "canonical": canon},
             "touched": [cl["id"]], "scope": {"states": [state]},
             "resolution": f"No change. The {bank.STATE_NAMES[state]} addendum sets its own value on purpose."})
    for i, (attr_id, line) in enumerate(sorted(LINE_VARIABLE.items())):
        if i >= counts["V_line"] and scale == 1:
            break
        attr = taxonomy.BY_ID[attr_id]
        hosts = [d for d in docs if d["type"] in ("policy", "procedure") and d["topic"] == attr["topic"]
                 and line in d["lines"] and d["status"] == "current"]
        if not hosts:
            continue
        host = rng.choice(hosts)
        gk = next(k for k in sorted(g) if k[0] == attr["id"])
        if any(m[2]["lines"] == [line] for m in g[gk]):
            continue  # a document scoped to just this line already states the rule, so a variation would conflict
        canon = canonical_value(gk)
        alt = rng.choice([a for a in attr["alts"] if vkey(a) != vkey(canon)])
        fam = library.pick_family(rng, attr, alt)
        prefix = f"For {taxonomy.line_phrase([line])} accounts,"
        cl = library.rule_clause(attr, alt, fam, library.pick_style(rng, attr, fam), host, lines=[line],
                                 scope_prefix=prefix, scope_text=prefix.rstrip(","))
        sec = next(s for s in host["sections"] if any(c["kind"] == "rule" for c in s["clauses"])) \
            if any(c["kind"] == "rule" for s in host["sections"] for c in s["clauses"]) else host["sections"][-1]
        sec["clauses"].append(cl)
        library.assign_ids([host])
        general = sorted(g[gk], key=lambda m: (TYPE_RANK[m[0]["type"]], m[1]["id"]))[0]
        add({"category": "V", "label": "variation", "attribute": attr["id"], "origin": "line",
             "target": cl["id"], "anchor": general[1]["id"], "values": {"target": alt, "canonical": canon},
             "touched": [cl["id"]], "scope": {"lines": [line]},
             "resolution": f"No change. {taxonomy.line_phrase([line]).capitalize()} accounts have their own value on purpose."})
    # The canonical scoped rules differ by line by design, so their pairs are variations too.
    g = groups()
    for attr in taxonomy.RULES:
        if not attr["scoped"]:
            continue
        heads = []
        for ls, _ in attr["canonical"]:
            members = sorted(g.get((attr["id"], tuple(ls)), []), key=lambda m: (TYPE_RANK[m[0]["type"]], m[1]["id"]))
            if members:
                heads.append(members[0])
        for a_i in range(len(heads) - 1):
            add({"category": "V", "label": "variation", "attribute": attr["id"], "origin": "canonical",
                 "target": heads[a_i + 1][1]["id"], "anchor": heads[a_i][1]["id"],
                 "values": {"target": heads[a_i + 1][2]["value"], "canonical": heads[a_i][2]["value"]},
                 "touched": [], "scope": {"lines": heads[a_i + 1][2]["lines"]},
                 "resolution": "No change. Each business line has its own cutoff."})

    # A: ambiguous items for the experts.
    a_made = 0
    g = groups()
    kinds = ["exception_path", "unit", "role_generic"]
    tries = 0
    while a_made < counts["A"] and tries < 400:
        tries += 1
        kind = kinds[a_made % 3]
        if kind == "exception_path":
            options = [k for k in sorted(g) if k[0] in EXCEPTION_PATHS]
        elif kind == "unit":
            options = [k for k in sorted(g) if taxonomy.BY_ID[k[0]]["type"] == "duration"
                       and canonical_value(k).get("unit") == "business_days"]
        else:
            options = [k for k in sorted(g) if k[0] in GENERIC_ROLES]
        if not options:
            kinds.remove(kind)
            continue
        gk = rng.choice(options)
        canon = canonical_value(gk)
        free = [m for m in g[gk] if m[1]["id"] not in used_clauses and m[1]["kind"] == "rule"
                and vkey(m[2]["value"]) == vkey(canon)]
        if len(free) < 2:
            continue
        free.sort(key=lambda m: (TYPE_RANK[m[0]["type"]], m[1]["id"]))
        first, second = free[0], rng.choice(free[1:])
        attr = taxonomy.BY_ID[gk[0]]
        if kind == "exception_path":
            tail, v2 = EXCEPTION_PATHS[attr["id"]]
            from generate.values import render
            extra = tail.format(v2=render(v2)) if v2 else tail
            text = first[1]["text"]
            first[1]["text"] = text[:-1] + extra + "."
            first[1]["atoms"][0]["exception"] = extra.strip(", ")
            target, other = first[1], second[1]
            note = "One clause adds an exception path the other leaves out."
        elif kind == "unit":
            wrong_unit = make("duration", canon["n"], "days")
            target_doc, target_cl = second[0], second[1]
            fam = target_cl["atoms"][0]["family"]
            rerender(target_cl, target_doc, attr, wrong_unit, fam, target_cl["atoms"][0].get("style"))
            target, other = target_cl, first[1]
            note = "One clause counts business days and the other counts days."
        else:
            target_doc, target_cl = second[0], second[1]
            generic = GENERIC_ROLES[attr["id"]]
            role_name = bank.ROLES[canon["role"]]
            text = target_cl["text"]
            for form in (f"the {role_name}", f"a {role_name}", f"The {role_name}", f"A {role_name}"):
                if form in text:
                    repl = generic[0].upper() + generic[1:] if form[0].isupper() else generic
                    target_cl["text"] = text.replace(form, repl, 1)
                    break
            else:
                continue
            target_cl["atoms"][0]["value"] = {"type": "role", "role": None, "generic": generic}
            target_cl["atoms"][0]["value_text"] = generic
            target, other = target_cl, first[1]
            note = "One clause names a specific role and the other a general one."
        used_clauses.update({target["id"], other["id"]})
        add({"category": "A", "label": "disputed", "kind": kind, "attribute": attr["id"], "target": target["id"],
             "anchor": other["id"], "touched": [target["id"]], "note": note})
        a_made += 1

    # D: duplicated steps copied into another document of the same topic.
    procs = [d for d in docs if d["type"] == "procedure" and d["status"] == "current"]
    d_made = d_tries = 0
    while d_made < counts["D"] and d_tries < counts["D"] * 20:
        d_tries += 1
        src = rng.choice(procs)
        steps = next(s for s in src["sections"] if s["heading"] == "Steps")
        if len(steps["clauses"]) < 5:
            continue
        size = rng.randint(3, 4)
        start = rng.randint(0, len(steps["clauses"]) - size)
        block = steps["clauses"][start:start + size]
        if any(c["plants"] or c.get("id") in used_clauses for c in block):
            continue
        hosts = [d for d in docs if d["topic"] == src["topic"] and d["key"] != src["key"]
                 and d["type"] in ("job_aid", "bulletin", "procedure") and d["status"] == "current"]
        host = rng.choice(hosts)
        exact = rng.random() < 0.6
        copies = []
        for cl in block:
            new = copy.deepcopy(cl)
            new["plants"] = []
            if not exact:
                for a, b in SYNONYMS:
                    if a in new["text"]:
                        new["text"] = new["text"].replace(a, b, 1)
                        break
            copies.append(new)
        host["sections"].append(library.section("Steps to follow", copies))
        library.assign_ids([host])
        add({"category": "D", "label": "duplicate", "source": [c["id"] for c in block],
             "copy": [c["id"] for c in copies], "exact": exact, "touched": [c["id"] for c in copies],
             "resolution": f"Keep the steps in {src['id']} and link to them from {host['id']}."})
        d_made += 1

    # S: an older version of a document left published beside the current one.
    candidates = [d for d in docs if d["type"] in ("procedure", "job_aid", "bulletin") and d["version"] >= 2
                  and d["status"] == "current" and any(c["kind"] in ("rule", "row") and c["id"] not in used_clauses
                                                       for s in d["sections"] for c in s["clauses"])]
    rng.shuffle(candidates)
    for cur in candidates[:counts["S"]]:
        old = copy.deepcopy(cur)
        old["version"] = cur["version"] - 1
        old["key"] = f"{old['id']}@v{old['version']}"
        old["effective"] = (date.fromisoformat(cur["effective"]) - timedelta(days=rng.randint(180, 540))).isoformat()
        old["status"] = "older_version"
        for s in old["sections"]:
            for c in s["clauses"]:
                c["plants"] = []
        library.assign_ids([old])
        rules_old = [c for s in old["sections"] for c in s["clauses"] if c["kind"] in ("rule", "row")
                     and taxonomy.BY_ID[c["atoms"][0]["attribute"]]["alts"]
                     and not taxonomy.BY_ID[c["atoms"][0]["attribute"]]["decoy_of"]]
        if not rules_old:
            continue
        cl = rng.choice(rules_old)
        atom = cl["atoms"][0]
        attr = taxonomy.BY_ID[atom["attribute"]]
        alts = [a for a in attr["alts"] if vkey(a) != vkey(atom["value"])]
        if not alts:
            continue
        old_value = rng.choice(alts)
        rerender(cl, old, attr, old_value, atom["family"] if atom["family"] != "row" else "a", atom.get("style"),
                 lines=atom["lines"] if attr["scoped"] else None)
        cur_cl = cl["id"].replace(old["key"], cur["key"])
        docs.append(old)
        add({"category": "S", "label": "superseded", "attribute": attr["id"], "old_doc": old["key"],
             "current_doc": cur["key"], "target": cl["id"], "anchor": cur_cl,
             "values": {"target": old_value, "canonical": atom["value"]}, "touched": [cl["id"]],
             "resolution": f"Archive version {old['version']} of {old['id']}, since version {cur['version']} replaces it."})

    # N: decoys placed beside the rule they resemble.
    for i in range(counts["N"]):
        decoy = taxonomy.DECOYS[i % len(taxonomy.DECOYS)]
        target_attr = decoy["decoy_of"]
        homes = [(d, s, c) for d in docs if d["status"] == "current" for s in d["sections"] for c in s["clauses"]
                 if c["atoms"] and c["atoms"][0]["attribute"] == target_attr and c["kind"] == "rule"]
        if not homes:
            continue
        d, s, near = rng.choice(homes)
        value = decoy["canonical"][0][1]
        fam = library.pick_family(rng, decoy, value)
        cl = library.rule_clause(decoy, value, fam, library.pick_style(rng, decoy, fam), d)
        s["clauses"].append(cl)
        library.assign_ids([d])
        add({"category": "N", "label": "unrelated", "attribute": decoy["id"], "decoy_of": target_attr,
             "target": cl["id"], "anchor": near["id"], "touched": [cl["id"]],
             "resolution": "No change. These clauses govern different things."})

    # X: implicit conflicts across three documents, recorded but out of scope.
    out_of_scope = []
    for topic, *texts in X_TRIPLES[:counts["X"] // scale if scale > 1 else counts["X"]]:
        hosts = rng.sample([d for d in docs if d["topic"] == topic and d["status"] == "current"], k=3)
        ids = []
        for host, text in zip(hosts, texts):
            host["sections"].append(library.section("Related requirements", [library.text_clause(text, "text")]))
            library.assign_ids([host])
            ids.append(host["sections"][-1]["clauses"][0]["id"])
        out_of_scope.append({"category": "X", "topic": topic, "clauses": ids,
                             "note": "Read together, these three clauses leave no one able to meet the first rule."})

    # Masking fixtures: example customer details in a few job aids.
    masking = []
    aids = [d for d in docs if d["type"] == "job_aid" and d["status"] == "current"]
    for name, acct, phone, ident in FIXTURES:
        host = rng.choice(aids)
        text = f"Example for training only: {name}, account {acct}, phone {phone}, ID number {ident}."
        host["sections"].append(library.section("Worked example", [library.text_clause(text, "text")]))
        library.assign_ids([host])
        masking.append({"clause": host["sections"][-1]["clauses"][0]["id"], "strings": [name, acct, phone, ident]})

    library.assign_ids(docs)
    return {"items": items, "out_of_scope": out_of_scope, "masking": masking,
            "counts": {c: sum(1 for i in items if i["category"] == c) for c in ("C", "P", "D", "S", "V", "N", "A")}}
