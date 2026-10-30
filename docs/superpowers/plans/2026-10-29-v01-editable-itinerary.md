# V01 可验证的连续伴游规划实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让游客把自然语言需求变成可编辑、可持续修改、可恢复的景区行程，并在确认后记录真实游览进度。

**Architecture:** 以 W01 Cookie 身份、TourSession 和不可变修订为持久基础；结构化 `TourSnapshotV2` 表示约束、停留、证据、锁定与进度关联。后端提供确定性编辑、预算检查及带版本校验的提案/确认流程；游客端路线工具、地图与导游共享同一个已确认快照。

**Tech Stack:** Vue 3、Pinia、FastAPI、Pydantic 2、SQLAlchemy async、Alembic、现有 LLM provider 与 Node/Vite 工具链；不增加 Agent 框架或依赖。

**Spec:** `docs/superpowers/specs/2026-10-29-v01-editable-itinerary-design.md`；调研参考 `docs/research/2026-10-29-v01-itinerary-research.md`。

## Global Constraints

- W01 代码仅从独立分支 `codex/w01-tour-sessions` 的最新已验收提交引入；不覆盖其仍在进行的浏览器/验收文档。
- 基线仓库已有未提交 F01/V03 修改；在其原工作树保持不变。仅在 V01 确有直接依赖时，按路径审阅并导入所需共享播放接口。
- Cookie/CSRF、owner 过滤、写请求幂等与 expected_version 沿用 W01，任务 ID 不作为权限。
- 只从 K01 当前发布修订、未下架知识目录解析 `metadata.attraction_id` 为 spot_code；演示坐标不作权威路网或实时客流证据。
- 普通聊天 SSE 合约保持不变；规划意图只生成 allowlist 操作，服务器验证后经游客确认保存。
- 计划预算是游览总预算；开始后只检查当前和未来部分。未知路段时长不计为 0，结果标 `unverified`。
- 完成/跳过进度与行程修订分别保存；任何行程撤销不回滚实际游览事件。
- 每项只在代码/文档实现完成并具有可复核证据后更新主待办；W01 验收状态由其负责对话维护。

## Review Focus

- W01 重复重试与两个标签页并发：owner 过滤、持久幂等和版本冲突必须在新接口沿用。
- 模型返回额外字段、伪造 spot_code、过量操作或错误 JSON：拒绝/有限纠正，草稿不变。
- 游客在模型生成或确认过程中编辑草稿：draft digest 不符时拒绝提交，不能覆盖本地改动。
- 行程提案与完成/跳过并发：用进度版本及事务校验，不删改已游事实。
- 知识下架或发布版本更新：旧来源只作历史摘要，不能继续读回已下架内容。

## 文件结构

- `backend/app/schemas/itinerary.py`：版本化快照、操作、预算和进度命令的严格 schema。
- `backend/app/services/itinerary/catalog.py`：已发布景点目录及 spot_code 唯一性/别名解析。
- `backend/app/services/itinerary/mutations.py`：纯操作 reducer、diff 与硬约束校验。
- `backend/app/services/itinerary/planning.py`：预算状态、最小改动候选选择和当前/未来停留校验。
- `backend/app/services/itinerary/proposals.py`：持久提案、确认、过期、幂等及版本/摘要校验。
- `backend/app/services/itinerary/intent.py`：模型意图解析；禁止其直接写数据库。
- `backend/app/models/tour_session.py`、Alembic、repository、API：基于 W01 的任务版本增加快照兼容、提案和独立执行进度。
- `backend/app/api/itinerary.py`：目录与提案路由；`backend/app/api/tour_sessions.py` 增进度命令。
- `frontend/src/api/itinerary.js`、`frontend/src/stores/itinerary.js`：行程请求、草稿、差异与确认状态，与聊天 store 分离。
- `frontend/src/components/tour/`：约束表单、行程编辑、提案差异和进度控制。
- `frontend/src/views/tourist/RouteView.vue`：组装组件，模板选择写成当前游览草稿。
- `frontend/src/views/tourist/ChatView.vue`：只转发行程编辑意图及当前任务，不拆普通聊天流。
- `frontend/src/views/tourist/MapView.vue`：从当前确认快照绘制有坐标依据的停留点，并提供当前点讲解动作。
- `docs/REPO_MAP.md`、`docs/ARCHITECTURE.md`、`docs/plans/2026-10-28-ai-workbench-backlog.md`：实现后补功能入口及实际状态。

---

### Task 1: 建立隔离集成基线并确认 W01 合约

