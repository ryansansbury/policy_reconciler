"""The code-only engine: parsing, values, extraction, scope, comparison, duplicates and the frozen score."""
import json
import unittest
from pathlib import Path

from engine import compare, duplicates, extract, parse, pipeline, scope, values
from evals import freeze, score

HERE = Path(__file__).resolve().parent.parent
TMP = HERE.joinpath(".cache", "tmp", "test_engine")
DEMO = HERE.joinpath("data", "library", "2026")
PLAN = HERE.joinpath("data", "key", "2026", "plan.json")


def needs_world(test):
    return unittest.skipUnless(DEMO.exists() and PLAN.exists(), "run python3 build.py --only generate first")(test)


class TestParse(unittest.TestCase):
    @needs_world
    def test_every_format_matches_the_plan_clause_for_clause(self):
        docs, held = parse.parse_folder(DEMO)
        self.assertEqual(held, [])
        plan = json.loads(PLAN.read_text())
        want = {c["id"]: c["text"] for d in plan["documents"] for s in d["sections"] for c in s["clauses"]}
        got = {c["id"]: c["text"] for d in docs for s in d["sections"] for c in s["clauses"]}
        self.assertEqual(got, want)
        self.assertEqual({d["format"] for d in docs}, {"docx", "html", "md"})

    def test_an_unreadable_file_is_held_with_its_reason(self):
        TMP.mkdir(parents=True, exist_ok=True)
        bad = TMP.joinpath("broken.docx")
        bad.write_bytes(b"not a zip file")
        TMP.joinpath("notes.txt").write_text("plain text")
        docs, held = parse.parse_folder(TMP)
        reasons = {h["file"]: h["reason"] for h in held}
        self.assertIn("broken.docx", reasons)
        self.assertIn("format", reasons["notes.txt"])
        self.assertEqual(docs, [])

    def test_dates_in_every_format(self):
        for text in ("2025-03-01", "March 1, 2025", "Mar 1, 2025", "03/01/2025"):
            self.assertEqual(parse.iso_date(text), "2025-03-01")


class TestValues(unittest.TestCase):
    def test_money(self):
        self.assertEqual(values.find("money", "up to $1,500 a day")[0][0]["dollars"], 1500)
        self.assertEqual(values.find("money", "at least fifty dollars")[0][0]["dollars"], 50)
        self.assertEqual(values.find("money", "twenty-five dollars")[0][0]["dollars"], 25)

    def test_times(self):
        for text, minutes in (("3:00 p.m.", 900), ("4:30 PM Central", 990), ("2 PM", 840), ("9:15 a.m.", 555)):
            self.assertEqual(values.find("time", text)[0][0]["minutes"], minutes, text)

    def test_durations(self):
        v = values.find("duration", "within two business days")[0][0]
        self.assertEqual((v["n"], v["unit"]), (2, "business_days"))
        v = values.find("duration", "for 60 calendar days")[0][0]
        self.assertEqual((v["n"], v["unit"]), (60, "days"))

    def test_counts_need_something_counted(self):
        self.assertEqual(values.find("count", "Collect two forms of identification")[0][0]["n"], 2)
        self.assertEqual(values.find("count", "the most a manager can waive for one account"), [])
        self.assertEqual(values.find("count", "within 2 business days"), [])

    def test_percent(self):
        self.assertEqual(values.find("percent", "up to 0.25%")[0][0]["bp"], 25)
        self.assertEqual(values.find("percent", "25 basis points")[0][0]["bp"], 25)

    def test_modal(self):
        self.assertEqual(values.modal("Two employees must be present.")["modal"], "must")
        self.assertEqual(values.modal("A single employee may open the vault.")["modal"], "may")
        self.assertEqual(values.modal("Never destroy a record under a legal hold.")["modal"], "must_not")
        self.assertEqual(values.modal("Optional")["modal"], "may")
        self.assertIsNone(values.modal("Signal the all-clear to the second opener."))


DOC = {"key": "PRO-FEE-01@v2", "id": "PRO-FEE-01", "version": 2, "type": "procedure", "effective": "2026-01-01",
       "states": list(scope.ALL_STATES), "lines": ["consumer", "small_business"]}


def read(text, cells=None):
    cl = {"id": "x/s1/c1", "text": text}
    if cells:
        cl["cells"] = cells
    return extract.extract_clause(cl, DOC)


class TestExtract(unittest.TestCase):
    def test_a_plain_rule_is_certain(self):
        atoms, unsure = read("Branch managers may waive service fees up to $50 per account in a calendar year.")
        self.assertEqual([(a["attribute"], a["value"]["dollars"]) for a in atoms], [("fee_waiver_bm", 50)])
        self.assertEqual(unsure, [])

    def test_an_inverse_rule_goes_to_the_ai_queue(self):
        atoms, unsure = read("Fee waivers above $50 for one account in a calendar year require approval from the "
                             "regional manager.")
        self.assertEqual(atoms, [])
        self.assertIn("fee_waiver_bm", [a for a, _ in unsure])

    def test_a_condition_goes_to_the_ai_queue(self):
        atoms, unsure = read("Funds from deposited checks are available within 2 business days unless a longer hold "
                             "applies.")
        self.assertEqual(atoms, [])
        self.assertEqual(unsure[0][0], "hold_standard")

    def test_a_general_role_goes_to_the_ai_queue(self):
        atoms, unsure = read("Escalate any complaint alleging unfair treatment to management on the day it is received.")
        self.assertEqual(atoms, [])
        self.assertTrue(any("general role" in r for _, r in unsure))

    def test_a_table_row_reads_its_value_cell(self):
        atoms, _ = read("Forms of identification per signer | two", ["Forms of identification per signer", "two"])
        self.assertEqual((atoms[0]["attribute"], atoms[0]["value"]["n"], atoms[0]["value_text"]), ("ao_id_count", 2, "two"))

    def test_a_step_with_no_rule_reads_nothing(self):
        self.assertEqual(read("Thank the customer for raising the issue and listen without interrupting."), ([], []))


