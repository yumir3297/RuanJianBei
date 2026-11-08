from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from render_api_policy import build_surface  # noqa: E402


class ApiSurfaceTests(unittest.TestCase):
    def test_inventory_exactly_matches_registered_method_and_path_pairs(self):
        checked_in = json.loads((ROOT / "deploy/api-surface.json").read_text(encoding="utf-8"))
        expected = build_surface()
        self.assertEqual(checked_in, expected)
        self.assertEqual(len(checked_in["routes"]), 86)
        self.assertEqual(len({(r["method"], r["path"]) for r in checked_in["routes"]}), 86)

    def test_boundary_is_method_sensitive_for_insights_and_owner_tasks(self):
        routes = {(r["method"], r["path"]): r for r in build_surface()["routes"]}
        self.assertEqual(routes[("GET", "/api/insights/qa-trend")]["boundary"], "admin-token")
        self.assertEqual(routes[("POST", "/api/insights/feedback")]["sites"], ["tourist"])
        self.assertEqual(routes[("GET", "/api/tour-sessions/{session_id}/events")]["boundary"], "visitor-cookie")
        self.assertNotIn(("GET", "/api/insights/feedback"), routes)

    def test_each_site_map_is_generated_from_its_allowlisted_routes(self):
        surface = build_surface()
        for site in ("tourist", "admin"):
            contents = (ROOT / f"deploy/nginx/{site}-api-map.conf").read_text(encoding="utf-8")
            self.assertIn(f"${site}_api_allowed", contents)
            self.assertIn(r"~^[A-Z]+:/api/ 0;", contents)
        self.assertIn("POST:/api/insights/feedback", (ROOT / "deploy/nginx/tourist-api-map.conf").read_text())
        self.assertNotIn("GET:/api/insights/qa-trend", (ROOT / "deploy/nginx/tourist-api-map.conf").read_text())


if __name__ == "__main__":
    unittest.main()