**Files:**
- Read: `/private/tmp/ruanjianbei-w01` 的 W01 最新提交与迁移/API/schema。
- Create: 执行时创建的 V01 隔离 worktree（从 W01 最新提交开始）。
- Modify: 无；仅选取 W01 引入提交并审阅 F01/V03 文件差异。

**Interfaces:**
- Consumes: W01 `TourSnapshot`, `TourSessionRepository.save_revision(owner_id, session_id, expected_version, payload, idempotency_key)` 及匿名身份依赖。
- Produces: 隔离的 V01 实施基线和清单：W01 最新 SHA、F01/V03 要保留的路径、迁移 head。

- [x] **Step 1: 读取 W01 当前分支最新状态**
  - 确认其执行对话已结束当前验收轮；读取 branch SHA、status、改动说明与 W01 文件清单。
  - 只读两个检出，不清理共享工作区。
- [x] **Step 2: 将已批准的 V01 设计与实施计划放入隔离分支**
  - 仅复制本任务的 research/spec/plan 文件；不覆盖 W01 的实现与验收记录。
- [x] **Step 3: 确认 W01 数据库迁移链与 API 合约**
  - W01 当前 Alembic head 为 `e9f4c2b8016a`；V01 迁移接在此后。主工作树的 `c3b7e1d9a62f` 语音迁移属于未提交 F01/V03，本 Task 不导入，未来整合时再重排。
- [x] **Step 4: 记录隔离基线 SHA、迁移 head 和延期整合的共享改动范围**

### Task 2: 版本化快照与已发布景点目录

**Files:**
- Create: `backend/app/schemas/itinerary.py`、`backend/app/services/itinerary/catalog.py`、`backend/app/services/itinerary/mutations.py`、对应 `backend/app/tests/` 用例。
- Modify: W01 tour schema、models、repository、API 与 Alembic migration；`backend/app/models/__init__.py`、`backend/app/api/router.py`。

**Interfaces:**
- Produces: `upgrade_snapshot(raw: dict) -> TourSnapshotV2`；`PublishedAttractionCatalog.list_for_site(site_id) -> CatalogSnapshot`；`parse_spot_reference(value: str, catalog: CatalogSnapshot) -> ResolvedSpot | AmbiguousSpot | UnknownSpot`。
- Produces: `apply_manual_operation(snapshot: TourSnapshotV2, operation: ItineraryOperation, catalog: CatalogSnapshot) -> MutationResult`，结果含规范快照、diff 与 `pass|conflict|unverified`。

- [x] **Step 1: 明确数据库中的已发布 revision 与 `spot_code` 来源**
  - K01 用 `KnowledgeEntry.published_revision_id` / `withdrawn_at` 控制可见性；目录 join 对应 `KnowledgeRevision` 并读取该 revision metadata。此版 K01 为单景区服务，目录 `site_id` 必须等于 `Settings.site_id`；`metadata.attraction_id` 是稳定景点码，entry id 与 revision id 单独保留。
  - V01 分支只读合入 K01 提交 `914c030` 的实现，不修改 `/Users/yumir/RuanJianBei` 原工作树；重复代码拒绝，歧义别名显式返回。
- [x] **Step 2: 定义快照 V2 schema 及升级规则**
  - 严格枚举 `visit|rest`、来源、预算依据和执行状态；最多 50 条，分钟预算 1–720。
  - 老 `TourSnapshot` 升级只创建新修订；历史 JSON 不变；无法解析的 spot 保留名称但标 unknown。
- [x] **Step 3: 写版本迁移与服务端序列化/反序列化**
  - 行程 stop 有 UUID；景点使用 spot_code，当前内容引用存 entry_id 和 published_revision_id；未解析地点不得伪造坐标。
  - 数据迁移不给来源/距离/开放状态补造证据；duration basis 为 unknown 时 duration 可空。
- [x] **Step 4: 写纯 reducer**
  - 实现 add/remove/replace/move/set-duration/add-rest/update-constraints；不接受模型写 owner、版本、lock、progress 或 resolved/source flags。
  - 按 stop_id 操作；验证锁定、排除/必去、顺序引用、重复 stop、额外字段与上限；返回确定性 diff。
- [x] **Step 5: 加可用预算和迁移防回归验证**
  - 已发布目录只返回可见条目；未知与歧义状态单独呈现。
  - W01、K01 与 V01 迁移合并到 `5c81a1e74f2b`；隔离 SQLite upgrade→downgrade base→upgrade head 已通过。正式 PostgreSQL 迁移仍需在本机/CI 确认。

### Task 3: 持久执行进度与时间预算

**Files:**
- Create: `backend/app/services/itinerary/progress.py`、执行进度 repository/schema 与相应用例。
- Modify: tour-session models、repository、API、migration；前端 API/store。

