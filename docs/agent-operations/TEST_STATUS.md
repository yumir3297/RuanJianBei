# Test and validation status

Updated: 2026-11-07. Results below were executed in the isolated worktree; these are local automation results, not production/device claims.

## Environment

- macOS Apple Silicon host; Node `v24.11.0`, npm `11.6.1`.
- Python test interpreter: existing repository venv at `backend/.venv`, Python `3.13.16` (reused read-only as an interpreter; `pytest-asyncio==1.4.1` was installed there after the first collection attempt).
- Frontend dependencies installed from the checked-in lockfile with `npm ci --ignore-scripts --offline`.
- Provider calls use the existing test doubles; no real provider credentials were read or used.

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
| `npm test` | PASS | Final full frontend suite: 164 passed, 0 failed. |
| `npm run build` | PASS WITH WARNING | Vite production build succeeded. Several chunks exceed 500 kB; largest is about 1.04 MB minified. |
| `python -m pytest app/tests -q` | PASS | Final serialized run: 671 passed, 19 skipped, 8 warnings. An earlier parallel run with a separate migration pytest process timed out while both used test DB resources; serialized rerun completed in 12.54s. |
| Migration check | PASS | `alembic heads`: one head `91a0c5e2f347`; selected SQLite migration/recovery tests: 7 passed (synthetic SQLite only). |
| Map checker + scripts tests after current map/docs edits | PASS | Checker: 8 documents/84 routes; scripts unittest: 11 passed. |
| Independent reviewer | PASS | Two read-only review passes. Correctness issues and the handoff/test-status mismatch were fixed; final review found no remaining P0/P1. |

## Not run / blocked by external conditions

- iOS Safari, WeChat iOS/Android, Android browser, tablets, touch/soft-keyboard, screen reader and real-device audio/GPS: **NOT RUN**.
- Real LLM, vision, ASR, TTS providers: **NOT RUN**; no provider secrets were used.
- PostgreSQL deployed-schema and true multi-process claim/progress race: **NOT RUN**. SQLite tests do not prove PostgreSQL behavior or upgrade safety for an existing production database.
- Verified scenic map, current crowd feed, emergency contact/dispatch: **NOT AVAILABLE / NOT VERIFIED**. Do not enable placeholder data as official.
- Full offline install/Service Worker on actual target devices: **NOT RUN**. The historical offline branch remains separate.
