"""The specialist's decisions: the disagreement groups match the experts', each decision settles its group by rule, the key
version moves, the agreement rises, and whatever evals/decisions.json holds is well formed."""
import json
import unittest
from pathlib import Path

from agents import combine, decisions, validate
from engine import pipeline
from evals import agreement, score

HERE = Path(__file__).resolve().parent.parent
KEY = HERE.joinpath("data", "key", "2026")


def needs_world(test):
    return unittest.skipUnless(KEY.exists(), "run python3 build.py first")(test)


def deciding(**labels):
    return {"key_version": 2, "decisions": {k: {"label": v, "reason": f"A test decision for {k}."}
                                            for k, v in labels.items()}}


class TestKappa(unittest.TestCase):
    def test_full_agreement_and_chance(self):
        a = {"1": "x", "2": "y", "3": "x", "4": "y"}
        self.assertEqual(agreement.kappa(a, dict(a)), 1.0)
        self.assertEqual(agreement.kappa(a, {"1": "y", "2": "x", "3": "y", "4": "x"}), -1.0)
        self.assertIsNone(agreement.kappa(a, {}))


@needs_world
class TestGroups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = json.loads(KEY.joinpath("key.json").read_text())
        cls.evals = json.loads(KEY.joinpath("evals.json").read_text())
        cls.experts = json.loads(KEY.joinpath("experts.json").read_text())["pairs"]
        cls.kinds = decisions.kinds(cls.evals["pairs"], cls.key)
        cls.result = pipeline.run(HERE.joinpath("data", "library", "2026"))

    def test_the_groups_are_exactly_where_the_experts_disagree(self):
        a, b = self.experts.values()
        disagree = {pid for pid in a if a[pid]["label"] != b[pid]["label"]}
        self.assertEqual(set(self.kinds), disagree)
        self.assertEqual(set(self.kinds.values()), set(decisions.KINDS))

    def test_deciding_every_group_brings_the_experts_to_full_agreement(self):
        a, b = ({pid: v["label"] for pid, v in e.items()} for e in self.experts.values())
        before = agreement.kappa(a, b)
        all_four = deciding(exception_path="conflict", unit="conflict", role_generic="consistent",
                            older_version="superseded")
        after = agreement.kappa(decisions.apply(a, self.kinds, all_four), decisions.apply(b, self.kinds, all_four))
        self.assertLess(before, 1.0)
        self.assertEqual(after, 1.0)

    def test_a_unit_decision_settles_its_pairs_by_rule(self):
        units = {it["target"] for it in self.key["items"] if it.get("kind") == "unit"}
        flagged = combine.review(self.result, decisions=deciding(unit="conflict"))
        ruled = [f for f in flagged["findings"] if f.get("decided_by") == "rule"]
        self.assertTrue(ruled)
        self.assertTrue(all(f["kind"] == "unit" for f in ruled))
        self.assertTrue({c for f in ruled for c in f["clauses"]} & units)
        quiet = combine.review(self.result, decisions=deciding(unit="consistent"))
        self.assertFalse(any(f.get("decided_by") == "rule" for f in quiet["findings"]))
        self.assertTrue(quiet["ruled"])
        self.assertFalse(any(p["kind"] == "unit" for p in quiet["pairs"]))

    def test_a_decided_item_is_scored_against_the_ruling(self):
        dec = deciding(unit="conflict")
        out = combine.review(self.result, decisions=dec)
        rows = [d for d in score.score(out, self.key, dec)["disputed"] if d["kind"] == "unit"]
        self.assertTrue(all(d["ruled"] == "conflict" for d in rows))
        ruled = {c for f in out["findings"] if f.get("decided_by") == "rule" for c in f["clauses"]}
        targets = {it["id"]: it["target"] for it in self.key["items"] if it.get("kind") == "unit"}
        self.assertTrue(all(d["matches"] for d in rows if targets[d["item"]] in ruled))
        summary = score.score(out, self.key, dec)["summary"]
        self.assertEqual((summary["decided_of"], summary["key_version"]), (len(rows), 2))

    def test_an_older_version_decided_live_ranks_as_a_conflict(self):
        out = combine.review(self.result, decisions=deciding(older_version="conflict"))
        older = [f for f in out["findings"] if f["type"] == "superseded"]
        self.assertTrue(older and all(f["live"] for f in older))
        out = combine.review(self.result, decisions=deciding(older_version="superseded"))
        self.assertFalse(any(f["live"] for f in out["findings"] if f["type"] == "superseded"))

    def test_the_scorer_reports_a_decided_unit_item(self):
        """Code alone can't read every policy statement, so only the unit items whose pair reached the rule are
        settled by it. The rest wait on the rule extractor."""
        out = combine.review(self.result, decisions=deciding(unit="consistent"))
        ruled = {c for p in out["ruled"] for c in (p["a"]["clause"], p["b"]["clause"])}
        said = {d["item"]: d["said"] for d in score.score(out, self.key)["disputed"] if d["kind"] == "unit"}
        targets = {it["id"]: it["target"] for it in self.key["items"] if it.get("kind") == "unit"}
        settled = [i for i, t in targets.items() if t in ruled]
        self.assertTrue(settled)
        self.assertTrue(all(said[i] == "the decision says consistent" for i in settled), said)


class TestRecord(unittest.TestCase):
    def test_the_decisions_file_is_well_formed(self):
        record = decisions.load()
        allowed = {"conflict", "consistent", "superseded"}
        for kind, d in record["decisions"].items():
            self.assertIn(kind, decisions.KINDS)
            self.assertIn(d["label"], allowed)
            self.assertTrue(d["reason"].strip())
            self.assertEqual(validate.writing_problems(d["reason"]), [])
        self.assertGreaterEqual(record.get("key_version", 1), 1 + bool(record["decisions"]))


if __name__ == "__main__":
    unittest.main()
