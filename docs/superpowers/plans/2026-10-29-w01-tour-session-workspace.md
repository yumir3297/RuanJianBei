# W01 游客游览任务与成果基础实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让匿名游客在同一浏览器创建、保存、恢复和删除持久游览任务，为 V01 行程编辑提供安全的数据基础。

**Architecture:** FastAPI 通过 HttpOnly Cookie 识别随机匿名身份，数据库仅保存凭据摘要；SQLAlchemy 保存任务、不可变行程修订和持久幂等结果。游客 API 每次按身份过滤任务，前端在现有路线工具内提供轻量“我的游览”操作。

**Tech Stack:** Vue 3、Pinia、Axios、FastAPI、Pydantic、SQLAlchemy async、Alembic、pytest、Node test runner。

**Spec:** `docs/superpowers/specs/2026-10-29-tour-session-workspace-design.md`

## Global Constraints

- 不把 `visitor_id`、`session_id` 或任务 ID 当作权限凭据。
- Cookie 为 HttpOnly、SameSite=Lax；HTTPS 时启用 Secure；数据库只存凭据摘要。
- 写请求要求 Origin 同源，并验证 `X-CSRF-Token` 等于 `tour_csrf` Cookie；CSRF token 以现有服务端签名密钥签发并绑定身份，Cookie 限定 `Path=/api`，bootstrap JSON 返回 token 给前端内存保存。
- 游客数据不进入 RAG、管理员私人数据查询或其他游客列表。
- 游览修订不可变；保存必须校验 `expected_version` 并原子递增。
- 30 天软删除期；历史版本恢复创建新修订。
- 未经确认的游客景点名称必须保留原文且标记未解析，不猜测稳定 ID。

## Review Focus

- Cookie/CSRF/Origin：跨站请求不得创建、读取或变更游客任务；归属测试覆盖匿名身份隔离。
- 数据库事务：并发修订只能有一个版本胜出，失败不留下孤立修订。
- 幂等持久化：提交后客户端超时再重试不创建重复任务或修订；同键异内容返回 409；响应记录保留 7 天。
- 删除边界：30 天到期后不能恢复；永久删除清理全部关联修订。
- 客户端恢复：保存失败时不显示“已保存”，刷新只恢复服务端确认过的版本。

---

## 文件结构

- Create `backend/app/models/tour_session.py` — 匿名身份、游览任务、修订、成果引用与幂等记录模型。
- Modify `backend/app/models/__init__.py`, `backend/alembic/env.py` — 注册模型。
- Create `backend/alembic/versions/<revision>_add_tour_sessions.py` — 身份与任务表迁移、索引和外键。
- Create `backend/app/schemas/tour_session.py` — 请求、响应及修订快照 schema。
- Create `backend/app/repositories/tour_session.py` — 事务、所有权查询、修订、软删除及幂等持久化。
- Create `backend/app/services/tour_session_identity.py` — Cookie 凭据生成/摘要、身份取得、CSRF 与同源校验。
- Create `backend/app/api/tour_sessions.py` — 创建身份及游客任务 API。
- Modify `backend/app/api/router.py`, `backend/main.py` — 注册路由及必要生命周期配置。
- Create `backend/app/tests/test_tour_session_identity.py`, `backend/app/tests/test_tour_session_api.py`, `backend/app/tests/test_tour_session_repository.py` — 安全、事务和业务行为测试。
- Create `frontend/src/api/tourSessions.js` — 游客任务 API 客户端。
- Create `frontend/src/stores/tourSessions.js` — 当前任务、列表和保存状态。
- Modify `frontend/src/views/tourist/RouteView.vue` — “我的游览”入口和任务列表/恢复操作。
- Modify `frontend/src/assets/guide-tools.css` — 轻量任务面板样式。
- Create `frontend/tests/tour-sessions.test.mjs` — 请求与保存状态行为测试。
- Modify `docs/plans/2026-10-28-ai-workbench-backlog.md`, `docs/REPO_MAP.md`, `docs/ARCHITECTURE.md`, `docs/COMPATIBILITY.md` — 状态、链路、接口与浏览器限制同步。

## Tasks

### Task 1: 持久化模型、迁移与事务 repository

**Files:**
- Create models, migration and repository listed above.
- Test `backend/app/tests/test_tour_session_repository.py`.

**Interfaces:**
- Produces `TourSessionRepository.create_session(owner_id, site_id, title, payload, idempotency_key)`.
- Produces `TourSessionRepository.save_revision(owner_id, session_id, expected_version, payload, idempotency_key)`.
- Produces list/get/restore/delete/undelete/purge methods, all requiring `owner_id`.