**Interfaces:**
- Produces: `start_tour(owner_id, session_id, expected_version, idempotency_key, started_at)`；`apply_progress_command(owner_id, session_id, expected_progress_version, command, idempotency_key)`。
- Progress command: `set_current(stop_id)`, `complete(stop_id)`, `skip(stop_id)`, `finish()`；所有命令追加事件并递增 progress_version。
- Produces: `validate_remaining_budget(snapshot, progress, now) -> BudgetValidation`。

- [x] **Step 1: 定义独立 TourProgress 与 append-only 进度事件**
  - 开始时记服务端 started_at 和 finish_by；progress_version 单调递增。
- [x] **Step 2: 实现原子、owner-scoped 进度命令**
  - 一个 current；只允许当前/未来合法转移；完成/跳过不可由快照保存改写；用户纠正必须有单独 correction 事件。
- [x] **Step 3: 实现剩余预算计算**
  - 草稿按全程已知停留、休息与有证据的路段；开始后排除 completed/skipped 历史，只算 current/future，与 finish_by-now 比较。
  - 当前点优先使用游客输入的剩余时长；未输入时按完整计划时长保守估算并在结果中标明。缺少计划停留时长、总预算或路段依据仍为 unknown/unverified，不用 0 填充。
- [x] **Step 4: 处理同步冲突和重试**
  - 开始、进度操作、保存修订与应用提案在数据库串行条件下比较 plan version 和 progress_version。
  - 进度与行程均使用 W01 owner filter、幂等键；stale progress/version 409，绝不回滚已游事实。
- [x] **Step 5: 处理历史恢复旁路**
  - W01 restore_revision 在已有 progress 时先合并保护条目并通过相同校验；不能直接覆盖执行状态。

### Task 4: 游客端手动规划工作区

**Files:**
- Create: `frontend/src/api/itinerary.js`、`frontend/src/stores/itinerary.js`、`frontend/src/components/tour/ItineraryEditor.vue`、`ItineraryConstraints.vue`、`TourProgressPanel.vue`。
- Modify: `frontend/src/views/tourist/RouteView.vue`、`frontend/src/assets/guide-tools.css`、W01 API/store 适配。

**Interfaces:**
- Store actions: `load(sessionId)`、`applyManual(operation)`、`save()`、`start()`、`progress(command)`、`acceptServerRevision(revision)`。
- RouteView consumes existing preset recommendations; selecting preset initializes the draft and source reference, never fabricates a chat answer as the itinerary.

- [x] **Step 1: 加载 W01 任务并初始化 V2 草稿**
  - Cookie unavailable/error keeps page usable as temporary draft and clearly marks save unavailable.
- [x] **Step 2: 做约束输入与模板采用**
  - 同行人、分钟预算、兴趣、必去/排除、步行偏好；未知约束不猜。模板 “采用”变成 stop list，不报虚假时间可行。
- [x] **Step 3: 做手动 stop editor**
  - 手机友好增删、上下移动、时长调整、休息和锁定；stop_id 稳定，已有 completed/skipped 不可由普通编辑抹除。
- [x] **Step 4: 做保存状态、版本冲突与恢复 UI**
  - show dirty/saving/saved/conflict/error；只有服务端确认 revision 才显示 saved。
  - 历史版本可以显式恢复为新修订；服务端校验 stop locks、执行进度和版本条件。
- [x] **Step 5: 做开始/完成/跳过/恢复流程与预算提示**
  - 明确显示 unknown/unverified，不以空路段计 0；开始后只展示当前/未来的剩余预算。
- [x] **Step 6: 检查前端构建与仓库地图**
  - Run: `npm run build -- --configLoader runner` from `frontend/`。
  - Run: `python3 scripts/check_repo_map.py` from repository root。

### Task 5: AI 结构化局部修改提案

**Files:**
- Create: `backend/app/services/itinerary/intent.py`、proposal model/schema/repository/service/API、对应 API 用例。
- Modify: W01 tour API/repository 与 `backend/app/api/router.py`。

**Interfaces:**
- `ItineraryIntentService.propose(text, snapshot, constraints, catalog) -> IntentResult` returns `clarification | operations` only.
- `ProposalService.create(owner, session_id, base_version, draft_digest, progress_version, intent, idempotency_key) -> Proposal`。
- `ProposalService.apply(owner, proposal_id, expected_version, draft_digest, progress_version, idempotency_key) -> TourRevision`。

- [x] **Step 1: 定义严格提案/操作契约与期限**
  - 20 operations max、50 stops max；proposal TTL 30 minutes；status pending/ready/needs_clarification/failed/applied/expired。
