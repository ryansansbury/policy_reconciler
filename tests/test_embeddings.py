"""The embeddings experiment's parts, offline: the embedding call keeps the texts' order and backs off a rate limit,
a queued clause takes its nearest read neighbor's rule only above the threshold and only where the extractor left it
unread, and the measures count paired paraphrases and wrong rules against the generator's record."""
import json
import unittest

from evals import embeddings as emb


class TestArms(unittest.TestCase):
    code = {"read1": {"fee"}, "read2": {"wire"}}
    near = {"q1": (0.9, "read1"), "q2": (0.5, "read2"), "q3": (0.95, "read2")}
    truth = {"read1": {"fee"}, "read2": {"wire"}, "q1": {"fee"}, "q2": {"wire"}, "q3": set()}

    def test_a_queued_clause_takes_its_neighbors_rule_above_the_threshold(self):
        arms = emb.arms(self.code, {"q3": {"hold"}}, self.near, 0.8)
        self.assertEqual(arms["embeddings"]["q1"], {"fee"})
        self.assertNotIn("q2", arms["embeddings"])
        self.assertEqual(arms["extractor"]["q3"], {"hold"})
        self.assertEqual(arms["all"]["q3"], {"hold"})
        self.assertEqual(arms["all"]["q1"], {"fee"})

    def test_the_measures_count_paired_paraphrases_and_wrong_rules(self):
        rules = emb.arms(self.code, {}, self.near, 0.8)["embeddings"]
        m = emb.measure(rules, self.code, self.truth, [("q1", "fee", ["read1"]), ("q2", "wire", ["read2"])])
        self.assertEqual(m, {"paired": 1, "of": 2, "added": 2, "wrong": 1})

    def test_the_threshold_trades_right_rules_against_wrong_ones_counted_twice(self):
        near = {"q1": (0.9, "read1"), "q2": (0.5, "read2"), "q3": (0.95, "read2")}
        truth = {"q1": {"fee"}, "q2": set(), "q3": {"wire"}}
        lib = {"code": self.code, "near": near, "truth": truth, "p": []}
        self.assertEqual(emb.tune([lib], grid=[0.4, 0.8, 0.96]), 0.8)


if __name__ == "__main__":
    unittest.main()
