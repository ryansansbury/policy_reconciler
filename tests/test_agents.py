"""The AI steps, offline: masking, validation, the recorder driven by a stand-in model, replay, the audit, the freeze
guard and the combined review. No test calls a model or the network."""
import json
import shutil
import unittest
from pathlib import Path

from agents import combine, flow, inputs, mask, prompts, replay, standin, steps, validate
from engine import extract, lexicon, pipeline, scope, values
from evals import score, score_ai

HERE = Path(__file__).resolve().parent.parent
TMP = HERE.joinpath(".cache", "tmp", "test_agents")
LIBRARY = HERE.joinpath("data", "library")
DEMO = LIBRARY.joinpath("2026")
KEY = HERE.joinpath("data", "key", "2026")

FEE = "Fee waivers above $50 for one account in a calendar year require approval from the regional manager."
ITEM = {"clause": "JA-FEE-09@v1/s1/c1", "text": FEE, "heading": "Limits", "document": {"title": "t", "type": "job_aid",
                                                                                     "applies_to": "All branches."}}
GOOD = {"attribute": "fee_waiver_bm", "value": {"type": "money", "dollars": 50}, "quote": "$50",
        "actor": "branch_manager", "actor_inferred": True, "scope_quote": None, "condition": None}


def quiet(line):
    pass


def needs_world(test):
    return unittest.skipUnless(DEMO.exists() and KEY.exists(), "run python3 build.py --only generate first")(test)


def reply(atoms, clause=ITEM["clause"]):
    return json.dumps({"results": [{"clause": clause, "atoms": atoms}]})


def gold_atoms():
    """{clause: gold atoms in the extractor's shape}, for the oracle stand-in. Only tests read the gold."""
    plan = json.loads(KEY.joinpath("plan.json").read_text())
    out = {}
    for d in plan["documents"]:
        for s in d["sections"]:
            for c in s["clauses"]:
                out[c["id"]] = [{"attribute": a["attribute"], "value": a["value"], "quote": a["value_text"],
                                 "actor": a["actor"], "actor_inferred": a["actor_inferred"],
                                 "scope_quote": a["scope_text"] if a["scope_text"] and a["scope_text"] in c["text"] else None,
                                 "condition": a.get("exception")} for a in c["atoms"]]
    return out


def tiny_result():
    """A policy that sets the branch manager's $50 limit, and a job aid clause code queued."""
    docs = []
    for key, kind, text in (("POL-FEE-01", "policy", "Branch managers may waive service fees up to $50 per account "
                                                     "in a calendar year."),
                            ("JA-FEE-01", "job_aid", FEE.replace("$50", "$75"))):
        docs.append({"key": f"{key}@v1", "id": key, "version": 1, "type": kind, "effective": "2026-01-01",
                     "title": key, "applies_to": "All branches. Consumer and small business accounts.",
                     "states": list(scope.ALL_STATES), "lines": ["consumer", "small_business"],
                     "sections": [{"heading": "Limits", "clauses": [{"id": f"{key}@v1/s1/c1", "text": text}]}]})
    code_atoms, _ = extract.extract_clause(docs[0]["sections"][0]["clauses"][0], docs[0])
    return {"documents": docs, "atoms": code_atoms, "findings": [],
            "queue": [{"clause": "JA-FEE-01@v1/s1/c1", "doc": "JA-FEE-01@v1", "text": docs[1]["sections"][0]["clauses"][0]["text"],
                       "reasons": ["fee_waiver_bm: stated through its exception"]}]}


def oracle_labels():
    """{pair id: label} from the planted catalog, for the oracle stand-in."""
    key = json.loads(KEY.joinpath("key.json").read_text())
    out = {}
    for it in key["items"]:
        if it["category"] in ("C", "P"):
            for other in set(it["conflicts_with"]) | {it["anchor"]}:
                out[inputs.pair_id(other, it["target"])] = "conflict"
        elif it["category"] == "V":
            out[inputs.pair_id(it["anchor"], it["target"])] = "variation"
    return out


class TestMask(unittest.TestCase):
    @needs_world
    def test_every_customer_detail_in_the_fixtures_is_masked(self):
        key = json.loads(KEY.joinpath("key.json").read_text())
        items = inputs.extract_items(demo_result(), [f["clause"] for f in key["masking"]])
        masked, counts = mask.mask_payload(items)
        text = json.dumps(masked)
        for f in key["masking"]:
            for s in f["strings"]:
                self.assertNotIn(s, text)
        self.assertEqual(set(counts), {"ACCOUNT", "ID", "PHONE", "NAME"})

    @needs_world
    def test_ids_and_dates_survive_masking(self):
        for d in demo_result()["documents"]:
            self.assertEqual(mask.mask(d["effective"])[0], d["effective"])
            for s in d["sections"]:
                for c in s["clauses"]:
                    self.assertEqual(mask.mask(c["id"])[0], c["id"])