- [x] **Step 2: 先写持久 request reservation 与幂等语义**
  - 同键异 body 409；数据库事务不能跨 provider await；过期 executing reservation 能安全标失败，不得改变当前游览。
- [x] **Step 3: 实现有限模型解析**
  - 仅用当前本地草稿、必要约束、已发布目录与本次请求；固定 provider/timeout budget 25s backend、35s route; 解析错误最多一次有界纠正。
  - 对用户输入当作数据，不接受 prompt 中要求覆盖锁定、owner 或事实的文本。
- [x] **Step 4: 通过相同 reducer 生成候选及验证**
  - 最多 200 个候选组合，确定性依次比较 hard conflicts、无关改动数、变更 stop 数、有证据软偏好；不声称全局最优。
  - `candidates.py` 对唯一候选复用 AI actor reducer；超过 200 个转追问。评分依次处理硬冲突、无关操作/字段、变更停留数、验证状态和稳定 JSON tie-break。少走路只按停留点数量作近似偏好，并读取已保存约束或本次明确请求，不推断真实距离。
  - 意图 JSON/schema 首次校验失败会在 25 秒总预算内重新生成一次；第二次失败安全返回错误，未将无效模型输出当作修复指令。
- [x] **Step 5: 实现 owner-scoped proposal read 与显式 apply**
  - 确认前核验 proposal owner、base plan version、draft digest、catalog digest、progress version、TTL；任一变化返回可解释 409。
  - apply 使用服务端已算出的 candidate，一次事务写新修订、进度保护和事件；重复请求返回原修订。
- [x] **Step 6: 验证下架与版本变化**
  - 未应用提案引用内容被下架或发布变化时拒绝旧 apply，要求刷新事实后重新生成。

### Task 6: 前端对话修改、差异确认和地图/数字人联动

**Files:**
- Create: `frontend/src/components/tour/ItineraryProposal.vue`、`ItineraryDiff.vue`。
- Modify: `frontend/src/views/tourist/ChatView.vue`、`frontend/src/views/tourist/MapView.vue`、itinerary API/store and tourist catalog projection。

**Interfaces:**
- `requestProposal(text, {tourId, draftDigest, baseVersion})`、`applyProposal(proposalId)`、`cancelProposal(proposalId)`。
- Chat distinguishes explicit edit intent from ordinary visitor QA; ambiguous intent asks whether to answer or edit. No edits execute from streamed answer text.

- [x] **Step 1: Add proposal state and bounded request/stop handling**
  - Executing proposals have a durable reservation; repeated same-key requests replay state, different request bodies conflict, and reservations older than two minutes fail safely.
  - The stop-waiting control aborts this browser's request/polling, invalidates its generation token, and prevents late responses from replacing the draft; the backend reservation may still finish. Local edits remain intact on failure.
- [x] **Step 2: Present clarification and structured diff**
  - List added/removed/moved/changed stops, constraint effects, evidence and unknown travel/opening facts; confirm button applies exact reviewed candidate.
- [x] **Step 3: Add “introduce current stop” using current confirmed spot_code**
  - Resolve only through server published catalog to entry id; use existing QA selection, not private stop name string as authority.
- [x] **Step 4: Project confirmed itinerary on map by stable stop_id and spot_code**
  - Render only coordinates provided by the approved catalog; unlocated stops remain in list. Do not use `SPOT_COORDS` aliases as routing evidence.
- [x] **Step 5: Connect digital human narration to current stop**
  - Map and chat now share playback ownership and stop semantics; map narration uses the visitor's saved speech rate and drives the shared digital-human speaking state. Current-stop questions continue using published `spot_code` resolution and existing QA selection; itinerary changes take effect only after explicit apply.
- [x] **Step 6: Check build and repository map**
  - `npm run build` and `python3 scripts/check_repo_map.py` pass. Desktop browser exercised draft/save/start/progress recovery and ambiguous-intent/provider-unavailable fallback. Later headless Chromium acceptance covered current-stop input, narrow-screen layout, proposal cancellation, progress refresh after a proposal, and PCM-backed WebAudio completion with map-to-chat playback ownership replacement; physical-device acoustics remain unverified.

### Task 7: Documentation and reviewable delivery

**Files:**
- Modify: `docs/REPO_MAP.md`, `docs/ARCHITECTURE.md`, `docs/plans/2026-10-28-ai-workbench-backlog.md`, `docs/COMPATIBILITY.md`.

**Interfaces:**
- Documentation reflects actual routes/files and states browser/provider/device boundaries separately.

