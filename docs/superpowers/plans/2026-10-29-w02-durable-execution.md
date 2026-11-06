# W02 Durable Execution Implementation Plan

> **For agentic workers:** This plan now includes the first feature adapter: V01 itinerary proposal generation. Publication and narration remain outside W02 until their domain contracts are designed.

**Goal:** Add database-backed tool execution records, atomic job claiming, fenced leases, retry/cancel rules, and a separately run worker so approved product workflows can recover without duplicate business writes.

**Architecture:** Keep domain job and step state in SQLAlchemy models, add all transitions through a repository, and execute only registered typed handlers in a separate worker process. Feature adapters retain proposal/apply/publish ownership. API process startup does not silently start a second worker.

**Tech Stack:** FastAPI, async SQLAlchemy 2.x, Alembic, Pydantic 2, existing PostgreSQL and SQLite support. No new queue or workflow dependency.

**Current status:** Kernel and the V01 itinerary proposal adapter/UI source are implemented in an isolated integration branch. The feature-owned V01 route creates typed W02 jobs; no generic arbitrary-tool create route exists. SQLite migration upgrade/downgrade, a 36-test targeted V01/W02 regression set, and frontend production build have passed. Full backend coverage, runtime fault recovery, PostgreSQL multi-worker behavior and real-browser verification remain outstanding.

**Spec:** `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md`

## Global Constraints

- Preserve feature ownership: W01 owns the tour, V01 owns itinerary proposal/apply, K01 owns publication, and W02 owns execution bookkeeping.
- W02 owns only the execution phase of V01 itinerary proposals. V01 remains owner of proposal content, explicit apply and progress rules; K01 remains owner of publication.
- SQLite reviewer deployment runs one worker; production multi-worker claims must use PostgreSQL row locking and fencing.
- Retry only operations explicitly marked safe. Uncertain external outcomes become `waiting_user` and are never blindly retried.
- Job completion creates or records a candidate; it does not confirm a tour change or publish knowledge.
- Check actor and target ownership on every read and write. Job IDs are not credentials.
- Do not persist full chat histories, photos, audio, provider credentials, or model reasoning in job events.
- Feature compatibility requires a matching handler version; unknown handlers fail visibly.

## Review Focus

- A duplicate create request races across processes — one job and one stable command receipt must result.
- A worker completes after losing its lease — the old fence must prevent every status, event, step, or result write.
- A worker crashes after an external call may have succeeded — the operation must pause for reconciliation or a user decision.
- Cancel races with successful completion — the committed database transition decides; cancellation cannot undo an already committed domain change.
- SQLite is tested as a single-worker development backend and must not be represented as proof of PostgreSQL multi-worker behavior.

---

### Task 1: Persist job, step, attempt, event, and command receipt records

**Files:**
- Create: `backend/app/models/tool_execution.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/<new>_add_tool_execution.py`
- Test: `backend/app/tests/test_tool_execution_models.py`

**Interfaces:**
- Produces model tables `tool_jobs`, `tool_steps`, `tool_attempts`, `tool_events`, and `tool_command_receipts` with the uniqueness constraints in the spec §4.
- `ToolJob` includes target/input digests, tool and workflow schema versions, status, next-run time, lease owner/until/fence, creation/update times.
- `ToolStep` has one logical row per `(job_id, step_key)` and stores only the structured result or bounded result reference required by the registered handler.

- [ ] Add model tests for unique job command receipts, unique step keys, monotonic event sequence, and cascade ownership.
- [ ] Run the focused model test; confirm duplicate constraints fail with an integrity error.
- [x] Add the Alembic revision after the V01 migration `5c81a1e74f2b`, which follows the prior repository head.
- [x] Import every model through `app.models` and Alembic `target_metadata`.
- [x] Apply and downgrade the migration against isolated SQLite; inspect generated indexes and foreign keys.

### Task 2: Add transactional repository commands and lease fencing

**Files:**
- Create: `backend/app/repositories/tool_execution.py`
- Create: `backend/app/schemas/tool_execution.py`
- Test: `backend/app/tests/test_tool_execution_repository.py`

**Interfaces:**
- `ToolExecutionRepository.create_job(principal_type, principal_id, tool_name, tool_version, workflow_schema_version, target, payload, idempotency_key) -> JobView`
- `ToolExecutionRepository.claim_next(worker_id, now, lease_seconds) -> JobLease | None`
- `ToolExecutionRepository.heartbeat(job_id, worker_id, fence, lease_until) -> bool`
- `ToolExecutionRepository.complete_step(job_id, worker_id, fence, step_key, result, event) -> bool`
- `ToolExecutionRepository.schedule_retry(job_id, worker_id, fence, step_key, error_code, next_run_at) -> bool`
- `ToolExecutionRepository.request_cancel(principal, job_id, idempotency_key) -> JobView | None`
- `ToolExecutionRepository.get_job(principal, job_id) -> JobView | None`
- All mutations match current status, lease owner and fence; create/retry/cancel receipts are bound to a canonical request digest.

