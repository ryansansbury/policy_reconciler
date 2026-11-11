"""Drafts, the gate, the judge and the assistant, offline: the gate's every failure, the diff, the search, the
publisher, each step's checks, the judge's calibration and family rule, and the whole chain from draft to answer
driven by stand-in models that answer from the gold."""
import json
import shutil
import unittest
from pathlib import Path

from agents import assisting, drafting, items, judging, replay, rulings, standin, validate
from engine import diff, gate, publish, search
from evals import score_ai

HERE = Path(__file__).resolve().parent.parent
TMP = HERE.joinpath(".cache", "tmp", "test_drafts")
KEY = HERE.joinpath("data", "key", "2026")
CFG = json.loads(HERE.joinpath("config", "models.json").read_text())["models"]
ALLOWED = {"POL-FEE-01@v2/s3/c2#value": "$50", "POL-FEE-01@v2/s3/c2#v2": "one calendar year"}


def needs_world(test):
    return unittest.skipUnless(KEY.exists(), "run python3 build.py first")(test)


def quiet(line):
    pass


class TestGate(unittest.TestCase):
    def test_a_draft_with_only_placeholders_passes_and_renders(self):
        text = "A branch manager may waive up to {clause:POL-FEE-01@v2/s3/c2#value} in fees for one account."
        problems, rendered = gate.check(text, ALLOWED)
        self.assertEqual(problems, [])
        self.assertEqual(rendered, "A branch manager may waive up to $50 in fees for one account.")

    def test_an_injected_value_fails(self):
        text = "A branch manager may waive up to {clause:POL-FEE-01@v2/s3/c2#value}, or $75 with approval."
        problems, rendered = gate.check(text, ALLOWED)
        self.assertIsNone(rendered)
        self.assertTrue(any("$75" in p for p in problems))

    def test_a_value_in_words_fails_too(self):
        problems, _ = gate.check("Collect two forms of identification and cite {clause:POL-FEE-01@v2/s3/c2#value}.",
                                 ALLOWED)
        self.assertTrue(any('"two"' in p for p in problems))

    def test_an_unknown_placeholder_and_no_citation_fail(self):
        self.assertTrue(gate.check("Cite {clause:FAQ-FEE-02@v2/s1/c1#value}.", ALLOWED)[0])
        self.assertIn("the draft cites no clause for its value", gate.check("Waive fees with care.", ALLOWED)[0])

    def test_a_role_rule_names_roles_only_through_placeholders(self):
        allowed = {"POL-AOP-01@v2/s3/c1#value": "branch manager"}
        ok = "Exceptions need approval from the {clause:POL-AOP-01@v2/s3/c1#value}."
        self.assertEqual(gate.check(ok, allowed, "role")[0], [])
        bad = ok + " A regional manager may also approve."
        self.assertTrue(gate.check(bad, allowed, "role")[0])

    def test_a_modal_rule_states_must_or_may_only_through_its_placeholder(self):
        allowed = {"POL-LND-01@v4/s3/c1#value": "must"}
        ok = "Staff {clause:POL-LND-01@v4/s3/c1#value} record the reason for every pricing exception."
        self.assertEqual(gate.check(ok, allowed, "modal"), ([], "Staff must record the reason for every pricing exception."))
        self.assertTrue(gate.check(ok + " It may wait until closing.", allowed, "modal")[0])


class TestDiffSearchPublish(unittest.TestCase):
    def test_the_diff_marks_what_changed(self):
        self.assertEqual(diff.diff("wires after 3 PM wait", "wires after 4 PM wait"),
                         [("same", "wires after"), ("del", "3"), ("add", "4"), ("same", "PM wait")])

    def test_search_ranks_the_clause_with_the_rare_words(self):
        ix = search.Index([{"id": "a", "text": "Wire transfers need a callback above the threshold."},
                           {"id": "b", "text": "Fee waivers need a branch manager."},
                           {"id": "c", "text": "Dormant accounts get a notice."}])
        self.assertEqual(ix.search("When does a wire need a callback?", 2)[0]["id"], "a")
        self.assertEqual(ix.search("the and of"), [])

    @needs_world
    def test_publishing_archives_older_versions_and_replaced_clauses(self):
        from engine import pipeline
        result = pipeline.run(HERE.joinpath("data", "library", "2026"))
        before = publish.before(result)
        some = before[0]["id"]
        after, archived = publish.after(result, [{"group": "g-x", "title": "T", "text": "New text.", "replaces": [some],
                                                  "approved_by": "the specialist"}])
        ids = {e["id"] for e in after}
        self.assertNotIn(some, ids)
        self.assertIn("draft:g-x", ids)
        self.assertTrue(any(a["reason"] == "older version" for a in archived))
        self.assertEqual(next(a for a in archived if a["id"] == some)["by"], "draft:g-x")


