"""The CI gate fails a planted regression, and the key scan catches a planted key. The fake key is built at run time,
so no file here ever holds one."""
import json
import shutil
import unittest
from pathlib import Path

from ci import run_gate

HERE = Path(__file__).resolve().parent.parent
TMP = HERE.joinpath(".cache", "tmp", "test_gate")
CFG = json.loads(HERE.joinpath("config", "gate.json").read_text())


def review(caught_c=36, caught_p=14, alarms=0, unexplained=0):
    return {"score": {"per_category": {"C": {"caught": caught_c, "planted": 36}, "P": {"caught": caught_p, "planted": 14}},
                      "summary": {"false_alarms": alarms, "unexplained": unexplained}}}


class TestThresholds(unittest.TestCase):
    def test_the_clean_results_pass(self):
        self.assertEqual(run_gate.thresholds(review(), {"drafts": {}, "audit_problems": []}, CFG), [])

    def test_each_planted_regression_fails(self):
        self.assertTrue(run_gate.thresholds(review(caught_c=30), None, CFG))
        self.assertTrue(run_gate.thresholds(review(alarms=1), None, CFG))
        self.assertTrue(run_gate.thresholds(review(unexplained=2), None, CFG))
        self.assertTrue(run_gate.thresholds(review(), {"drafts": {"2026": {"gate_pass_rate": 0.5}}}, CFG))
        self.assertTrue(run_gate.thresholds(review(), {"audit_problems": ["no audit line for a run"]}, CFG))


class TestCopy(unittest.TestCase):
    def test_no_copy_puts_a_comma_before_so(self):
        self.assertEqual(run_gate.comma_before_so(), [])


class TestKeyScan(unittest.TestCase):
    def test_a_planted_key_is_found_and_the_repo_is_clean(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.joinpath("config").mkdir(parents=True)
        fake = "sk-" + "ant-" + "a1B2" * 10
        TMP.joinpath("config", "leak.json").write_text(json.dumps({"key": fake}))
        self.assertEqual(run_gate.key_shaped(TMP), ["config/leak.json"])
        self.assertEqual(run_gate.key_shaped(), [])


if __name__ == "__main__":
    unittest.main()
