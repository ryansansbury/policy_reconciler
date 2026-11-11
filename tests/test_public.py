"""The public copy is replay only. Nothing in the build or the page can reach the network or start another program,
and every recording names only its vendor and model."""
import ast
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SHIPPED = ("engine", "agents", "app", "generate", "evals", "prompts")
NEVER_IMPORTED = {"socket", "ssl", "urllib", "http", "subprocess", "requests", "ftplib", "smtplib", "telnetlib",
                  "xmlrpc", "asyncio", "webbrowser"}
BACKEND_FIELDS = {"vendor", "model", "label", "client_context"}


def modules():
    yield HERE.joinpath("build.py")
    for folder in SHIPPED:
        yield from sorted(HERE.joinpath(folder).rglob("*.py"))


class TestReplayOnly(unittest.TestCase):
    def test_no_module_imports_anything_that_reaches_the_network_or_starts_a_program(self):
        found = []
        for path in modules():
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    names = []
                found += [f"{path.relative_to(HERE)} imports {n}" for n in names if n.split(".")[0] in NEVER_IMPORTED]
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os"
                        and node.attr.startswith(("system", "popen", "exec", "spawn"))):
                    found.append(f"{path.relative_to(HERE)} calls os.{node.attr}")
        self.assertEqual(found, [])

    def test_there_is_no_model_layer_to_call(self):
        self.assertFalse(HERE.joinpath("agents", "llm.py").exists())

    def test_the_head_carries_the_address_and_the_preview_from_site_json(self):
        from app import bundle
        site = json.loads(HERE.joinpath("config", "site.json").read_text(encoding="utf-8"))
        tags = bundle.site_tags()
        self.assertIn(f'<link rel="canonical" href="{site["url"]}">', tags)
        self.assertIn(f'<meta property="og:image" content="{site["url"]}{site["image"]}">', tags)
        self.assertIn("summary_large_image", tags)

    def test_the_page_carries_no_source_and_every_code_link_opens_a_file_in_this_repo(self):
        from app import code_view
        site = json.loads(HERE.joinpath("config", "site.json").read_text(encoding="utf-8"))
        self.assertEqual(code_view.blob("engine/gate.py"), f"{site['repo']}/blob/{site['branch']}/engine/gate.py")
        linked = {p for p, _ in code_view.FEATURED} | set(code_view.BOXES.values())
        self.assertEqual([p for p in sorted(linked) if not HERE.joinpath(p).exists()], [])
        self.assertFalse(HERE.joinpath("app", "showcase.json").exists())
        self.assertFalse(HERE.joinpath("site", "code.js").exists())

    def test_every_recording_names_only_its_vendor_and_model(self):
        extra = set()
        for path in HERE.joinpath("data", "ai_runs").rglob("*.json"):
            extra |= set(json.loads(path.read_text(encoding="utf-8")).get("backend") or {}) - BACKEND_FIELDS
        self.assertEqual(extra, set())


if __name__ == "__main__":
    unittest.main()
