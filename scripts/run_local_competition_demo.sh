#!/usr/bin/env bash
set -Eeuo pipefail

# Full local competition smoke. It writes only to a temporary SQLite/Chroma
# directory and uses explicitly synthetic providers. It is an acceptance
# runner, not a production deployment script.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${DEMO_PYTHON:-$ROOT_DIR/backend/.venv/bin/python}"
CHROME="${PLAYWRIGHT_EXECUTABLE_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
if [[ "${DEMO_SYNTHETIC_CONFIRM:-}" != 1 || -z "${DEMO_ADMIN_PASSWORD:-}" ]]; then
  echo 'Set DEMO_SYNTHETIC_CONFIRM=1 and DEMO_ADMIN_PASSWORD for an isolated demo.' >&2
  exit 2
fi
[[ -x "$PYTHON" ]] || { echo "Python not executable: $PYTHON" >&2; exit 2; }
[[ -x "$CHROME" ]] || { echo "Chrome not executable: $CHROME" >&2; exit 2; }
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 2; }

DEMO_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/a5-competition-demo.XXXXXX")"
PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
  rm -rf "$DEMO_WORK_DIR"
}
trap cleanup EXIT INT TERM

export PYTHONPATH="$ROOT_DIR/backend"
export DATABASE_URL="sqlite+aiosqlite:///$DEMO_WORK_DIR/demo.sqlite"
export APP_ENV=test SITE_ID=demo ENABLE_SAMPLE_DATA=false
export AUTO_MIGRATE_ON_STARTUP=false BOOTSTRAP_ON_STARTUP=true
export ADMIN_PASSWORD="$DEMO_ADMIN_PASSWORD" ADMIN_TOKEN_SECRET=isolated-demo-secret
export CASS_ENABLED=true CASS_DEMO_ENABLED=true GUIDE_LOOP_PILOT_ENABLED=true GUIDE_LOOP_VISITOR_ENABLED=true
export TTS_PROVIDER=stub ASR_PROVIDER=stub
export LLM_PROVIDER=demo_synthetic LLM_API_KEY=synthetic LLM_MODEL=synthetic
export LLM_BASE_URL=http://127.0.0.1:18765/v1
export EMBEDDING_MODEL_NAME=simple-dev-embedder RERANKER_MODEL_NAME=no-model
export GUIDEMATCH_ENABLED=true
export GUIDEMATCH_MODEL_DIR="${GUIDEMATCH_MODEL_DIR:-$ROOT_DIR/.cache/guidematch/seed13}"
export GUIDEMATCH_DEVICE="${GUIDEMATCH_DEVICE:-cpu}"
export CHROMA_PERSIST_DIR="$DEMO_WORK_DIR/chroma"
export KNOWLEDGE_UPLOAD_DIR="$DEMO_WORK_DIR/knowledge"
export UI_ASSET_UPLOAD_DIR="$DEMO_WORK_DIR/ui"
export UI_ASSET_MANIFEST_PATH="$DEMO_WORK_DIR/display-assets.json"
export DEMO_BASE_URL=http://127.0.0.1:8000
export DEMO_ADMIN_URL=http://127.0.0.1:5174
export DEMO_TOURIST_URL=http://127.0.0.1:5173
export PLAYWRIGHT_EXECUTABLE_PATH="$CHROME"
export VITE_GUIDE_LOOP_PILOT=1

cd "$ROOT_DIR"
"$PYTHON" -c 'import os; from app.services.qa.guidematch_gate import GuideMatchGate; g = GuideMatchGate(os.environ["GUIDEMATCH_MODEL_DIR"], os.environ["GUIDEMATCH_DEVICE"]); assert g.decide("大佛在哪里", "大佛在哪里") in {"reuse", "distinct", "clarify"}; print("GuideMatch model preflight: PASS")'
"$PYTHON" -m app.cli.deployment migrate
"$PYTHON" -m app.cli.deployment initialize

DEMO_SYNTHETIC_CONFIRM=1 "$PYTHON" backend/scripts_local_demo_itinerary_provider.py >"$DEMO_WORK_DIR/synthetic-provider.log" 2>&1 &
PIDS+=("$!")
PYTHONPATH="$ROOT_DIR/backend" "$PYTHON" -m uvicorn main:app --host 127.0.0.1 --port 8000 >"$DEMO_WORK_DIR/backend.log" 2>&1 &
PIDS+=("$!")
PYTHONPATH="$ROOT_DIR/backend" "$PYTHON" -m app.services.tool_execution.worker --poll-seconds 0.2 >"$DEMO_WORK_DIR/tool-worker.log" 2>&1 &
PIDS+=("$!")

(cd "$ROOT_DIR/frontend" && npm run dev:admin -- --host 127.0.0.1 --port 5174 --strictPort >"$DEMO_WORK_DIR/admin-vite.log" 2>&1) &
PIDS+=("$!")
(cd "$ROOT_DIR/frontend" && npm run dev:tourist -- --host 127.0.0.1 --port 5173 --strictPort >"$DEMO_WORK_DIR/tourist-vite.log" 2>&1) &
PIDS+=("$!")

for attempt in $(seq 1 60); do
  if curl -fsS --max-time 1 http://127.0.0.1:8000/health >/dev/null \
    && curl -fsS --max-time 1 http://127.0.0.1:5173/ >/dev/null \
    && curl -fsS --max-time 1 http://127.0.0.1:5174/ >/dev/null; then
    break
  fi
  [[ "$attempt" == 60 ]] && { echo "Services did not become ready; logs: $DEMO_WORK_DIR" >&2; exit 1; }
  sleep 1
done

cd "$ROOT_DIR/frontend"
node tests/e2e/knowledge-publish-tourist-smoke.mjs
node tests/e2e/itinerary-real-service-smoke.mjs
node tests/e2e/local-demo-smoke.mjs
node tests/e2e/guide-loop-binding-smoke.mjs
(npm run build:tourist >/dev/null)
export OFFLINE_EVIDENCE_DIR="$DEMO_WORK_DIR/offline-evidence"
node tests/e2e/offline.e2e.mjs
echo 'FULL LOCAL COMPETITION DEMO: PASS (synthetic local data/providers)'
