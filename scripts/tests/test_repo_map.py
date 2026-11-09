"""CLI contracts for repository-map validation; no application dependencies."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "check_repo_map.py"
DOCUMENTS = (
    "README.md", "AGENTS.md", "frontend/AGENTS.md", "backend/AGENTS.md",
    "docs/REPO_MAP.md", "docs/ARCHITECTURE.md", "docs/DEVELOPMENT.md",
    "docs/COMPATIBILITY.md",
)


class RepoMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="repo map 中文 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in DOCUMENTS:
            self.write(name, "# Documentation\n")
        self.write("backend/app/api/router.py", '''
api_router = APIRouter(prefix="/api")
api_router.include_router(chat.router, prefix="/chat")
''')
        # A parser must not import this module or execute its side effects.
        self.write("backend/app/api/chat.py", '''
raise RuntimeError("must not execute application code")
router = APIRouter(prefix="/nested")
@router.post("/stream")
async def stream_chat():
    pass
''')
        self.write("backend/main.py", '''
def create_app():
    app.include_router(api_router)
    @app.get("/health")
    async def health():
        pass
''')

    def write(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            cwd=self.root.parent, capture_output=True, text=True, encoding="utf-8",
        )

    def test_accepts_unicode_space_path_and_runs_outside_repository(self):
        self.write("docs/中文 资料.md", "hello")
        self.write("docs/REPO_MAP.md", "[file](<中文 资料.md>)\n`POST /api/chat/nested/stream`\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_missing_link(self):
        self.write("docs/REPO_MAP.md", "[file](missing.py)\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing.py", result.stdout)

    def test_rejects_path_outside_repository(self):
        self.write("docs/REPO_MAP.md", "[file](../../outside.txt)\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside repository", result.stdout)

    def test_rejects_wrong_case_even_on_case_insensitive_filesystems(self):
        self.write("docs/Guide.md", "hello")
        self.write("docs/REPO_MAP.md", "[file](guide.md)\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("guide.md", result.stdout)

    def test_rejects_removed_api_reference(self):
        self.write("docs/REPO_MAP.md", "`POST /api/chat/removed`\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("POST /api/chat/removed", result.stdout)

    def test_exports_combined_router_prefixes_and_nested_health_without_import(self):
        result = self.run_cli("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertCountEqual(payload["routes"], [
            {"method": "GET", "path": "/health", "file": "backend/main.py", "handler": "health"},
            {"method": "POST", "path": "/api/chat/nested/stream", "file": "backend/app/api/chat.py", "handler": "stream_chat"},
        ])
        self.assertNotIn(str(self.root), result.stdout)

    def test_reports_syntax_error_as_failure_without_traceback(self):
        self.write("backend/app/api/chat.py", "this is invalid python !!!")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("chat.py", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_dynamic_route_instead_of_silently_omitting_it(self):
        self.write("backend/app/api/chat.py", '''
router = APIRouter()
@router.post(dynamic_path)
def dynamic():
    pass
''')
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("literal", result.stdout)

    def test_rejects_imperative_router_registration_instead_of_omitting_it(self):
        with (self.root / "backend/app/api/chat.py").open("a", encoding="utf-8") as stream:
            stream.write('\nrouter.add_api_route("/extra", stream_chat)\n')
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsupported", result.stdout)

    def test_rejects_imperative_app_registration_instead_of_omitting_it(self):
        with (self.root / "backend/main.py").open("a", encoding="utf-8") as stream:
            stream.write('\napp.add_api_route("/extra", health)\n')
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsupported", result.stdout)

    def test_rejects_machine_specific_links_before_url_scheme_filtering(self):
        for target in ("C:/Users/someone/missing.md", r"C:\Users\someone\missing.md",
                       r"\\server\share\missing.md", "file:///Users/someone/missing.md"):
            with self.subTest(target=target):
                self.write("docs/REPO_MAP.md", f"[file]({target})\n")
                result = self.run_cli()
                self.assertEqual(result.returncode, 1)
                self.assertIn("repository-relative", result.stdout)


if __name__ == "__main__":
    unittest.main()
