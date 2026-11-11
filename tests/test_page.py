"""The page: it builds for every profile, the strip check holds, every word it asks for exists, and the node
click-through passes every tab and finding with no script errors."""
import json
import shutil
import subprocess
import unittest
from unittest import mock
from pathlib import Path

from app import bundle, never, page, view
from app import words as words_mod

HERE = Path(__file__).resolve().parent.parent
SITE = HERE.joinpath(".cache", "tmp", "test_page", "site")
RESULTS = json.loads(HERE.joinpath("evals", "code_only.json").read_text())["totals"]


def needs_world(test):
    return unittest.skipUnless(HERE.joinpath("data", "library", "2026").exists(), "run python3 build.py first")(test)


class TestStripCheck(unittest.TestCase):
    def test_a_never_word_fails_the_public_build(self):
        word = "zzplantedwordzz"
        with mock.patch.object(never, "words", return_value=(word,)):
            with self.assertRaises(bundle.StripCheckFailed):
                bundle.strip_check([f"A page that says {word}"], "general")
            self.assertEqual(bundle.allowed_words("general"), set())


@needs_world
class TestPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(SITE.parent, ignore_errors=True)
        cls.profile = words_mod.default_profile()
        cls.info = bundle.build(cls.profile, 2026, ["claude-sonnet"], RESULTS, out=SITE)
        cls.html = SITE.joinpath("index.html").read_text()

    def test_every_tab_and_the_footer_render(self):
        for tab in bundle.NAV:
            self.assertIn(f"id=\"t-{tab}\"", self.html)
        self.assertIn(page.esc(words_mod.load(self.profile)["page.footer"]), self.html)
        self.assertIn("index, follow", self.html)

    def test_the_public_profile_carries_no_client_word(self):
        vm, combined = bundle.view_model(2026, ["claude-sonnet"])
        html, data = bundle.render(words_mod.load("general"), vm, combined, RESULTS)
        self.assertEqual(never.hits(html + data), [])

    def test_the_routing_panel_has_a_view_with_five_charts_for_every_vendor_choice(self):
        path = HERE.joinpath("evals", "model_comparison.json")
        if not path.exists():
            self.skipTest("no model comparison recorded")
        routes = json.loads(path.read_text())["routes"]
        views = self.html.split('class="route-view"')[1:]
        self.assertEqual(len(views), len(routes))
        self.assertEqual(sum(1 for v in views if v.split(">", 1)[0].rstrip().endswith("hidden")), len(routes) - 1)
        for v in views:
            chart = v.split("</figure>")[0]
            self.assertEqual(chart.count('class="facet"'), 5)
            self.assertGreaterEqual(chart.count('class="pt s-route"'), 3)
            self.assertIn('class="table-view"', chart)

    def test_the_embeddings_panel_shows_every_arm_in_order_and_the_choices(self):
        from app import how
        w = words_mod.load(self.profile)
        if not HERE.joinpath("evals", "embeddings.json").exists():
            self.assertIn(page.esc(w["embed.waiting"]), how.embed_panel(w))
        arm = {"paired": 1, "of": 2, "added": 1, "wrong": 0}
        data = {"model": "m", "threshold": 0.7, "dev": ["11", "23"], "held": ["6101"],
                "pairing": {a: dict(arm) for a in ("all", "code", "embeddings", "extractor")},
                "search": {"bm25": {"gold": 3, "both": 2}, "bm25_wide": {"gold": 4, "both": 3},
                           "hybrid": {"gold": 5, "both": 4}, "questions": 10, "lost": 0},
                "cost_per_library": {"embeddings": 0.0006, "embeddings_seconds": 1.0, "extractor": 0.3,
                                     "extractor_seconds": 110.0},
                "choice": {"pairing": "no_gain", "search": "keep"}}
        html = how.embed_panel(w, data)
        order = [html.index(page.esc(w["embed.arm." + a])) for a in ("code", "embeddings", "extractor", "all")]
        self.assertEqual(order, sorted(order))
        self.assertIn(page.esc(w["embed.choice.search.keep"]), html)
        self.assertIn("$0.0006", html)

    def test_every_column_of_numbers_lines_up_with_its_header(self):
        import re
        bad = []
        for attrs, body in re.findall(r"<table([^>]*)>(.*?)</table>", self.html, flags=re.S):
            head = re.search(r"<thead><tr>(.*?)</tr></thead>", body, flags=re.S)
            if not head:
                continue
            ths = re.findall(r"<th([^>]*)>", head.group(1))
            numeric = {}
            for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body.split("</thead>", 1)[1], flags=re.S)[:50]:
                for i, a in enumerate(re.findall(r"<td([^>]*)>", row)):
                    numeric.setdefault(i, set()).add('class="n"' in a)
            bad += [(attrs, i) for i, kinds in numeric.items() if i < len(ths) and (kinds == {True}) != ('class="n"' in ths[i])]
        self.assertEqual(bad, [])

    def test_ids_are_stable_and_unique(self):
        data = SITE.joinpath("data.js").read_text()
        rows = json.loads(data[data.index("=") + 1:].rstrip().rstrip(";"))["findings"]
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i.startswith("f-") for i in ids))

    @unittest.skipUnless(shutil.which("node"), "node isn't on the path")
    def test_the_click_through_passes(self):
        out = subprocess.run(["node", str(HERE.joinpath("tests", "js", "check_app.js")), str(SITE)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        report = json.loads(out.stdout)
        self.assertEqual(report["errors"], [])
        failed = [c for c in report["checks"] if not c["ok"]]
        self.assertEqual(failed, [], json.dumps(failed, indent=1)[:2000])
        self.assertGreater(len(report["checks"]), 20)


class TestRisk(unittest.TestCase):
    def test_the_formula(self):
        cfg = {"category": {"conflict": 3, "duplicate": 1, "superseded": 2}, "customer_weight": 1, "breadth_weight": 2,
               "topics": {"fees": {"severity": 2, "customer": True}}}
        self.assertEqual(view.risk({"type": "conflict", "topic": "fees", "breadth": 0.5}, cfg), 12.0)
        self.assertEqual(view.risk({"type": "superseded", "topic": "fees", "breadth": 0.5, "live": True}, cfg), 12.0)
        self.assertEqual(view.risk({"type": "duplicate", "topic": "other", "breadth": 1}, cfg), 3.0)


if __name__ == "__main__":
    unittest.main()
