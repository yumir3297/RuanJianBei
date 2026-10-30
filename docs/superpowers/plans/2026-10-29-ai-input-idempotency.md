# AI 输入接口短期幂等实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 ASR 与图片识别的同一操作在网络重试/并发重复提交时只运行一次上游调用。

**Architecture:** 新增无输入数据持久化的异步进程内幂等协调器，以 endpoint/key/fingerprint 分离调用；缓存有 TTL、条目和结果字节上限。前端对每次录音/图片分析发送稳定到该操作完成的 UUID 请求键。

**Tech Stack:** FastAPI async routes、Python asyncio、Vue 3、Axios、Node 内置测试、pytest。

**Spec:** `docs/superpowers/specs/2026-10-29-ai-input-idempotency-design.md`

## Global Constraints

- 不把音频/图片或明文业务响应写入数据库、磁盘或日志。
- 相同 key 搭配不同请求内容返回 409；失败不缓存。
- 限定 TTL 300 秒、最多 128 项、总 JSON 响应缓存不超过 1 MiB。
- 进程重启/多 worker 不共享该协调器；文档不得宣称持久或分布式幂等。
- 保留无 key 客户端兼容行为和现有容量释放语义。

## Review Focus

- 并发请求会同时触发上游：并发 single-flight 测试。
- key 重用到不同图像/音频：fingerprint 冲突测试。
- 客户端取消等待会取消实际操作或重复 provider 调用：shielded future 测试。
- 错误结果被永久缓存：异常后同键重试测试。
- 缓存无界保存识别结果：TTL/LRU/总字节上限测试。

---

### Task 1: 幂等协调器

**Files:**
- Create: `backend/app/services/idempotency.py`
- Test: `backend/app/tests/test_idempotency.py`

- [x] Write failing tests for single-flight, cached retry, payload conflict, failure retry, TTL, in-flight cap and cancellation shielding.
- [x] Verify tests fail on missing coordinator behavior.
- [x] Implement bounded async coordinator and explicit conflict/capacity errors.
- [x] Run focused tests.

### Task 2: ASR/vision endpoint integration

**Files:**
- Modify: `backend/app/api/voice.py`
- Modify: `backend/app/api/vision.py`
- Test: `backend/app/tests/test_voice_api.py`
- Test: `backend/app/tests/test_vision_api.py`

- [x] Add route tests proving duplicate requests with same key+fingerprint call service once, mismatches return 409, and missing key keeps current behavior.
- [x] Implement endpoint fingerprinting over bytes + MIME + semantic inputs; route cache hit bypasses capacity acquisition/provider.
- [x] Run focused route tests and existing capacity/validation tests.

### Task 3: Frontend operation keys

**Files:**
- Create: `frontend/src/utils/idempotencyKey.js`
- Modify: `frontend/src/api/voice.js`
- Modify: `frontend/src/api/vision.js`
- Modify: `frontend/src/views/tourist/ChatView.vue`
- Test: focused Node/Vite tests for API headers and key lifecycle.

- [x] Test key creation and API headers; ChatView retains the image key until image replacement/clear and creates a new key for each image capture/selection and ASR recording.
- [x] Add `Idempotency-Key` header to ASR and vision POST requests and pass stable operation keys from ChatView.
- [x] Run full frontend tests/build.

### Task 4: Backlog and validation

- [x] Update F01 to mark only ASR/vision process-local coverage complete; retain chat SSE and K01 publication durability as open items.
- [x] Update repository map and architecture for new coordinator.
- [x] Run full backend tests, map checker and `git diff --check`.
- [x] Final review of privacy, capacity leases, exception/cancellation and cache bounds.

Final review: self-review (multi-agent delegation disabled for this task).