- [ ] Write focused repository tests for idempotent create, same-key/different-input conflict, ownership filtering, competing claims, expired lease re-claim, stale fencing, and event cursor ordering.
- [ ] Run the repository tests before implementing and confirm each missing behavior fails for its expected reason.
- [x] Implement short transactions; for PostgreSQL claim with `FOR UPDATE SKIP LOCKED`, then increment the fence and commit before running the handler.
- [x] Implement SQLite's single-worker conditional-update path with bounded busy handling; never hold a write transaction during handler execution.
- [ ] Re-run focused tests, then the existing backend suite required for this task.

### Task 3: Execute versioned registered handlers in a separate worker

**Files:**
- Create: `backend/app/services/tool_execution/registry.py`
- Create: `backend/app/services/tool_execution/runner.py`
- Create: `backend/app/services/tool_execution/worker.py`
- Modify: `backend/main.py` only if needed for explicit worker bootstrap/close helpers; API startup must not run the worker loop.
- Test: `backend/app/tests/test_tool_execution_runner.py`

**Interfaces:**
- `ToolHandler` declares `name`, `version`, `input_model`, `output_model`, retry policy and recovery mode.
- `ToolRegistry.register(handler)` rejects duplicate `(name, version)` registrations.
- `ToolRunner.run_one(worker_id) -> bool` claims at most one job, validates handler/version/input, stores step outcome and event through the repository, and conditionally commits by fence.
- Provide a documented command `python -m app.services.tool_execution.worker` for a separate worker process; shutdown stops new claims and lets the current handler finish or expire its lease.

- [ ] Write tests using a small registered pure handler for success, malformed input, incompatible handler version, idempotent step-result reuse, lease loss, bounded retry and cancellation.
- [ ] Run them before the runner exists and observe expected failures.
- [x] Implement registry validation and one-job runner using per-handler timeout and retry rules; unknown external outcome maps to `waiting_user`.
- [ ] Add a pure handler test that terminates a runner after its claim, starts a second runner, and verifies only the current fence can persist completion.
- [ ] Re-run runner tests and the required backend suite.

### Task 4: Expose authorized execution status and command operations

**Files:**
- Create: `backend/app/api/tool_execution.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/app/tests/test_tool_execution_api.py`

**Interfaces:**
- `GET /api/tour-sessions/{session_id}/executions/{job_id}` returns the caller's job snapshot after W01 identity, site and session ownership checks.
- `GET .../executions/{job_id}/events?after_seq=N` returns a bounded ordered event page and a snapshot-required flag if event pruning has ever made the cursor incomplete.
- `POST .../executions/{job_id}/cancel` and `/retry` require W01 CSRF, an idempotency key and a request digest.
- No generic public “execute arbitrary tool” endpoint. V01's feature-owned proposal route validates its business command and calls the typed internal enqueue command.

- [ ] Write API tests for an owner reading a job, a different tour identity receiving 404, an invalid CSRF write being rejected, same-key replay, conflicting key reuse, bounded events, and cursor expiry.
- [ ] Run the new tests first and confirm the expected route/behavior is missing.
- [x] Implement route dependencies and typed response schemas; avoid leaking raw input, provider error bodies, or result internals.
- [ ] Complete the full execution API matrix. Proposal creation, same-key replay and changed-payload conflict are covered by the targeted acceptance test; broader authorization, event cursor, cancel/retry cases remain unrun.
- [x] Run `scripts/check_repo_map.py`; it passes for the registered routes and current documentation links.

### Task 5: Record safe integration boundary and operator visibility

**Files:**
- Modify: `docs/plans/2026-10-28-ai-workbench-backlog.md`
- Modify: `docs/selling-points/w02-continuous-tour-recovery.md`
- Modify: `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md`
- Create: `docs/superpowers/plans/2026-10-29-w02-execution-ledger.md`

- [x] Document the first real tourist integration (V01 itinerary proposals) and keep unverified recovery claims clearly bounded.
- [x] Keep K01's publication dispatcher and transaction as the owner of publication; add no adapter without its actual job contract.
- [x] Move only V01 proposal generation to W02; preserve explicit V01 apply and revalidation of itinerary, progress and catalog versions.
- [x] Record restart/fencing, retries and ambiguous provider outcomes as required evidence scenarios; none have been executed yet.
- [x] Run `git diff --check` and inspect untracked-file whitespace.
- [x] Run `scripts/check_repo_map.py` to validate local documentation links and registered API paths.
- [x] Report that SQLite migration and targeted tests passed; PostgreSQL multi-worker, fault injection and real-device behavior have not been exercised.

## Integration Ledger

| Producer | Consumer | Contract to verify before implementation |
|---|---|---|
| W01 session identity and revision | Tool job owner/target authorization | Must use the stable identity and owner ID from the actual W01 worktree; never infer owner from browser session ID |
| ToolExecutionRepository | ToolRunner | Every mutating method takes `worker_id + fence`; a false result means the lease was lost and must stop the handler |
| ToolRegistry | ToolRunner | Tool name and code version must match exactly; no fallback to current handler |
| ToolJob | API event page | API rechecks authorization for every request and returns bounded summaries only |
| V01 proposal reservation | W02 itinerary handler | Reservation + job enqueue share one transaction; candidate + job success share one transaction; V01 apply remains explicit |

## Scope notes

The first feature adapter covers V01 itinerary proposal generation. It does not make narration, file import, or publication resumable, and it does not mark the complete W02 backlog finished. Full fault-injection, browser-resume and PostgreSQL multi-worker evidence are still required.
