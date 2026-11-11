"""The synthetic world: rebuilds byte for byte, plants exactly what the catalog says, and leaks no private word."""
import json
import shutil
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app import never
from generate import catalog, taxonomy, world
from generate.values import key as vkey

HERE = Path(__file__).resolve().parent.parent
TMP = HERE.joinpath(".cache", "tmp", "test_world")
SEED = 2026


def text_of(path):
    if path.suffix == ".docx":
        with zipfile.ZipFile(path) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
        return " ".join(t.text or "" for t in root.iter() if t.tag.endswith("}t"))
    return path.read_text(encoding="utf-8")


class TestWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TMP.exists():
            shutil.rmtree(TMP)
        cls.first = world.build_seed(SEED, "demo", TMP.joinpath("a"))
        cls.second = world.build_seed(SEED, "demo", TMP.joinpath("b"))
        kd = TMP.joinpath("a", "key", str(SEED))
        cls.plan = json.loads(kd.joinpath("plan.json").read_text())
        cls.key = json.loads(kd.joinpath("key.json").read_text())
        cls.evals = json.loads(kd.joinpath("evals.json").read_text())
        cls.experts = json.loads(kd.joinpath("experts.json").read_text())
        cls.clauses = {c["id"]: (d, c) for d in cls.plan["documents"] for s in d["sections"] for c in s["clauses"]}

    def test_rebuild_is_byte_identical(self):
        self.assertEqual(self.first["library"], self.second["library"])
        self.assertEqual(self.first["key"], self.second["key"])

    def test_counts_match_the_catalog(self):
        c = self.key["counts"]
        for cat in ("C", "P", "D", "N"):
            self.assertEqual(c[cat], catalog.COUNTS[cat], cat)
        self.assertGreaterEqual(c["S"], 13)
        self.assertGreaterEqual(c["V"], catalog.COUNTS["V_state"] + catalog.COUNTS["V_line"])
        self.assertGreaterEqual(c["A"], 16)
        self.assertEqual(len(self.key["out_of_scope"]), catalog.COUNTS["X"])

    def test_every_item_points_at_real_clauses(self):
        for it in self.key["items"]:
            refs = [it.get("target"), it.get("anchor")] + it.get("source", []) + it.get("copy", [])
            for r in filter(None, refs):
                self.assertIn(r, self.clauses, f"{it['id']} points at a missing clause {r}")

    def test_contradictions_really_contradict(self):
        for it in self.key["items"]:
            if it["category"] not in ("C", "P"):
                continue
            target = self.clauses[it["target"]][1]["atoms"][0]["value"]
            anchor = self.clauses[it["anchor"]][1]["atoms"][0]["value"]
            self.assertNotEqual(vkey(target), vkey(anchor), it["id"])
            self.assertEqual(vkey(anchor), vkey(it["values"]["canonical"]), it["id"])

    def test_paraphrases_change_the_phrasing(self):
        for it in self.key["items"]:
            if it["category"] == "P":
                fam_t = self.clauses[it["target"]][1]["atoms"][0]["family"]
                fam_a = self.clauses[it["anchor"]][1]["atoms"][0]["family"]
                self.assertNotEqual(fam_t, fam_a, it["id"])

    def test_variations_state_a_narrower_scope(self):
        for it in self.key["items"]:
            if it["category"] != "V":
                continue
            t = self.clauses[it["target"]][1]["atoms"][0]
            a = self.clauses[it["anchor"]][1]["atoms"][0]
            narrower_state = set(t["states"]) < set(a["states"])
            narrower_line = set(t["lines"]) < set(a["lines"]) or not set(t["lines"]) & set(a["lines"])
            self.assertTrue(narrower_state or narrower_line, it["id"])

    def test_old_versions_share_an_id_with_an_earlier_date(self):
        docs = {d["key"]: d for d in self.plan["documents"]}
        for it in self.key["items"]:
            if it["category"] == "S":
                old, cur = docs[it["old_doc"]], docs[it["current_doc"]]
                self.assertEqual(old["id"], cur["id"])
                self.assertLess(old["effective"], cur["effective"])
                self.assertLess(old["version"], cur["version"])

    def test_every_docx_parses(self):
        lib = TMP.joinpath("a", "library", str(SEED))
        files = sorted(lib.glob("*.docx"))
        self.assertGreater(len(files), 40)
        for p in files:
            with zipfile.ZipFile(p) as z:
                ElementTree.fromstring(z.read("word/document.xml"))

    def test_no_private_word_in_the_library(self):
        lib = TMP.joinpath("a", "library", str(SEED))
        word_list = never.words()
        for p in sorted(lib.iterdir()):
            self.assertEqual(never.hits(text_of(p), word_list), [], p.name)

    def test_eval_sets_have_their_sizes(self):
        self.assertEqual(len(self.evals["extraction"]), 180)
        self.assertGreaterEqual(len(self.evals["pairs"]), 200)
        self.assertEqual(len(self.evals["judge"]), 30)
        self.assertEqual(len(self.evals["assistant"]), 10)

    def test_experts_disagree_only_where_designed(self):
        ops, comp = self.experts["pairs"]["operations"], self.experts["pairs"]["compliance"]
        disagree = [p for p in self.evals["pairs"] if ops[p["pair"]]["label"] != comp[p["pair"]]["label"]]
        cats = {p["category"] for p in disagree}
        self.assertTrue(cats <= {"A", "S"}, cats)
        self.assertEqual(sum(1 for p in disagree if p["category"] == "A"),
                         sum(1 for p in self.evals["pairs"] if p["category"] == "A"))

    def test_every_attribute_is_stated_somewhere(self):
        seen = {c["atoms"][0]["attribute"] for _, c in self.clauses.values() if c["atoms"]}
        self.assertEqual(seen, set(taxonomy.BY_ID))


class TestFrozen(unittest.TestCase):
    def test_generator_matches_the_freeze(self):
        frozen = HERE.joinpath("evals", "frozen.json")
        if not frozen.exists():
            self.skipTest("not frozen yet")
        want = json.loads(frozen.read_text())
        self.assertEqual(world.generator_hash(), want["generator"],
                         "The generator changed after the freeze. That needs a new catalog version.")


if __name__ == "__main__":
    unittest.main()