- [x] **Step 1: Update V01 work package with implemented slice and actual evidence**
  - Keep unchecked any unbuilt capability; identify schema/API and incomplete later phases.
- [x] **Step 2: Update code map and architecture for only live code**
  - Add tour snapshot, proposal, progress, catalog and UI entries; do not mark roadmap-only design as implemented.
- [x] **Step 3: Run production build and repository map checks**
  - Record exact outputs and limitations. Do not claim device, browser, provider or live walking-route validation unless actually observed.
- [x] **Step 4: `git diff --check` and inspect the final branch diff**
  - Confirm no W01 owner files were edited in its active checkout and no unrelated uncommitted F01/V03 changes were lost.
- [x] **Step 5: Prepare one fresh branch review**
  - Review schema/ownership, migration chain, concurrency, prompt contract, and demo path before considering a PR.
  - Fresh read-only review found four important gaps (dirty draft start, client provenance, insertion before current, and start/save race); all four were fixed and reviewed again with no new findings. Full migration/owner/concurrency/provider paths were also covered by the backend suite. W02 remains in its own worktree; both branches modify the tour-session repository/model/API and `models/__init__.py`, so integration must resolve those overlapping edits together.
  - Verification in the V01 worktree: backend `316 passed, 1 skipped`; frontend node tests `21 passed`; production Vite build succeeded (existing >500 kB chunk warning); repository map `8 documents, 76 registered HTTP routes`; `git diff --check` clean.
  - Desktop in-app browser at 1280×720: V2 upgrade, published catalog selection, dirty-draft start guard, save/start/current-stop, reload recovery, and completion passed against an isolated temporary local API. An OpenAI-compatible local mock completed proposal generation and a concrete 40→30 minute diff; editing the draft after generation marked the proposal stale and disabled confirmation; regeneration used the changed draft; confirmation saved revision 5 and reload restored it. Provider-unavailable fallback was also observed. Real provider, mobile device, audio, weak-network behavior, and duplicate-submit races remain unverified.
  - Focused review then found that applying a proposal can advance the server progress version; the store now reloads progress after apply, clears stale progress and prompts for refresh if that read fails. Unit coverage verifies both branches; headless browser acceptance then applied a proposal, observed progress version 5, and confirmed the next command submitted version 5.
  - Backend repository regression now covers active tour → apply proposal → reload reconciled progress version → complete current stop successfully; headless browser acceptance confirms the same progression through the frontend store.
  - Budget validation uses the current stop's full plan duration as a labeled conservative estimate when actual remaining time is absent; explicit remaining time overrides it. Boundary tests cover exact budget fit, unknown stop/leg duration, missing total budget, known overrun, finished tour, and invalid negative remaining time. API regression withdraws a published catalog row after proposal generation and confirms apply is rejected without changing snapshot, revisions, itinerary/progress events, or progress state.
- Route page now lets a visitor enter the current stop's actual remaining minutes; clearing the field returns to the labeled conservative estimate. The endpoint validates negative values as HTTP 422. The budget API integration test passes; frontend tests cover query construction, cancellation generations, and map/chat narration ownership. Headless Chromium passed the input/clear flow and proposal-cancel late-response case against mocked API responses. At 390×844 there was no horizontal overflow, long stop text wrapped, and the completion control measured 298×40 px. A separate browser run applied a proposal, refreshed progress to version 5, and completed the current stop with expected version 5. WebAudio decoded and completed synthetic PCM audio for map and chat sessions, and ownership replacement stopped the prior session. Physical-device acoustic output remains unverified.
- Final concurrency review found two store-level races. `confirmProposal` now rechecks the selected tour/proposal and draft after preparation, and after the apply response preserves any draft edits made while the request was pending, leaving them visibly unsaved for review. V2 `save` now refreshes active progress after the server reconciles a plan revision; if refresh fails, progress actions remain gated until reload. New utility tests cover both draft reconciliation outcomes and active/non-active progress refresh. Final regression: backend `316 passed, 1 skipped` (4.79 s); frontend `21 passed`; production Vite build succeeds with the existing >500 kB chunk warning; repo map reports `8 documents, 76 registered HTTP routes`; `git diff --check` is clean. PostgreSQL 17 was initialized in an isolated temporary cluster, and Alembic successfully ran empty base → head (`5c81a1e74f2b`), head → base, and base → head; `alembic current` confirmed `5c81a1e74f2b (head)`. The temporary server and files were stopped and removed. This verifies the real PostgreSQL DDL lifecycle on an empty database; the existing migration tests cover legacy data migration on SQLite. W02 remains in its separate worktree; both branches modify overlapping tour-session files, so integration must resolve them together.
