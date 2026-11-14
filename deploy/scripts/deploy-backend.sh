#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: deploy-backend.sh --confirm-maintenance-window --compose-file FILE --env-file FILE \
  --w02-drained --candidate-release FILE --current-backend-release FILE \
  --frontend-release FILE --frontend-release FILE --state-root DIR --backup-dir DIR --lock-file FILE
This script performs a controlled stop, PostgreSQL snapshot, state archive, one-shot migration,
initialize, and restart. It leaves services stopped if any migration/restore prerequisite fails.
EOF
  exit 2
}

confirm=0; w02_drained=0; compose_file=""; env_file=""; candidate=""; current_backend_release=""; state_root=""; backup_dir=""; lock_file=""; frontend_releases=()
while (($#)); do
  case "$1" in
    --confirm-maintenance-window) confirm=1; shift ;;
    --w02-drained) w02_drained=1; shift ;;
    --compose-file) compose_file="${2:?}"; shift 2 ;;
    --env-file) env_file="${2:?}"; shift 2 ;;
    --candidate-release) candidate="${2:?}"; shift 2 ;;
    --current-backend-release) current_backend_release="${2:?}"; shift 2 ;;
    --lock-file) lock_file="${2:?}"; shift 2 ;;
    --frontend-release) frontend_releases+=("${2:?}"); shift 2 ;;
    --state-root) state_root="${2:?}"; shift 2 ;;
    --backup-dir) backup_dir="${2:?}"; shift 2 ;;
    *) usage ;;
  esac
done
(( confirm == 1 && w02_drained == 1 )) && [[ -f "$compose_file" && -f "$env_file" && -f "$candidate" && -n "$current_backend_release" && -d "$state_root" && ${#frontend_releases[@]} -gt 0 && -n "$backup_dir" && -n "$lock_file" && -n "${DATABASE_URL:-}" ]] || usage
[[ "$state_root" == /* && "$backup_dir" == /* && "$lock_file" == /* ]] || { echo "state-root, backup-dir and lock-file must be absolute paths" >&2; exit 2; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 2; }
command -v pg_dump >/dev/null || { echo "pg_dump is required" >&2; exit 2; }
command -v flock >/dev/null || { echo "flock is required to serialize deployments" >&2; exit 2; }
pg_dump --version >/dev/null
python3 -c 'from urllib.parse import urlsplit; import os,sys; p=urlsplit(os.environ["DATABASE_URL"]); sys.exit(0 if p.scheme in ("postgres","postgresql","postgresql+asyncpg") and p.hostname and p.path.strip("/") else 1)' || { echo "DATABASE_URL must be PostgreSQL" >&2; exit 2; }
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
checker=(python3 "$repo_root/scripts/check_release_compatibility.py" backend --candidate "$candidate")
for release in "${frontend_releases[@]}"; do checker+=(--frontend "$release"); done
"${checker[@]}"
compose=(docker compose --env-file "$env_file" -f "$compose_file")
mkdir -p "$(dirname "$lock_file")"
exec 9>"$lock_file"
flock -n 9 || { echo "another publish/deployment operation holds $lock_file" >&2; exit 2; }
maintenance_active=0
cleanup_on_failure() {
  local status=$?
  if (( status != 0 && maintenance_active == 1 )); then
    "${compose[@]}" stop --timeout 60 gateway api tool-worker >/dev/null 2>&1 || true
  fi
  return "$status"
}
trap cleanup_on_failure EXIT
# Resolve the exact candidate image and compare its local immutable ID before the maintenance window.
"${compose[@]}" build api
# `config --images` follows service declaration order (gateway comes first here).
# Read the image from the named API service so we never compare the NGINX image by accident.
image="$("${compose[@]}" config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["api"]["image"])')"
[[ -n "$image" ]] || { echo "resolved API image is empty" >&2; exit 2; }
image_id="$(docker image inspect --format '{{.Id}}' "$image")"
image_source_sha="$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$image")"
expected_digest="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["image_digest"])' "$candidate")"
expected_source_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["source_sha"])' "$candidate")"
[[ "$image_id" == "$expected_digest" ]] || { echo "candidate image ID does not match compatibility metadata" >&2; exit 2; }
[[ "$image_source_sha" == "$expected_source_sha" ]] || { echo "candidate image source label does not match compatibility metadata" >&2; exit 2; }
mkdir -p "$backup_dir"
state_root="$(cd "$state_root" && pwd -P)"
backup_dir="$(cd "$backup_dir" && pwd -P)"
case "$backup_dir/" in "$state_root/"*) echo "backup-dir must not be inside app-state-root" >&2; exit 2;; esac
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
snapshot="$backup_dir/database-$stamp.dump"
archive="$backup_dir/state-$stamp.tar.gz"
[[ ! -e "$snapshot" && ! -e "$archive" ]] || { echo "backup output collision" >&2; exit 2; }

maintenance_active=1
"${compose[@]}" stop --timeout 60 gateway api tool-worker
if [[ -n $("${compose[@]}" ps --status running -q gateway api tool-worker) ]]; then
  echo "old gateway/API/W02 processes are still running" >&2; exit 2
fi
python3 "$repo_root/deploy/scripts/dump_postgres.py" --output "$snapshot"
"$repo_root/deploy/scripts/backup-state.sh" --quiesced --database-snapshot "$snapshot" \
  --state "app-state=$state_root" --output "$archive"
"${compose[@]}" run --rm migrate
"${compose[@]}" run --rm initialize
expected_head="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["schema_head"])' "$candidate")"
preflight_head="$("${compose[@]}" run --rm migrate python -m app.cli.deployment check-schema)"
[[ "$preflight_head" == "$expected_head" ]] || { echo "migrated database schema head does not match candidate metadata" >&2; exit 2; }
"${compose[@]}" up -d api tool-worker
# Start the gateway only after the new API passes its process health check.
for attempt in {1..36}; do
  if "${compose[@]}" exec -T api python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)' >/dev/null 2>&1; then break; fi
  sleep 5
done
"${compose[@]}" exec -T api python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)'
# Do not reopen public traffic unless the live database is exactly at the candidate schema head.
actual_head="$("${compose[@]}" exec -T api python -m app.cli.deployment check-schema)"
[[ "$actual_head" == "$expected_head" ]] || { echo "live database schema head does not match candidate metadata" >&2; exit 2; }
# Minimal live contract check before public traffic is restored.
"${compose[@]}" exec -T api python -c 'import json,urllib.request; x=json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/visitor-config", timeout=5)); assert "avatar" in x and "display" in x'
"${compose[@]}" exec -T api python -c '
import urllib.error
import urllib.request

request = urllib.request.Request("http://127.0.0.1:8000/api/admin/runtime-limits")
try:
    urllib.request.urlopen(request, timeout=5)
except urllib.error.HTTPError as error:
    assert error.code in (401, 403)
else:
    raise AssertionError("admin endpoint was public")
'
"${compose[@]}" up -d gateway
"${compose[@]}" exec -T gateway nginx -t
current_parent="$(dirname "$current_backend_release")"
mkdir -p "$current_parent"
current_temp="$current_parent/.backend-release.$$.tmp"
cp "$candidate" "$current_temp"
mv -f "$current_temp" "$current_backend_release"
maintenance_active=0
printf 'Backend release verified and current metadata promoted. Backup: %s\n' "$archive"