class TestValidate(unittest.TestCase):
    def test_a_good_atom_passes(self):
        ok, problems = validate.check_extract([ITEM], reply([GOOD]))
        self.assertEqual(problems, [])
        self.assertEqual(ok[ITEM["clause"]][0]["attribute"], "fee_waiver_bm")

    def test_a_quote_with_curly_punctuation_still_matches(self):
        item = dict(ITEM, text="The branch manager\u2019s limit is $50 per account.")
        atom = dict(GOOD, quote="manager\u2019s limit is $50")
        self.assertEqual(validate.check_extract([item], reply([dict(atom, quote="manager's limit is $50")]))[1], [])
        self.assertEqual(validate.check_extract([item], reply([atom]))[1], [])

    def test_a_fenced_reply_passes(self):
        ok, problems = validate.check_extract([ITEM], "```json\n" + reply([GOOD]) + "\n```")
        self.assertEqual(problems, [])

    def test_bad_atoms_fail_with_reasons(self):
        cases = [(dict(GOOD, quote="$75"), "isn't in the clause"),
                 (dict(GOOD, value={"type": "money", "dollars": 75}), "doesn't hold the value"),
                 (dict(GOOD, attribute="no_such_rule"), "isn't a tracked attribute"),
                 (dict(GOOD, value={"type": "duration", "n": 50, "unit": "days"}), "must be a money value"),
                 (dict(GOOD, actor="the_ceo"), "role list"),
                 (dict(GOOD, condition="unless it rains"), "condition isn't in the clause")]
        for atom, why in cases:
            ok, problems = validate.check_extract([ITEM], reply([atom]))
            self.assertEqual(ok, {}, why)
            self.assertTrue(any(why in p for p in problems), (why, problems))

    def test_a_missing_result_and_bad_json_fail(self):
        self.assertIn("no result", validate.check_extract([ITEM], json.dumps({"results": []}))[1][0])
        self.assertIn("valid JSON", validate.check_extract([ITEM], "not json")[1][0])

    def test_labels_quotes_and_rationales(self):
        pair = {"pair": "pair-x", "a": {"text": "Waive up to $50."}, "b": {"text": "Waive up to $75."}}

        def check(**kw):
            r = dict({"pair": "pair-x", "label": "conflict", "quote_a": "$50", "quote_b": "$75",
                      "rationale": "The limits differ for the same staff."}, **kw)
            return validate.check_classify([pair], json.dumps({"results": [r]}))

        self.assertEqual(check()[1], [])
        for kw, why in (({"label": "maybe"}, "label must be"), ({"quote_a": "$60"}, "quote_a"),
                        ({"rationale": "The policy allows $100."}, "numbers that aren't"),
                        ({"rationale": "One is newer; it wins."}, "colon or semicolon"),
                        ({"rationale": "One limit is higher - staff are confused."}, "a dash")):
            ok, problems = check(**kw)
            self.assertEqual(ok, {}, why)
            self.assertTrue(any(why in p for p in problems), (why, problems))

    def test_a_clock_time_and_the_documents_numbers_are_allowed(self):
        pair = {"pair": "pair-t", "a": {"text": "Wires sent after 3:00 PM go out the next day.", "document": {"version": 4}},
                "b": {"text": "Wires sent after 2:30 PM go out the next day.", "document": {"version": 2}}}
        r = {"pair": "pair-t", "label": "conflict", "quote_a": "3:00 PM", "quote_b": "2:30 PM",
             "rationale": "Version 4 sets 3:00 PM and version 2 sets 2:30 PM for the same cutoff."}
        self.assertEqual(validate.check_classify([pair], json.dumps({"results": [r]}))[1], [])

    def test_a_comma_before_so_is_fixed_for_display_and_never_holds_an_answer(self):
        pair = {"pair": "pair-x", "a": {"text": "Waive up to $50."}, "b": {"text": "Waive up to $75."}}
        r = {"pair": "pair-x", "label": "conflict", "quote_a": "$50", "quote_b": "$75",
             "rationale": "The limits differ, so staff get two answers."}
        self.assertEqual(validate.check_classify([pair], json.dumps({"results": [r]}))[1], [])
        self.assertEqual(validate.plain(r["rationale"]), "The limits differ. So staff get two answers.")
        self.assertIn("a comma before so", validate.writing_problems(r["rationale"])[0])

    def test_canonical_values_drop_extra_fields(self):
        self.assertEqual(validate.canonical({"type": "money", "dollars": 50, "currency": "USD"}),
                         {"type": "money", "dollars": 50})
        self.assertEqual(validate.canonical({"type": "role", "role": None, "generic": "a manager"}),
                         {"type": "role", "role": None, "generic": "a manager"})


class TestPrompts(unittest.TestCase):
    def test_the_prompt_carries_every_attribute_and_role(self):
        text = prompts.system("extract")
        for attr in lexicon.L:
            self.assertIn(f"- {attr}: ", text)
        for rid in values.ROLES.values():
            self.assertIn(f"- {rid}: ", text)

    def test_the_hash_is_stable(self):
        self.assertEqual(prompts.prompt_hash("classify"), prompts.prompt_hash("classify"))
        self.assertNotEqual(prompts.prompt_hash("extract"), prompts.prompt_hash("classify"))


