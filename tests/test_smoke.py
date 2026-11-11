"""The skeleton holds together: the words load for every profile, and the build runs."""
import subprocess
import sys
import unittest
from pathlib import Path

from app import never, words

HERE = Path(__file__).resolve().parent.parent


class TestWords(unittest.TestCase):
    def test_both_profiles_load(self):
        self.assertIn("general", words.profiles())
        for name in words.profiles():
            w = words.load(name)
            self.assertTrue(w["page.title"])

    def test_profiles_override_the_footer(self):
        public = words.load("general")["page.footer"]
        self.assertEqual(never.hits(public), [])
        for name in words.profiles():
            if name != "general":
                self.assertNotEqual(words.load(name)["page.footer"], public)

    def test_a_missing_key_fails(self):
        with self.assertRaises(words.MissingWord):
            words.load("general")["no.such.key"]

    def test_fill_needs_every_name(self):
        w = words.load("general")
        self.assertIn("Larkhaven Bank", w.fill("header.bank", bank="Larkhaven Bank"))
        with self.assertRaises(words.MissingWord):
            w.fill("header.bank")

    def test_a_key_twice_in_one_file_fails(self):
        with self.assertRaises(ValueError):
            words.parse("## a\none\n\n## a\ntwo\n")


class TestBuild(unittest.TestCase):
    @unittest.skipUnless(HERE.joinpath("data", "library", "2026").exists(), "run python3 build.py first")
    def test_the_build_runs_for_each_profile(self):
        for name in words.profiles():
            out = subprocess.run([sys.executable, str(HERE.joinpath("build.py")), "--profile", name, "--only", "review"],
                                 capture_output=True, text=True, cwd=str(HERE))
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn(f"the {name} profile", out.stdout)


if __name__ == "__main__":
    unittest.main()
