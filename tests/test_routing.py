"""The routing rule: the cheapest model that clears each bar within the approved vendors, the faster one on a tie,
a judge from another vendor than the drafter, holds, and every vendor combination precomputed."""
import unittest

from agents import routing
from app import words


def row(vendor, quality, cost, seconds=1.0, **more):
    return dict(vendor=vendor, quality=quality, cost_per_item=cost, seconds_per_item=seconds, **more)


COMPARISON = {"steps": {
    "extract": {"big": row("A", 0.95, 0.010), "small": row("A", 0.945, 0.001), "other": row("B", 0.90, 0.0005)},
    "classify": {"big": row("A", 0.96, 0.02), "cheap": row("B", 0.95, 0.002, variations_as_conflict=1),
                 "mid": row("B", 0.95, 0.004)},
    "draft": {"big": row("A", 1.0, 0.05, judged=8), "cheap": row("B", 0.875, 0.01, judged=8),
              "unread": row("B", 1.0, 0.001, judged=0)},
    "assist": {"big": row("A", 1.0, 0.03), "cheap": row("B", 1.0, 0.003)},
    "judge": {"big": row("A", 0.97, 0.02, trusted_on_all=True), "gem": row("B", 0.96, 0.01, trusted_on_all=True)},
}}


class TestRouting(unittest.TestCase):
    def test_the_cheapest_model_that_clears_the_bar_wins(self):
        plan = routing.plan(COMPARISON, {"A", "B"})
        self.assertEqual(plan["extract"]["model"], "small")
        self.assertIn("other", plan["extract"]["rejected"])
        self.assertEqual(plan["extract"]["fallbacks"], ["big"])

    def test_a_variation_labeled_a_conflict_disqualifies(self):
        plan = routing.plan(COMPARISON, {"A", "B"})
        self.assertEqual(plan["classify"]["model"], "mid")
        self.assertEqual(plan["classify"]["rejected"]["cheap"], "classify_variation")

    def test_the_judge_avoids_the_drafters_vendor(self):
        plan = routing.plan(COMPARISON, {"A", "B"})
        self.assertEqual(plan["draft"]["model"], "big")
        self.assertEqual(plan["judge"]["model"], "gem")

    def test_a_drafter_the_judge_failed_or_never_read_does_not_route(self):
        rejected = routing.plan(COMPARISON, {"A", "B"})["draft"]["rejected"]
        self.assertEqual(rejected, {"cheap": "draft_below", "unread": "draft_unjudged"})

    def test_one_approved_vendor_can_leave_the_judge_without_a_model(self):
        plan = routing.plan(COMPARISON, {"A"})
        self.assertEqual((plan["judge"]["model"], plan["judge"]["reason"]), (None, "same_vendor"))

    def test_a_hold_keeps_its_model_and_names_the_free_route(self):
        plan = routing.plan(COMPARISON, {"A", "B"}, holds={"assist": "big"})
        self.assertEqual((plan["assist"]["model"], plan["assist"]["reason"]), ("big", "hold"))
        self.assertEqual((plan["assist"]["unheld"], plan["assist"]["fallbacks"]), ("cheap", ["cheap"]))

    def test_the_blend_prices_one_run_and_names_the_steps_a_person_does(self):
        plan = routing.plan(COMPARISON, {"A"})
        dollars, people = routing.blend(COMPARISON, plan, {"extract": 100, "judge": 10})
        self.assertEqual((dollars, people), (0.1, ["judge"]))

    def test_the_judge_bar_reads_its_lowest_criterion(self):
        m = {"by_criterion": {"keeps_rules": 1.0, "plain": 0.85}}
        self.assertEqual((routing.measure("judge", m), routing.bar("judge", 1.0)), (0.85, 0.9))
        self.assertEqual(routing.bar("classify", 0.98), 0.96)

    def test_every_reason_the_rule_can_give_has_its_words(self):
        w = words.load("general")
        for key in ("cheapest", "hold", "none_clears", "same_vendor", "unmeasured"):
            self.assertTrue(w["route.reason." + key])
        for key in routing.WHY:
            self.assertTrue(w["route.why." + key])

    def test_every_vendor_combination_is_precomputed(self):
        self.assertEqual(sorted(routing.every_policy(COMPARISON)), ["A", "A + B", "B"])


if __name__ == "__main__":
    unittest.main()
