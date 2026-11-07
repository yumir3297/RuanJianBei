# Test and validation status

Updated: 2026-11-07. Results below were executed in the isolated worktree; these are local automation results, not production/device claims.

## Environment

- macOS Apple Silicon host; Node `v24.11.0`, npm `11.6.1`.
- Python test interpreter: existing repository venv at `backend/.venv`, Python `3.13.16` (reused read-only as an interpreter; `pytest-asyncio==1.4.1` was installed there after the first collection attempt).
- Frontend dependencies installed from the checked-in lockfile with `npm ci --ignore-scripts --offline`.
- Automated tests use provider test doubles. Separate minimal live DeepSeek and Volcengine TTS smoke calls were run after user configuration; no key values were printed or written to reports.

## Baseline on source SHA `7ef0459`

| Check | Result | Evidence / boundary |
|---|---|---|
| `python3 scripts/check_repo_map.py` | PASS | 8 documents, 84 registered HTTP routes |
| `python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v` | PASS | 11 tests |
| Backend first attempt: `python -m pytest app/tests -q` | ENVIRONMENT FAILURE | 49 async tests failed to run because `pytest-asyncio` was absent; 622 passed, 19 skipped. Not treated as application failures or PASS. |
| Backend retry after installing `pytest-asyncio==1.4.1`: same command | PASS | 671 passed, 19 skipped, 8 warnings in 11.57s. SQLite/Alembic tests are synthetic; 19 skips include unavailable optional/external test conditions. |
| `alembic heads` | PASS | Single head `91a0c5e2f347`; no database was migrated by this command. |
| `npm test` | PASS | 155 tests before current K01 UI recovery edits |
| `npm run build` | PASS with warning | Vite production build succeeded; several chunks exceed 500 kB (largest ~1.04 MB). |

## Current-change focused tests

| Check | Result | Evidence / boundary |
|---|---|---|
| `node --test tests/publication-recovery.test.mjs` | PASS | 13 tests cover lost response → no automatic POST on refresh → explicit same-key recovery; known job restore by GET only; storage failure blocks POST; success cleanup; rejected stale snapshot; in-flight unmount; lost retry response; job-ID persistence failure; create-success/status-404 preservation. Controller-level automation, not a real browser storage test. |
| `pytest app/tests/test_sample_scenic_knowledge_acceptance.py -q` | PASS | Repository sample `data/processed/guide_sections.json`: 22 entries imported to temporary SQLite drafts; 0 visible before publish; publication succeeded; after disposing and reopening the SQLite engine all 22 published revisions were visible and 22 chunks matched 22 deterministic fake vectors. Uploads/DB used auto-cleaned temp paths; no production DB, Chroma, or real embedding/provider was used. This verifies workflow plumbing, not scenic fact accuracy. |
| DeepSeek vision + Volcengine ASR + legacy Bailian provider contract tests | PASS | `pytest app/tests/test_deepseek_vision_service.py app/tests/test_vision_api.py app/tests/test_voice_api.py app/tests/test_asr_volcengine.py app/tests/test_asr_bailian.py -q` — 49 passed, 1 warning. WebSocket/HTTP are mocked; no provider credentials/network calls. FFmpeg WAV normalization test runs only when FFmpeg is installed. |
| Live provider smoke before the ASR provider switch | PARTIAL PASS | DeepSeek LLM runtime adapter, DeepSeek `deepseek-flash` vision, and Volcengine TTS each passed one minimal real request using local credentials; no key values were printed or saved. The standalone LLM smoke with a 32-token budget did not reach final content because `deepseek-v4-pro` used reasoning tokens; the actual configured runtime budget returned a non-fallback answer. Bailian ASR was not called because the public audio URL was absent. These calls may incur small usage charges. |
| `npm test` | PASS | Final full frontend suite: 164 passed, 0 failed. |
| `npm run build` | PASS WITH WARNING | Vite production build succeeded. Several chunks exceed 500 kB; largest is about 1.04 MB minified. |
| `python -m pytest app/tests -q` | PASS | Serialized run after Volcengine WebSocket ASR adapter and 100 ms packet pacing: 685 passed, 19 skipped, 8 warnings in 20.02s. |
| Migration check | PASS | `alembic heads`: one head `91a0c5e2f347`; selected SQLite migration/recovery tests: 7 passed (synthetic SQLite only). |
| Map checker + scripts tests after current map/docs edits | PASS | Checker: 8 documents/84 routes; scripts unittest: 11 passed. |
| Independent reviewer | PASS | Two read-only review passes. Correctness issues and the handoff/test-status mismatch were fixed; final review found no remaining P0/P1. |

## Not run / blocked by external conditions

- iOS Safari, WeChat iOS/Android, Android browser, tablets, touch/soft-keyboard, screen reader and real-device audio/GPS: **NOT RUN**.
- Real Volcengine ASR: **NOT RUN**; protocol/API contract tests are mocked. A real smoke requires a Volcengine ASR resource authorized for the configured API key. DeepSeek LLM/vision and Volcengine TTS had one minimal real smoke each as recorded above.
- PostgreSQL deployed-schema and true multi-process claim/progress race: **NOT RUN**. SQLite tests do not prove PostgreSQL behavior or upgrade safety for an existing production database.
- Verified scenic map, current crowd feed, emergency contact/dispatch: **NOT AVAILABLE / NOT VERIFIED**. Do not enable placeholder data as official.
- Full offline install/Service Worker on actual target devices: **NOT RUN**. The historical offline branch remains separate.

## GitHub delivery status

- PR #3: https://github.com/yumir3297/RuanJianBei/pull/3, targeting `codex/competition-integration`; state **OPEN** at the last check.
- GitHub reported an empty status-check rollup and `gh pr checks` reported no checks for the branch. This is not a local test failure; local verification above is the available evidence.
- GitHub's `mergeable` field was `UNKNOWN` at that time. No merge was attempted; the PR is awaiting normal review/branch analysis.