- [ ] Write tests for create, immutable revision, expected-version conflict, idempotent replay and same-key/different-payload conflict.
- [ ] Run the focused repository tests and confirm the missing model/repository failures.
- [ ] Implement models and repository with one transaction per write and unique `(owner_id, endpoint, idempotency_key)`.
- [ ] Write tests for soft delete, restore within 30 days, expiry and permanent purge of revisions.
- [ ] Run repository tests and Alembic upgrade/downgrade/upgrade against isolated SQLite.

### Task 2: Anonymous identity and request protections

**Files:**
- Create `backend/app/services/tour_session_identity.py`.
- Create `backend/app/tests/test_tour_session_identity.py`.
- Modify configuration only if a named same-origin deployment setting is required.

**Interfaces:**
- `get_or_create_tour_identity(request, response, db) -> TourIdentity`.
- `require_tour_write_protection(request, identity) -> None`.

- [ ] Test random HttpOnly identity cookie issuance, digest-only persistence, identity reuse and cookie clearing behavior.
- [ ] Test same-origin Origin and signed double-submit CSRF acceptance; missing/cross-origin Origin or mismatched cookie/header rejection.
- [ ] Implement 365-day identity cookie with SameSite=Lax, HttpOnly and Secure when request is HTTPS; set a signed identity-bound `tour_csrf` cookie with SameSite=Lax, Path=/api, Secure when HTTPS and readable by the frontend.
- [ ] Run identity tests and confirm no bearer/admin auth grants private session access.

### Task 3: Owner-scoped API and persistent idempotency

**Files:**
- Create schema, API and `backend/app/tests/test_tour_session_api.py`.
- Modify `backend/app/api/router.py` and app setup as necessary.

**Interfaces:**
- `GET /api/tour-sessions` — list active tasks for cookie identity.
- `POST /api/tour-sessions` — create task; requires `Idempotency-Key` and CSRF.
- `GET /api/tour-sessions/{session_id}` — read current task and revision.
- `PUT /api/tour-sessions/{session_id}` — save snapshot with `expected_version` and `Idempotency-Key`.
- `POST /api/tour-sessions/{session_id}/restore/{revision}` — create a new revision from an old one.
- `DELETE /api/tour-sessions/{session_id}` — soft delete with expected version.
- `GET /api/tour-sessions/trash` — list recoverable tasks.
- `POST /api/tour-sessions/{session_id}/undelete` and `DELETE /api/tour-sessions/{session_id}/purge` — recover/permanently delete.

Register static `/trash` before dynamic `/{session_id}` routes so the path resolves deterministically.

- [ ] Test cross-owner reads and mutations return indistinguishable 404s; test admin token does not bypass ownership.
- [ ] Test expected-version conflicts return 409 with current version metadata.
- [ ] Test idempotent replay, changed payload conflict and deletion racing with stale saves.
- [ ] Implement endpoints with owner filtering on every repository call and bounded Pydantic fields.
- [ ] Run API tests using isolated database and verify migration-created tables.

### Task 4: Frontend task list, save and recovery states

**Files:**
- Create API and Pinia store listed above.
- Modify RouteView and CSS; create frontend test.

**Interfaces:**
- `useTourSessionsStore`: `loadList`, `create`, `open`, `save`, `remove`, `loadTrash`, `restoreDeleted`, `restoreRevision`, `purge`.
- Store exposes `items`, `current`, `saveState` (`idle|saving|saved|error|conflict`) and `error`.

- [ ] Test request headers include CSRF and per-operation idempotency keys; verify retry reuses a key only for the exact same payload, and expired idempotency results are no longer replayed after 7 days.
- [ ] Test state transitions retain edited data after network error and mark saved only after server success.
- [ ] Implement a compact “我的游览” panel inside route tool with create, open, save, trash, restore and confirmed purge.
- [ ] Show 409 conflict with server version details while retaining local edits; do not silently replace current draft.
- [ ] Run frontend tests and production build; inspect desktop and narrow viewport layout in browser.

### Task 5: Repository map and acceptance record

**Files:**
- Modify backlog, repo map, architecture and compatibility docs.

- [ ] Record W01 scope completion only for verified items; keep cross-device identity and real-device acceptance open.
- [ ] Add model/API/UI/test paths and ownership/security behavior to repository map and architecture.
- [ ] Record supported same-origin deployment, cookie restrictions, deletion behavior and manual verification gaps.
- [ ] Run `python3 scripts/check_repo_map.py`, backend focused/full tests, frontend tests/build and `git diff --check`.

## Execution

Use inline execution by the current implementer, in an isolated feature worktree based on the current authorized project state. Keep the pre-existing shared working-tree changes intact and include them only as needed after checking their latest state; do not commit unrelated changes.