class TestChecks(unittest.TestCase):
    def test_the_judge_needs_every_criterion_and_quoted_evidence(self):
        item = {"draft": "d1", "text": "Wires go out the next business day, in most cases.", "sources": ["Wires go out."]}
        good = {c: {"pass": True, "evidence": ""} for c in judging.CRITERIA}
        good["plain"] = {"pass": False, "evidence": "in most cases"}
        reply = json.dumps({"results": [{"draft": "d1", "scores": good}]})
        self.assertEqual(judging.check([item], reply)[1], [])
        bad = dict(good, plain={"pass": False, "evidence": "not in the draft"})
        self.assertTrue(judging.check([item], json.dumps({"results": [{"draft": "d1", "scores": bad}]}))[1])
        missing = {k: v for k, v in good.items() if k != "keeps_scope"}
        self.assertTrue(judging.check([item], json.dumps({"results": [{"draft": "d1", "scores": missing}]}))[1])

    def test_the_judge_reads_each_distinct_comparison_draft_from_another_vendor(self):
        vendor = {"a1": "A", "a2": "A", "b1": "B"}
        groups = [{"group": "g1", "keep": {"text": "Keep this rule."}}]
        drafts = {"a1": {"g1": {"rendered": "Same text."}}, "a2": {"g1": {"rendered": "Same text."}},
                  "b1": {"g1": {"rendered": "Other text."}}}
        main = judging.comparison_items(groups, drafts, "b1", "b1", vendor)
        second = judging.comparison_items(groups, drafts, "a2", "b1", vendor)
        self.assertEqual([i["text"] for i in main], ["Same text."])
        self.assertEqual([i["text"] for i in second], ["Other text."])
        self.assertNotIn("a1", main[0]["draft"])
        ok = {c: {"pass": True} for c in judging.CRITERIA}
        grades = {"b1": {main[0]["draft"]: ok}, "a2": {second[0]["draft"]: dict(ok, keeps_rules={"pass": False})}}
        self.assertTrue(judging.comparison_grades("a1", drafts["a1"], grades, vendor)["g1"][0])
        self.assertFalse(judging.comparison_grades("b1", drafts["b1"], grades, vendor)["g1"][0])
        lenient = judging.comparison_grades("b1", drafts["b1"], grades, vendor, passes=lambda key, g: True)
        self.assertTrue(lenient["g1"][0])

    def test_rulings_cover_the_judges_flags_by_rule_or_by_draft(self):
        record = {"rules": {"subject": {"criterion": "adds_no_rule", "words": ["staff"], "verdict": "harmless"}},
                  "drafts": {"g1.aaaa": {"seed": "2026", "group": "g1", "criterion": "adds_no_rule", "verdict": "real",
                                         "note": "Write it again."},
                             "g2.bbbb": {"seed": "2026", "group": "g2", "criterion": "plain", "verdict": "source_gap"}}}
        ok = {c: {"pass": True, "evidence": ""} for c in judging.CRITERIA}
        staff = dict(ok, adds_no_rule={"pass": False, "evidence": "Staff"})
        self.assertTrue(rulings.passes("g9.cccc", staff, record))
        self.assertFalse(rulings.passes("g1.aaaa", staff, record))
        self.assertFalse(rulings.passes("g9.cccc", dict(ok, keeps_rules={"pass": False, "evidence": "same day"}), record))
        self.assertTrue(rulings.passes("g2.bbbb", dict(ok, plain={"pass": False, "evidence": "longer"}), record))
        self.assertEqual(rulings.notes("2026", record), {"g1": "Write it again."})
        self.assertEqual(rulings.notes("6101", record), {})

    def test_every_recorded_ruling_is_a_known_verdict_in_plain_words(self):
        record = rulings.load()
        for r in list(record["rules"].values()) + list(record["drafts"].values()):
            self.assertIn(r["verdict"], rulings.VERDICTS)
            self.assertEqual(validate.writing_problems(r["reason"]), [], r["reason"])
        for d in record["drafts"].values():
            self.assertEqual(validate.writing_problems(d.get("note", "")), [], d.get("note"))

    def test_the_family_rule(self):
        self.assertFalse(judging.family_ok("claude-opus", "claude-sonnet", CFG))
        self.assertTrue(judging.family_ok("claude-opus", "google-a", CFG))

    def test_the_assistant_must_flag_disagreeing_sources_and_cite_what_it_states(self):
        item = {"question": "q-1", "type": "money", "clauses": [{"id": "a", "text": "The limit is $50."},
                                                                {"id": "b", "text": "The limit is $75."}]}

        def run(answer, cites, disagree):
            r = {"question": "q-1", "answer": answer, "citations": cites, "sources_disagree": disagree}
            return assisting.check([item], json.dumps({"results": [r]}))[1]

        self.assertEqual(run("The sources disagree between $50 and $75.", ["a", "b"], True), [])
        self.assertTrue(run("The limit is $50 and the other page says $75.", ["a", "b"], False))
        self.assertTrue(run("The limit is $60.", ["a"], False))
        self.assertTrue(run("The limit is $50.", ["c"], False))


def oracle_draft(item, repair=False):
    """The kept clause itself, with every value it states swapped for its placeholder, which is a faithful draft."""
    text, keep = item["keep"]["text"], item["keep"]["clause"]
    for ph, words in sorted(item["allowed"].items(), key=lambda kv: -len(kv[1])):
        if ph.startswith(keep + "#") and words in text:
            text = text.replace(words, "{clause:" + ph + "}", 1)
    if item["type"] == "modal":
        text = "Staff " + item["placeholder"] + " follow this rule. " + " ".join(gate.MODAL_WORDS.sub("", text).split())
    return {"title": item["rule"], "text": text}


if __name__ == "__main__":
    unittest.main()
