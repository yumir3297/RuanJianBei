from __future__ import annotations

import json
import os
import ast
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy/scripts/deploy-backend.sh"
IMAGE_ID = "sha256:" + "a" * 64


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class BackendDeployOrderingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "commands.log"
        docker = self.bin / "docker"
        docker.write_text(
            "#!/bin/sh\n"
            f"echo docker:$* >> '{self.log}'\n"
            "if [ \"$1\" = image ] && [ \"$2\" = inspect ]; then case \"$4\" in *org.opencontainers*) echo \"${FAKE_SOURCE_SHA:-abcdef0123456}\";; *) echo '" + IMAGE_ID + "';; esac; fi\n"
            "if [ \"$1\" = compose ]; then\n"
            "  case \"$*\" in *'config --format json'*) printf '%s\\n' '{\"services\":{\"gateway\":{\"image\":\"nginx:1.28-alpine\"},\"api\":{\"image\":\"scenic-guide-backend:candidate\"}}}';; esac\n"
            "  case \"$*\" in *'config --images'*) printf '%s\\n' nginx:1.28-alpine scenic-guide-backend:candidate;; esac\n"
            "  case \"$*\" in *'run --rm migrate python -m app.cli.deployment check-schema'*) echo \"${FAKE_PREFLIGHT_SCHEMA:-head-2}\";; *'check-schema'*) echo \"${FAKE_SCHEMA:-head-2}\";; esac\n"
            "  case \"$*\" in *'nginx -t'*) [ \"${FAIL_NGINX:-0}\" = 1 ] && exit 1;; esac\n"
            "  case \"$*\" in *'ps --status running -q'* ) [ \"${FAKE_RUNNING:-0}\" = 1 ] && echo api-container;; esac\n"
            "fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        docker.chmod(0o755)
        pg_dump = self.bin / "pg_dump"
        pg_dump.write_text(
            f"#!/bin/sh\necho pg_dump:$* >> '{self.log}'\n"
            "while [ $# -gt 0 ]; do if [ \"$1\" = --file ]; then [ \"${FAIL_PG_DUMP:-0}\" = 1 ] && exit 1; shift; echo snapshot > \"$1\"; fi; shift; done\n",
            encoding="utf-8",
        )
        pg_dump.chmod(0o755)
        flock = self.bin / "flock"
        flock.write_text(f"#!/bin/sh\necho flock:$* >> '{self.log}'\n[ \"${{FAIL_FLOCK:-0}}\" = 1 ] && exit 1\nexit 0\n", encoding="utf-8")
        flock.chmod(0o755)
        self.env_file = self.root / "runtime.env"
        self.env_file.write_text("APP_ENV=production\nSOURCE_SHA=abcdef0123456\n", encoding="utf-8")
        self.state_root = self.root / "app-state"
        self.state_root.mkdir()
        (self.state_root / "manifest.json").write_text("{}", encoding="utf-8")
        self.backup_dir = self.root / "backups"
        self.current_backend_release = self.root / "releases/current/backend-release.json"
        self.lock_file = self.root / "deployment.lock"
        self.frontends = []
        for app, capabilities in (("tourist", ["visitor-config-v1", "guide-context-v1"]), ("admin", ["admin-runtime-limits-v1"])):
            self.frontends.append(write_json(self.root / f"{app}.json", {
                "app": app, "release_id": f"{app}-1", "required_backend_capabilities": capabilities,
            }))
        self.candidate = write_json(self.root / "backend-release.json", {
            "image_digest": IMAGE_ID, "source_sha": "abcdef0123456", "schema_head": "head-2",
            "capabilities": ["visitor-config-v1", "guide-context-v1", "admin-runtime-limits-v1"],
        })
        self.compose_file = ROOT / "deploy/compose.yaml"

    def tearDown(self):
        self.temp.cleanup()

    def run_deploy(self, *, fail_dump: bool = False, running: bool = False, schema_head: str = "head-2", preflight_schema_head: str = "head-2", fail_nginx: bool = False, fail_lock: bool = False, image_source_sha: str = "abcdef0123456") -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        environment.update({
            "PATH": f"{self.bin}:{environment['PATH']}", "DATABASE_URL": "postgresql+asyncpg://demo:secret@db.example:5432/demo",
            "COMMAND_LOG": str(self.log), "FAIL_PG_DUMP": "1" if fail_dump else "0",
            "FAKE_RUNNING": "1" if running else "0",
            "FAKE_SCHEMA": schema_head,
            "FAKE_PREFLIGHT_SCHEMA": preflight_schema_head,
            "FAIL_NGINX": "1" if fail_nginx else "0",
            "FAIL_FLOCK": "1" if fail_lock else "0",
            "FAKE_SOURCE_SHA": image_source_sha,
        })
        command = [
            str(SCRIPT), "--confirm-maintenance-window", "--w02-drained",
            "--compose-file", str(self.compose_file), "--env-file", str(self.env_file),
            "--candidate-release", str(self.candidate), "--state-root", str(self.state_root),
            "--backup-dir", str(self.backup_dir), "--current-backend-release", str(self.current_backend_release),
            "--lock-file", str(self.lock_file),
        ]
        for frontend in self.frontends:
            command.extend(("--frontend-release", str(frontend)))
        return subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)

    def test_backup_precedes_migration_and_contract_checks_precede_gateway(self):
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout + self.log.read_text(encoding="utf-8"))
        commands = self.log.read_text(encoding="utf-8").splitlines()
        lock_acquire = next(i for i, item in enumerate(commands) if item.startswith("flock:"))
        stop = next(i for i, item in enumerate(commands) if " stop --timeout 60 " in item)
        dump = next(i for i, item in enumerate(commands) if item.startswith("pg_dump:") and "--file" in item)
        migrate = next(i for i, item in enumerate(commands) if " run --rm migrate" in item)
        api_up = next(i for i, item in enumerate(commands) if " up -d api tool-worker" in item)
        preflight_schema_check = next(i for i, item in enumerate(commands) if " run --rm migrate python -m app.cli.deployment check-schema" in item)
        schema_check = next(i for i, item in enumerate(commands) if "exec -T api python -m app.cli.deployment check-schema" in item)
        contract = next(i for i, item in enumerate(commands) if "api/visitor-config" in item)
        gateway_up = next(i for i, item in enumerate(commands) if " up -d gateway" in item)
        nginx_check = next(i for i, item in enumerate(commands) if "nginx -t" in item)
        self.assertLess(lock_acquire, stop)
        self.assertLess(stop, dump)
        self.assertLess(dump, migrate)
        self.assertLess(migrate, preflight_schema_check)
        self.assertLess(preflight_schema_check, api_up)
        self.assertLess(api_up, schema_check)
        self.assertLess(schema_check, contract)
        self.assertLess(contract, gateway_up)
        self.assertLess(gateway_up, nginx_check)
        self.assertEqual(json.loads(self.current_backend_release.read_text(encoding="utf-8")), json.loads(self.candidate.read_text(encoding="utf-8")))
        self.assertTrue(list(self.backup_dir.glob("state-*.tar.gz")))

    def test_candidate_image_resolution_uses_api_service_not_first_compose_image(self):
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout + self.log.read_text(encoding="utf-8"))
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any("config --format json" in item for item in commands))
        self.assertTrue(any("image inspect --format {{.Id}} scenic-guide-backend:candidate" in item for item in commands))
        self.assertFalse(any("image inspect --format {{.Id}} nginx:1.28-alpine" in item for item in commands))

    def test_database_backup_failure_never_runs_migration_or_reopens_gateway(self):
        result = self.run_deploy(fail_dump=True)
        self.assertNotEqual(result.returncode, 0)
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any(" stop --timeout 60 " in item for item in commands), result.stderr + result.stdout + "\n".join(commands))
        self.assertFalse(any(" run --rm migrate" in item for item in commands))
        self.assertFalse(any(" up -d gateway" in item for item in commands))

    def test_any_old_process_still_running_blocks_backup_and_migration(self):
        result = self.run_deploy(running=True)
        self.assertNotEqual(result.returncode, 0)
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any(" stop --timeout 60 " in item for item in commands))
        self.assertFalse(any(item.startswith("pg_dump:") and "--file" in item for item in commands))
        self.assertFalse(any(" run --rm migrate" in item for item in commands))
        self.assertFalse(any(" up -d gateway" in item for item in commands))

    def test_schema_head_mismatch_never_reopens_gateway(self):
        result = self.run_deploy(preflight_schema_head="unexpected-head")
        self.assertNotEqual(result.returncode, 0)
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any(" run --rm migrate python -m app.cli.deployment check-schema" in item for item in commands))
        self.assertFalse(any(" up -d api tool-worker" in item for item in commands))
        self.assertFalse(any(" up -d gateway" in item for item in commands))
        self.assertFalse(self.current_backend_release.exists())

    def test_admin_auth_probe_embedded_python_is_valid(self):
        script = SCRIPT.read_text(encoding="utf-8")
        snippets = re.findall(r"python -c '([^']*)'", script, flags=re.DOTALL)
        probe = next((snippet for snippet in snippets if "/api/admin/runtime-limits" in snippet), None)
        self.assertIsNotNone(probe, "deployment script must retain its unauthenticated admin probe")
        tree = ast.parse(probe)
        nested_exec = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "exec"
        ]
        for call in nested_exec:
            self.assertTrue(call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str))
            ast.parse(call.args[0].value)

    def test_schema_drift_after_preflight_is_caught_before_gateway(self):
        result = self.run_deploy(schema_head="unexpected-head")
        self.assertNotEqual(result.returncode, 0)
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any(" up -d api tool-worker" in item for item in commands))
        self.assertTrue(any("exec -T api python -m app.cli.deployment check-schema" in item for item in commands))
        self.assertFalse(any(" up -d gateway" in item for item in commands))
        self.assertFalse(self.current_backend_release.exists())

    def test_nginx_failure_does_not_promote_current_backend_metadata(self):
        result = self.run_deploy(fail_nginx=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.current_backend_release.exists())
        commands = self.log.read_text(encoding="utf-8").splitlines()
        nginx_check = next(i for i, item in enumerate(commands) if "nginx -t" in item)
        self.assertTrue(any(" stop --timeout 60 gateway api tool-worker" in item for item in commands[nginx_check + 1:]))

    def test_lock_contention_blocks_maintenance_before_stop(self):
        result = self.run_deploy(fail_lock=True)
        self.assertNotEqual(result.returncode, 0)
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any(item.startswith("flock:") for item in commands))
        self.assertFalse(any(" stop --timeout 60 " in item for item in commands))
        self.assertFalse(any(" run --rm migrate" in item for item in commands))

    def test_image_source_label_mismatch_blocks_maintenance(self):
        result = self.run_deploy(image_source_sha="different-commit")
        self.assertNotEqual(result.returncode, 0)
        commands = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any("org.opencontainers.image.revision" in item for item in commands))
        self.assertFalse(any(" stop --timeout 60 " in item for item in commands))


if __name__ == "__main__":
    unittest.main()