def atom(clause, value, doc_type="procedure", states=None, lines=None, explicit=False, effective="2026-01-01",
         doc_id=None, version=1, attribute="od_fee"):
    return {"clause": clause, "doc": f"{doc_id or clause}@v{version}", "doc_id": doc_id or clause, "version": version,
            "doc_type": doc_type, "effective": effective, "attribute": attribute, "value": {"type": "money", "dollars": value},
            "value_text": f"${value}", "states": states or list(scope.ALL_STATES),
            "lines": lines or ["consumer", "small_business"], "explicit": explicit, "scope_text": None,
            "decided_by": "code"}


def docs_for(atoms):
    return [{"id": a["doc_id"], "version": a["version"], "key": a["doc"]} for a in atoms]


class TestScopeAndCompare(unittest.TestCase):
    def test_document_scope(self):
        self.assertEqual(scope.doc_scope("All branches. All business lines."), (list(scope.ALL_STATES), list(scope.ALL_LINES)))
        self.assertEqual(scope.doc_scope("Colorado branches. Consumer and small business accounts."),
                         (["CO"], ["consumer", "small_business"]))

    def test_clause_scope_prefixes(self):
        sc = scope.clause_scope("In Colorado branches, mail the notice 45 days before.", list(scope.ALL_STATES), ["consumer"])
        self.assertEqual((sc["states"], sc["explicit"]), (["CO"], True))
        sc = scope.clause_scope("For commercial accounts, the fee is $35.", list(scope.ALL_STATES), list(scope.ALL_LINES))
        self.assertEqual((sc["lines"], sc["explicit"]), (["commercial"], True))

    def test_a_job_aid_that_disagrees_with_the_policy_is_a_conflict(self):
        atoms = [atom("POL", 30, "policy"), atom("JA", 35, "job_aid")]
        found, variations = compare.conflicts(atoms, docs_for(atoms))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["authoritative"], "POL")

    def test_an_explicit_narrower_scope_is_a_variation(self):
        atoms = [atom("POL", 30, "policy"), atom("PRO", 35, lines=["small_business"], explicit=True)]
        found, variations = compare.conflicts(atoms, docs_for(atoms))
        self.assertEqual(found, [])
        self.assertEqual(len(variations), 1)

    def test_a_state_addendum_is_a_variation(self):
        atoms = [atom("POL", 30, "policy"), atom("ADD", 45, "addendum", states=["CO"], lines=list(scope.ALL_LINES))]
        found, _ = compare.conflicts(atoms, docs_for(atoms))
        self.assertEqual(found, [])

    def test_an_older_version_is_superseded_not_a_conflict(self):
        atoms = [atom("PRO-1", 30, doc_id="PRO-1", version=2), atom("PRO-1-old", 25, doc_id="PRO-1", version=1),
                 atom("POL", 30, "policy")]
        docs = [{"id": "PRO-1", "version": 2, "key": "PRO-1@v2"}, {"id": "PRO-1", "version": 1, "key": "PRO-1@v1"},
                {"id": "POL", "version": 1, "key": "POL@v1"}]
        found, _ = compare.conflicts(atoms, docs)
        self.assertEqual(found, [])
        older = compare.superseded(atoms, docs)
        self.assertEqual([(o["doc"], len(o["changes"])) for o in older], [("PRO-1@v1", 1)])

    def test_duplicate_runs_need_three_in_a_row(self):
        w = [frozenset({"a", str(i)}) for i in range(5)]
        self.assertEqual(duplicates.runs(w, w[1:4]), [(1, 0, 3)])
        self.assertEqual(duplicates.runs(w, [w[0], w[3]]), [])


class TestFrozenEngine(unittest.TestCase):
    def test_the_engine_matches_its_freeze(self):
        frozen = HERE.joinpath("evals", "engine_freeze.json")
        if not frozen.exists():
            self.skipTest("not frozen yet")
        want = json.loads(frozen.read_text())
        self.assertEqual(freeze.engine_hash(), want["engine"],
                         "The engine changed after its freeze. Freeze a new version and score it once on fresh seeds.")

    @needs_world
    def test_the_demo_seed_scores_like_the_held_out_seeds(self):
        result = pipeline.run(DEMO)
        s = score.score(result, score.load_key(2026))
        self.assertGreaterEqual(s["summary"]["caught"], 85)
        self.assertEqual(s["summary"]["false_alarms"], 0)
        self.assertEqual(s["summary"]["unexplained"], 0)


if __name__ == "__main__":
    unittest.main()
