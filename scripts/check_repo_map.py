"""Read-only repository map checks. Python 3.10+, standard library only.

Understands this repository's explicit api_router.include_router registrations,
APIRouter prefixes and HTTP decorators. Never imports application code.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


DOCUMENTS = (
    "README.md", "AGENTS.md", "frontend/AGENTS.md", "backend/AGENTS.md",
    "docs/REPO_MAP.md", "docs/ARCHITECTURE.md", "docs/DEVELOPMENT.md",
    "docs/COMPATIBILITY.md",
)
METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
API = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[A-Za-z0-9_{}./-]+)")


def parse_source(root: Path, file: str) -> ast.Module:
    try:
        return ast.parse((root / file).read_text(encoding="utf-8-sig"), filename=file)
    except (SyntaxError, OSError) as exc:
        raise ValueError(f"Cannot parse {file}: {exc}") from exc


def literal(node: ast.AST | None, location: str) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    raise ValueError(f"Expected string literal at {location}")


def keyword(call: ast.Call, name: str, location: str, default: str = "") -> str:
    for item in call.keywords:
        if item.arg is None:
            raise ValueError(f"Unsupported dynamic keywords at {location}")
        if item.arg == name:
            return literal(item.value, location)
    return default


def is_call(call: ast.AST, owner: str, method: str) -> bool:
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == owner and call.func.attr == method
    )


def reject_imperative_routes(tree: ast.Module, owner: str, file: str) -> None:
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"add_api_route", "add_route"}):
            continue
        target = node.func.value
        while isinstance(target, ast.Attribute):
            target = target.value
        if isinstance(target, ast.Name) and target.id == owner:
            raise ValueError(f"Unsupported imperative route registration at {file}:{node.lineno}")


def router_prefix(tree: ast.Module, name: str, location: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            call = node.value
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "APIRouter":
                return keyword(call, "prefix", location)
    raise ValueError(f"Missing explicit APIRouter assignment: {location}:{name}")


def decorated_routes(tree: ast.Module, owner: str, prefix: str, file: str) -> list[dict]:
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == owner):
                continue
            if decorator.func.attr not in METHODS:
                raise ValueError(f"Unsupported route decorator at {file}:{node.name}")
            path = (literal(decorator.args[0], file) if decorator.args
                    else keyword(decorator, "path", file))
            if not path.startswith("/"):
                raise ValueError(f"Route path must start with / at {file}:{node.name}")
            result.append({"method": decorator.func.attr.upper(), "path": prefix + path,
                           "file": file, "handler": node.name})
    return result


def collect_routes(root: Path) -> list[dict]:
    registration = "backend/app/api/router.py"
    tree = parse_source(root, registration)
    reject_imperative_routes(tree, "api_router", registration)
    base = router_prefix(tree, "api_router", registration)
    result = []
    includes = [node for node in ast.walk(tree) if is_call(node, "api_router", "include_router")]
    if not includes:
        raise ValueError(f"No explicit router registrations in {registration}")
    for call in includes:
        target = call.args[0] if call.args else None
        if not (isinstance(target, ast.Attribute) and target.attr == "router"
                and isinstance(target.value, ast.Name)):
            raise ValueError(f"Unsupported router registration at {registration}")
        file = f"backend/app/api/{target.value.id}.py"
        module = parse_source(root, file)
        reject_imperative_routes(module, "router", file)
        if any(is_call(node, "router", "include_router") for node in ast.walk(module)):
            raise ValueError(f"Nested router registration is unsupported at {file}")
        prefix = base + keyword(call, "prefix", registration) + router_prefix(module, "router", file)
        result.extend(decorated_routes(module, "router", prefix, file))

    main_file = "backend/main.py"
    main = parse_source(root, main_file)
    reject_imperative_routes(main, "app", main_file)
    app_includes = [node for node in ast.walk(main) if is_call(node, "app", "include_router")]
    if (len(app_includes) != 1 or not app_includes[0].args
            or not isinstance(app_includes[0].args[0], ast.Name)
            or app_includes[0].args[0].id != "api_router"):
        raise ValueError("Expected a single app.include_router(api_router) in backend/main.py")
    app_prefix = keyword(app_includes[0], "prefix", main_file)
    for route in result:
        route["path"] = app_prefix + route["path"]
    result.extend(decorated_routes(main, "app", "", main_file))
    return sorted(result, key=lambda route: (route["path"], route["method"], route["file"]))


def check_local_link(root: Path, document: Path, target: str) -> str | None:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if "\\" in target or re.match(r"^[A-Za-z]:", target):
        return f"Use a repository-relative POSIX link: {target}"
    parts = urlsplit(target)
    if parts.scheme.lower() == "file":
        return f"Use a repository-relative POSIX link: {target}"
    if parts.scheme or parts.netloc or not parts.path:
        return None
    path = unquote(parts.path)
    if "\\" in path or path.startswith("/"):
        return f"Use a repository-relative POSIX link: {target}"
    destination = (document.parent / path).resolve()
    if not destination.is_relative_to(root):
        return f"Link outside repository: {target}"
    if not destination.exists():
        return f"Missing link: {target}"
    # Exact casing matters on Linux even when the author uses Windows/macOS.
    current = root
    for component in (document.parent / path).relative_to(root).parts:
        if component == "..":
            current = current.parent
        elif component != ".":
            if component not in {entry.name for entry in current.iterdir()}:
                return f"Link case mismatch: {target}"
            current = current / component
    return None


def check_documents(root: Path, routes: list[dict]) -> list[str]:
    known = {(route["method"], route["path"]) for route in routes}
    errors = []
    for file in DOCUMENTS:
        path = root / file
        if not path.is_file():
            errors.append(f"Missing map document: {file}")
            continue
        text = path.read_text(encoding="utf-8-sig")
        for target in LINK.findall(text):
            error = check_local_link(root, path, target)
            if error:
                errors.append(f"{file}: {error}")
        for method, endpoint in API.findall(text):
            if (method, endpoint) not in known:
                errors.append(f"{file}: Unknown API reference: {method} {endpoint}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="Export live route index as JSON after validation")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        routes = collect_routes(root)
        errors = check_documents(root, routes)
    except (ValueError, OSError, UnicodeError) as exc:
        errors = [str(exc)]
        routes = []
    if args.json:
        print(json.dumps({"schema_version": 1, "routes": routes, "errors": errors}, ensure_ascii=False, indent=2))
    elif errors:
        print("Repository map check FAILED:\n" + "\n".join(errors))
    else:
        print(f"Repository map OK: {len(DOCUMENTS)} documents, {len(routes)} registered HTTP routes.")
    return 1 if errors else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
