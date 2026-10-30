# 游客历史回答重播实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在游客当前聊天中重播已保存回答，并在 TTS 不可用时降级为浏览器朗读。

**Architecture:** 新增 session-scoped repository 查询和轻量重播 API，调用 TTS 工厂合成数据库中保存的原答案，不触发 QA pipeline。ChatView 请求该 API 后把音频/文本提交给共享播放器，复用播放所有权及本地语速。

**Tech Stack:** FastAPI、Pydantic、SQLAlchemy async、Vue 3、Pinia、Axios、Node 内置测试、pytest。

**Spec:** `docs/superpowers/specs/2026-10-29-tourist-answer-replay-design.md`

## Global Constraints

- 不改 `sources/` 同步参考文件。
- 不新增数据库迁移、持久音频缓存或问答生成调用。
- 使用 `chat_log_id + session_id` 限定访问，并沿用现有 TTS 工厂和播放器会话隔离。
- 语速继续只在前端播放层生效；后端重播不接收或应用语速。
- 不提交、不推送；保留工作副本中已有的其他改动。

## Review Focus

- 越权或错误会话读取：repository/API 测试确保不匹配时返回 404 且不调用 TTS。
- 重播意外调用 LLM：API 测试确保只读取日志并调用 TTS 工厂。
- 重播过程中被其他播放替换后，迟到音频启动：前端控制流测试覆盖 session token 失效。
- TTS 未配置：响应 `available=false`，播放器回退浏览器朗读。
- 用户当前语速变化：重播传本机最新值而不让 provider 再次调速。

---

### Task 1: 会话归属查询与重播 API

**Files:**
- Modify: `backend/app/repositories/chat_log.py`
- Modify: `backend/app/api/chat.py`
- Test: `backend/app/tests/test_chat_replay_api.py`
- Test: `backend/app/tests/test_chat_log_repository.py`

**Interfaces:**
- Produces: `ChatLogRepository.get_for_session(chat_log_id: int, session_id: str) -> ChatLog | None`。
- Produces: `POST /api/chat/replay` 接受 `chat_log_id`、`session_id`、可选 `tts_voice`，返回 `base64_audio`、`duration_ms`、`provider`、`available`。

- [x] **Step 1: 先写失败测试**。覆盖 repository 同会话命中、跨会话/未知 ID 返回 `None`；API 用假的 session/repository/TTS 证明合成文本等于保存答案、无配置返回 `available=false`、错会话 404 且不调用 TTS、不调用 `build_pipeline`。
- [x] **Step 2: 运行新增测试确认因接口未实现而失败**。运行 `python -m pytest app/tests/test_chat_log_repository.py app/tests/test_chat_replay_api.py -q`（cwd `backend/`）；初次因 repository 方法和 route 不存在失败。
- [x] **Step 3: 实现最小 session-scoped 查询与重播路由**。使用 Pydantic 请求模型限制 session ID 长度、可选音色沿用现有四种枚举；取得会话归属记录后，在 TTS ready 时 `build_tts_service(...).synthesize(log.answer)`，否则返回不可用标记；保留 404/429/503 语义。
- [x] **Step 4: 重跑新增测试确认通过**。聚焦后端测试 5 passed；完整后端测试 242 passed、3 skipped。

### Task 2: 游客重播控制与共享播放器

**Files:**
- Modify: `frontend/src/api/chat.js`
- Modify: `frontend/src/views/tourist/ChatView.vue`
- Test: `frontend/tests/chat-replay.test.mjs` 或既有测试支持的最小控制器模块及相应测试。

**Interfaces:**
- Consumes: 后端 `POST /api/chat/replay` 响应接口。
- Produces: 已完成回答的“重播讲解”操作；请求使用当前 session、当前音色；播放使用当前本机语速及共享播放器 session ID。

- [x] **Step 1: 先写失败测试**。通过抽取的最小可测函数验证点击创建播放会话、传当前 session/voice/rate、把响应交给播放器；失效 session 的迟到响应不入队；空音频允许浏览器朗读；同条回答连续重播状态不互相覆盖。
- [x] **Step 2: 运行测试确认缺失行为导致失败**。在 `frontend/` 执行 `npm test -- tests/chat-replay.test.mjs`；初次因控制器行为未实现失败。
- [x] **Step 3: 实现 API 客户端、控制函数与按钮**。仅对已完成且含日志 ID 的非欢迎回答显示；按钮状态/错误与单条回答关联；替换播放后取消旧重播并丢弃迟到响应；沿用全局 `claimPlayback`/`enqueue`。
- [x] **Step 4: 重跑新增测试确认通过**。重播控制测试 5 passed。

### Task 3: 回归与仓库资料

**Files:**
- Modify: `docs/plans/2026-10-28-ai-workbench-backlog.md`
- Modify: `docs/REPO_MAP.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/COMPATIBILITY.md`

- [x] **Step 1: 运行后端完整测试与前端完整测试/构建**。后端 242 passed、3 skipped；前端 61 passed、1 skipped；production build passed（保留既有大 chunk 警告）。
- [x] **Step 2: 更新文档**。V03 已勾选历史重播，并保留音色/版本/缓存及真机验收待办；更新功能地图、架构和兼容性矩阵。
- [x] **Step 3: 运行仓库地图校验与差异检查**。`python3 scripts/check_repo_map.py`：8 docs、43 routes；`git diff --check` 通过。
- [x] **Step 4: 最终独立代码复核**。作者复核接口权限范围、TTS/QA 边界、迟到/替换播放状态、降级路径；无遗留 Critical/Important 发现。未在真实供应商或真机环境验收。
