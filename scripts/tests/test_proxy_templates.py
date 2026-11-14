from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from render_api_policy import import_budget_mib, render_nginx  # noqa: E402


class ProxyTemplateTests(unittest.TestCase):
    def test_compose_mounts_target_rendered_sites_and_route_maps(self):
        compose = (ROOT / "deploy/compose.yaml").read_text(encoding="utf-8")
        for filename in ("tourist.conf", "admin.conf", "tourist-api-map.conf", "admin-api-map.conf"):
            self.assertIn(f"${{NGINX_CONFIG_ROOT:?render target-specific NGINX config first}}/{filename}:/etc/nginx/conf.d/{filename}:ro", compose)
        self.assertIn("${NGINX_CONFIG_ROOT:?render target-specific NGINX config first}/snippets:/etc/nginx/snippets:ro", compose)
        self.assertNotIn("default.conf:/etc/nginx/conf.d", compose)

    def test_proxy_keeps_api_prefix_and_has_sse_timeout_policy(self):
        common = (ROOT / "deploy/nginx/common-api.conf").read_text(encoding="utf-8")
        self.assertIn("proxy_pass http://api:8000;", common)
        self.assertIn("proxy_buffering off;", common)
        self.assertIn("proxy_cache off;", common)
        self.assertIn("proxy_read_timeout 240s;", common)
        self.assertNotIn("proxy_pass http://api:8000/;", common)

    def test_site_templates_keep_endpoint_specific_limits_and_json_413(self):
        for site in ("tourist", "admin"):
            text = (ROOT / f"deploy/nginx/{site}.conf.template").read_text(encoding="utf-8")
            self.assertIn("__IMPORT_BODY_LIMIT__", text)
            self.assertIn("client_max_body_size 12m;", text)
            self.assertIn("client_max_body_size 6m;", text)
            self.assertIn("default_type application/json;", text)
            self.assertIn("return 413", text)
            self.assertIn("try_files $uri =404;", text)
            self.assertIn('add_header Cache-Control "public, max-age=31536000, immutable";', text)
            self.assertIn('location = /index.html { add_header Cache-Control "no-cache";', text)
            self.assertIn('location ^~ /models/ { add_header Cache-Control "no-cache";', text)

    def test_import_budget_tracks_actual_batch_file_count(self):
        file_bytes = 50 * 1024 * 1024
        self.assertEqual(import_budget_mib(1, file_bytes), 55)
        self.assertGreater(import_budget_mib(20, file_bytes), 55)
        self.assertEqual(import_budget_mib(20, file_bytes), 1009)

    def test_renderer_rejects_same_or_invalid_hosts_and_writes_exact_batch_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            render_nginx(output, "guide.example.org", "admin.example.org", 1, 50 * 1024 * 1024)
            tourist = (output / "tourist.conf").read_text(encoding="utf-8")
            admin = (output / "admin.conf").read_text(encoding="utf-8")
            self.assertIn("server_name guide.example.org;", tourist)
            self.assertIn("server_name admin.example.org;", admin)
            self.assertIn("client_max_body_size 55m;", tourist)
            self.assertIn("client_max_body_size 55m;", admin)
            self.assertTrue((output / "tourist-api-map.conf").is_file())
            self.assertTrue((output / "snippets/common-api.conf").is_file())
        with self.assertRaises(ValueError):
            render_nginx(Path(directory) / "invalid", "same.example.org", "same.example.org", 1, 100)


if __name__ == "__main__":
    unittest.main()
