"""Incremental runs: a change rereads only its own section, compares only the rules that section states, and finds
the same contradictions a full run would."""
import unittest
from pathlib import Path

from agents import items
from app import change
from engine import compare, incremental

HERE = Path(__file__).resolve().parent.parent


@unittest.skipUnless(HERE.joinpath("data", "library", "2026").exists(), "run python3 build.py first")
class TestIncremental(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = items.library(2026)

    def test_nothing_changed_means_nothing_reruns(self):
        r = incremental.rerun(self.result, self.result["documents"])
        self.assertEqual((r["changed_sections"], r["clauses_reread"], r["created"], r["cleared"]), ([], 0, [], []))

    def test_a_change_reruns_only_its_section_and_its_rule(self):
        s = change.scenario(self.result)
        self.assertEqual(len(s["changed_sections"]), 1)
        self.assertEqual(s["rules_recompared"], [change.pick(self.result)["attribute"]])
        self.assertTrue(s["created"])
        self.assertLess(s["seconds"], s["full_seconds"])

    def test_the_incremental_result_matches_a_full_comparison(self):
        a = change.pick(self.result)
        docs = incremental.change_clause(self.result["documents"], a["clause"], a["value_text"], "$1")
        r = incremental.rerun(self.result, docs)
        atoms = [x for x in self.result["atoms"] if x["clause"] != a["clause"]]
        atoms.append(dict(a, value={"type": "money", "dollars": 1}, value_text="$1"))
        full, _ = compare.conflicts([x for x in atoms if x["attribute"] == a["attribute"]], docs)
        before = {tuple(f["clauses"]) for f in self.result["findings"]
                  if f["type"] == "conflict" and f["attribute"] == a["attribute"]}
        self.assertEqual(set(r["created"]), {tuple(f["clauses"]) for f in full} - before)


if __name__ == "__main__":
    unittest.main()
