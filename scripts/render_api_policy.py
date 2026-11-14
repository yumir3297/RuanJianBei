#!/usr/bin/env python3
"""Build/check the explicit gateway inventory from registered FastAPI routes."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_repo_map import collect_routes  # noqa: E402

OUT = ROOT / "deploy" / "api-surface.json"


def policy_for(route: dict) -> tuple[str, list[str]]:
    file = Path(route["file"]).name
    path = route["path"]
    handler = route["handler"]
    if file == "main.py":
        return "internal", ["gateway"]
    if file == "auth.py":
        return "anonymous", ["admin"]
    if file == "admin.py" or file in {"guide_loop.py", "knowledge.py", "knowledge_imports.py", "knowledge_publications.py"}:
        return "admin-token", ["admin"]
    if file == "insights.py":
        if handler == "submit_feedback":
            return "anonymous", ["tourist"]
        return "admin-token", ["admin"]
    if file in {"tour_sessions.py", "tool_execution.py"}:
        return "visitor-cookie", ["tourist"]
    if file == "itinerary.py":
        return "anonymous", ["tourist"]
    if file in {
        "chat.py", "display_assets.py", "guide.py", "quick_select.py", "recommend.py",
        "visitor_config.py", "vision.py", "voice.py", "weather.py",
    }:
        return "anonymous", ["tourist"]
    raise ValueError(f"Unclassified API route: {route['method']} {path} ({file}:{handler})")


def build_surface() -> dict:
    entries = []
    for route in collect_routes(ROOT):
        boundary, sites = policy_for(route)
        entries.append({"method": route["method"], "path": route["path"], "boundary": boundary, "sites": sites})
    entries.sort(key=lambda item: (item["path"], item["method"]))
    return {"schema_version": 1, "routes": entries}


def render_site_map(surface: dict, site: str) -> str:
    if site not in {"tourist", "admin"}:
        raise ValueError("site must be tourist or admin")
    variable = f"${site}_api_allowed"
    lines = [f'map "$request_method:$uri" {variable} {{', "    default 1;"]
    site_routes = [route for route in surface["routes"] if site in route["sites"]]
    site_routes.sort(key=lambda route: (route["method"], route["path"]))
    for route in site_routes:
        segments = route["path"].split("/")
        pattern = "/".join("[^/]+" if segment.startswith("{") and segment.endswith("}") else re.escape(segment) for segment in segments)
        lines.append(f"    ~^{route['method']}:{pattern}$ 1;")
    lines.extend([r"    ~^[A-Z]+:/api/ 0;", "}", ""])
    return "\n".join(lines)


def import_budget_mib(max_files: int, max_file_bytes: int) -> int:
    if max_files < 1 or max_file_bytes < 1:
        raise ValueError("upload limits must be positive")
    # Reserve 256 KiB multipart framing per file plus a 4 MiB request envelope.
    budget = max_files * max_file_bytes + max_files * 256 * 1024 + 4 * 1024 * 1024
    return math.ceil(budget / (1024 * 1024))


def validate_host(host: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host) or ".." in host:
        raise ValueError(f"invalid configured hostname: {host!r}")
    return host


def render_nginx(output_dir: Path, tourist_host: str, admin_host: str, max_files: int, max_file_bytes: int) -> None:
    tourist_host = validate_host(tourist_host)
    admin_host = validate_host(admin_host)
    if tourist_host == admin_host:
        raise ValueError("tourist and admin hostnames must differ")
    budget = f"{import_budget_mib(max_files, max_file_bytes)}m"
    output_dir.mkdir(parents=True, exist_ok=True)
    templates = {
        "tourist.conf": (ROOT / "deploy/nginx/tourist.conf.template", "__TOURIST_HOST__", tourist_host),
        "admin.conf": (ROOT / "deploy/nginx/admin.conf.template", "__ADMIN_HOST__", admin_host),
    }
    for output_name, (template, host_token, host) in templates.items():
        rendered = template.read_text(encoding="utf-8").replace(host_token, host).replace("__IMPORT_BODY_LIMIT__", budget)
        if "__" in rendered:
            raise ValueError(f"unresolved NGINX template marker in {template.name}")
        (output_dir / output_name).write_text(rendered, encoding="utf-8")
    for name in ("common-api.conf", "tourist-api-map.conf", "admin-api-map.conf"):
        source = ROOT / "deploy/nginx" / name
        (output_dir / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the checked-in inventory is stale")
    parser.add_argument("--max-files", type=int, default=1)
    parser.add_argument("--max-file-bytes", type=int, default=50 * 1024 * 1024)
    parser.add_argument("--print-import-budget", action="store_true")
    parser.add_argument("--render-nginx", type=Path, metavar="OUTPUT_DIR")
    parser.add_argument("--tourist-host")
    parser.add_argument("--admin-host")
    args = parser.parse_args()
    if args.print_import_budget:
        print(f"{import_budget_mib(args.max_files, args.max_file_bytes)}m")
    expected = build_surface()
    encoded = json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != encoded:
            print("API surface is stale; run python scripts/render_api_policy.py")
            return 1
        for site in ("tourist", "admin"):
            map_path = ROOT / "deploy" / "nginx" / f"{site}-api-map.conf"
            if not map_path.is_file() or map_path.read_text(encoding="utf-8") != render_site_map(expected, site):
                print(f"{site} API map is stale; run python scripts/render_api_policy.py")
                return 1
    else:
        OUT.write_text(encoded, encoding="utf-8")
        for site in ("tourist", "admin"):
            map_path = ROOT / "deploy" / "nginx" / f"{site}-api-map.conf"
            map_path.write_text(render_site_map(expected, site), encoding="utf-8")
        print(f"Wrote {OUT.relative_to(ROOT)} ({len(expected['routes'])} routes)")
    if args.render_nginx:
        if not args.tourist_host or not args.admin_host:
            parser.error("--render-nginx requires --tourist-host and --admin-host")
        render_nginx(args.render_nginx, args.tourist_host, args.admin_host, args.max_files, args.max_file_bytes)
        print(f"Rendered NGINX site configs to {args.render_nginx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