class TestPromptFreeze(unittest.TestCase):
    def test_the_frozen_prompts_match_their_freeze(self):
        frozen = HERE.joinpath("evals", "prompt_freeze.json")
        if not frozen.exists():
            self.skipTest("no prompt is frozen yet")
        want = json.loads(frozen.read_text())
        for step in want["prompts"]:
            self.assertEqual(prompts.prompt_hash(step), want["prompts"][step],
                             f"The {step} prompt changed after its freeze. Freeze a new version for fresh seeds.")


class TestFreezeGuard(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)


    def test_a_held_out_seed_is_scored_once(self):
        r = {"models": ["m"], "seeds": {"6101": {}, "11": {}}, "extraction": {"evals-6101": {}}, "pairs": {}}
        path = TMP.joinpath("scored.json")
        kept = score_ai.record_scored(r, path, {"engine": 2, "prompts": 1, "catalog": 2})
        self.assertEqual(kept["held_out"], ["6101", "evals-6101"])
        with self.assertRaises(SystemExit):
            score_ai.record_scored(r, path, {"engine": 3, "prompts": 1, "catalog": 2})
        later = dict(r, seeds={"6101": {}, "8101": {}})
        self.assertEqual(score_ai.record_scored(later, path, {"engine": 3, "prompts": 1, "catalog": 2})["held_out"], ["8101"])


def demo_result():
    """The demo library's code review, parsed once for the whole module. Nothing here changes it."""
    if not hasattr(demo_result, "cached"):
        demo_result.cached = pipeline.run(DEMO)
    return demo_result.cached


@needs_world
class TestCombined(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        self.runs = TMP.joinpath("runs")
        self.result = demo_result()
        self.key = score.load_key(2026)

    def test_with_no_recordings_the_review_is_code_alone(self):
        out = flow.run(self.result, "2026", self.runs)
        self.assertEqual(score.score(out, self.key)["summary"]["caught"],
                         score.score(self.result, self.key)["summary"]["caught"])
        self.assertEqual(out["ai"]["extract"]["missing"], len(self.result["queue"]))

    def test_an_ai_conflict_becomes_a_finding_and_other_labels_explain(self):
        result = tiny_result()
        ja = "JA-FEE-01@v1/s1/c1"
        atom = dict(GOOD, value={"type": "money", "dollars": 75}, quote="$75")
        first = combine.review(result, {ja: [atom]})
        self.assertEqual(len(first["pairs"]), 1)
        self.assertIn("inferred", first["pairs"][0]["reason"])
        self.assertEqual([f for f in first["findings"] if f["type"] == "conflict"], [])
        lab = {"label": "conflict", "quote_a": "$50", "quote_b": "$75", "rationale": "The limits differ."}
        out = combine.review(result, {ja: [atom]}, {first["pairs"][0]["pair"]: lab})
        self.assertEqual([f["decided_by"] for f in out["findings"] if f["type"] == "conflict"], ["ai"])
        out = combine.review(result, {ja: [atom]}, {first["pairs"][0]["pair"]: dict(lab, label="variation")})
        self.assertEqual([f for f in out["findings"] if f["type"] == "conflict"], [])
        self.assertEqual(out["decided"][0]["label"], "variation")

    def test_code_wins_where_it_already_read_the_rule(self):
        a = self.result["atoms"][0]
        atom = {"attribute": a["attribute"], "value": a["value"], "quote": a["value_text"], "actor": None,
                "actor_inferred": False, "scope_quote": None, "condition": None}
        out = combine.review(self.result, {a["clause"]: [atom]})
        self.assertEqual(len(out["atoms"]), len(self.result["atoms"]))

    def test_the_scorers_count_right_and_wrong(self):
        sets = json.loads(KEY.joinpath("evals.json").read_text())
        gold = sets["extraction"]
        perfect = {"accepted": {g["clause"]: [{"attribute": a["attribute"], "value": a["value"]} for a in g["gold"]]
                                for g in gold}, "held": {}, "used": []}
        s = score_ai.score_extract(gold, perfect)
        self.assertEqual((s["exact_share"], s["atoms"]["precision"], s["atoms"]["recall"]), (1.0, 1.0, 1.0))
        empty = {"accepted": {g["clause"]: [] for g in gold}, "held": {}, "used": []}
        s = score_ai.score_extract(gold, empty)
        self.assertEqual(s["outcomes"]["missed"], sum(1 for g in gold if g["gold"]))
        pairs = sets["pairs"]
        same = {"accepted": {inputs.pair_id(p["a"], p["b"]): {"label": "consistent", "rationale": ""} for p in pairs},
                "held": {}, "used": []}
        c = score_ai.score_classify(pairs, same)
        scored = [p for p in pairs if p["label"] != "disputed"]
        self.assertAlmostEqual(c["accuracy"], round(sum(p["label"] == "consistent" for p in scored) / len(scored), 3))
        self.assertEqual(len(c["disputed"]), sum(p["label"] == "disputed" for p in pairs))


if __name__ == "__main__":
    unittest.main()
