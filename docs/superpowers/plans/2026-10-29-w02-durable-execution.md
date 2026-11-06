# W02 Durable Execution Implementation Plan

> **For agentic workers:** This plan implements the first W02 deliverable: a persistent execution kernel that can be safely integrated with feature-owned operations. It does not claim that itinerary generation, publication, or narration has been made resumable.

**Goal:** Add database-backed tool execution records, atomic job claiming, fenced leases, retry/cancel rules, and a separately run worker so approved product workflows can recover without duplicate business writes.

**Architecture:** Keep domain job and step state in SQLAlchemy models, add all transitions through a repository, and execute only registered typed handlers in a separate worker process. Feature adapters retain proposal/apply/publish ownership. API process startup does not silently start a second worker.

**Tech Stack:** FastAPI, async SQLAlchemy 2.x, Alembic, Pydantic 2, existing PostgreSQL and SQLite support. No new queue or workflow dependency.

**Spec:** `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md`

## Global Constraints

- Preserve feature ownership: W01 owns the tour, V01 owns itinerary proposal/apply, K01 owns publication, and W02 owns execution bookkeeping.
- Preserve V01's current process-crash behavior until a separate design changes it.
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
- [ ] Add the Alembic revision after the actual current migration heads; do not assume the repository has one head until checked.
- [ ] Import every model through `app.models` and Alembic `target_metadata`.
- [ ] Apply and downgrade the migration against isolated SQLite; inspect generated indexes and foreign keys.

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
- [ ] Implement short transactions; for PostgreSQL claim with `FOR UPDATE SKIP LOCKED`, then increment the fence and commit before running the handler.
- [ ] Implement SQLite's single-worker conditional-update path with bounded busy handling; never hold a write transaction during handler execution.
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
- [ ] Implement registry validation and one-job runner using per-handler timeout and retry rules; unknown external outcome maps to `waiting_user`.
- [ ] Add a pure handler test that terminates a runner after its claim, starts a second runner, and verifies only the current fence can persist completion.
- [ ] Re-run runner tests and the required backend suite.

### Task 4: Expose authorized execution status and command operations

**Files:**
- Create: `backend/app/api/tool_execution.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/app/tests/test_tool_execution_api.py`

**Interfaces:**
- `GET /api/tool-jobs/{job_id}` returns the caller's job snapshot after ownership checks.
- `GET /api/tool-jobs/{job_id}/events?after_seq=N` returns a bounded ordered event page; if the cursor expired, return a snapshot-required response.
- `POST /api/tool-jobs/{job_id}/cancel` and `/retry` require CSRF or existing admin authorization, an idempotency key, and a request digest.
- No generic public “execute arbitrary tool” endpoint. Creation remains a typed internal service call until a product feature registers its own authorized command.

- [ ] Write API tests for an owner reading a job, a different tour identity receiving 404, an invalid CSRF write being rejected, same-key replay, conflicting key reuse, bounded events, and cursor expiry.
- [ ] Run the new tests first and confirm the expected route/behavior is missing.
- [ ] Implement route dependencies and typed response schemas; avoid leaking raw input, provider error bodies, or result internals.
- [ ] Re-run API tests and update `docs/REPO_MAP.md` and `docs/ARCHITECTURE.md` with actual routes and limits.

### Task 5: Record safe integration boundary and operator visibility

**Files:**
- Modify: `docs/plans/2026-10-28-ai-workbench-backlog.md`
- Modify: `docs/selling-points/w02-continuous-tour-recovery.md`
- Modify: `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md`
- Create: `docs/superpowers/plans/2026-10-29-w02-execution-ledger.md`

- [ ] Document that the kernel is not an end-to-end durable tourist workflow until one registered production feature uses it.
- [ ] Keep K01's publication dispatcher and transaction as the owner of publication; add a projection adapter only after its actual job contract is available.
- [ ] Keep V01 proposals on their approved failure semantics; add query/conflict visibility without changing proposal execution semantics.
- [ ] Record one database restart/fencing example, retries and ambiguous provider outcomes in the evidence plan.
- [ ] Check all changed links and `git diff --check`; report any PostgreSQL or real-device behavior not actually exercised.

## Integration Ledger

| Producer | Consumer | Contract to verify before implementation |
|---|---|---|
| W01 session identity and revision | Tool job owner/target authorization | Must use the stable identity and owner ID from the actual W01 worktree; never infer owner from browser session ID |
| ToolExecutionRepository | ToolRunner | Every mutating method takes `worker_id + fence`; a false result means the lease was lost and must stop the handler |
| ToolRegistry | ToolRunner | Tool name and code version must match exactly; no fallback to current handler |
| ToolJob | API event page | API rechecks authorization for every request and returns bounded summaries only |

## Scope notes

The first milestone ships the persistent engine and authorized query/control surface. End-to-end recovery for narration, itinerary proposals, file import, or publication requires a separate feature adapter and domain-specific design/approval. This plan does not mark those flows complete.
