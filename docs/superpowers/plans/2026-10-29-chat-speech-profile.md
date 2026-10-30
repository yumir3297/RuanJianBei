# 聊天语音版本与重播缓存实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为已保存答案关联内容指纹和生成时 TTS profile，并为重复历史重播提供有界的进程内缓存。

**Architecture:** Alembic 为 chat_logs 增加可空 `speech_metadata` JSON 文本列；pipeline 写入回答指纹和非秘密合成参数。重播 API 优先用历史音色，依据答案指纹与当前完整 profile 命中 TTL/LRU 缓存，缓存未命中时合成并缓存。

**Tech Stack:** FastAPI、SQLAlchemy async、Alembic、Vue 3、Node 内置测试、pytest。

**Spec:** `docs/superpowers/specs/2026-10-29-chat-speech-profile-design.md`

## Global Constraints

- 不触碰 `sources/`，不访问或启动真实数据库，不运行迁移、不调用真实 TTS。
- 元数据不得含 API keys、Access Keys 或原始音频。
- 缓存必须有 TTL、条目数和内存上界；仅同一文本与相同全部合成参数可命中。
- 旧日志 `speech_metadata=NULL`、旧前端请求及已有跨会话校验保持兼容。
- 保留工作副本的既有变更，不提交、不推送。

## Review Focus

- TTS profile 变更仍复用旧音频：参数隔离测试覆盖 provider/model/voice/format/sample rate。
- 旧日志或历史音色缺失：重播回退当前请求音色。
- 缓存无限增长或过期音频被复用：TTL/LRU/总字节上限测试。
- SQLite/PostgreSQL 旧行兼容：迁移可逆且字段可空。
- 日志意外持久凭据：profile allowlist 测试只含声明字段。

---

### Task 1: TTS Profile 与有界重播缓存

**Files:**
- Create: `backend/app/services/tts/speech_profile.py`
- Create: `backend/app/services/tts/replay_cache.py`
- Test: `backend/app/tests/test_tts_replay_cache.py`
- Test: `backend/app/tests/test_tts_speech_profile.py`

- [x] Write failing tests for exact key variation, SHA-256 answer fingerprint, secret exclusion, TTL expiry, LRU, max entries and max bytes.
- [x] Verify tests fail on missing profile/cache behavior.
- [x] Implement allowlisted profile construction and bounded TTL/LRU byte cache.
- [x] Run focused tests and confirm green (8 profile/cache tests passed after byte-bound coverage).

### Task 2: Persist metadata and upgrade existing DBs

**Files:**
- Modify: `backend/app/models/chat_log.py`
- Modify: `backend/app/repositories/chat_log.py`
- Modify: `backend/app/services/qa/pipeline.py`
- Modify: `backend/app/api/chat.py`
- Create: `backend/alembic/versions/<new>_add_chat_speech_metadata.py`
- Test: `backend/app/tests/test_chat_log_repository.py`
- Test: `backend/app/tests/test_pipeline.py`

- [x] Add failing tests that saved chat logs carry answer hash plus generated voice/profile, while omit secrets and preserve null for existing rows.
- [x] Verify tests fail before code changes.
- [x] Add nullable column migration and model/repository serialization; inject profile from settings into QAPipeline and persist it with every non-text-only assistant answer. Existing Alembic env already imports ChatLog, so no env edit was needed.
- [x] Verify migration script syntax and revision chain without connecting to the configured application database; run relevant persistence/pipeline tests (17 passed).

### Task 3: Cache replay audio and prefer original voice

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/tests/test_chat_replay_api.py`
- Modify: `frontend/tests/chat-replay.test.mjs` if request contract changes.

- [x] Add failing tests for stored voice precedence, legacy fallback voice, same-key cache hit, changed profile cache miss and cross-session isolation.
- [x] Verify tests fail before implementation.
- [x] Use profile+answer fingerprint for cache lookup; synthesize only on miss and cache only nonempty output. Prefer persisted voice preset; keep fallback for older records.
- [x] Run replay tests, then backend/frontend full suites and frontend build; backend 256 passed / 3 skipped, frontend 61 passed / 1 skipped, build passed.

### Task 4: Update plan documents and validate maps

- [x] Mark V03 profile/voice/cache and local-only cross-device policy accurately; retain W01 dependency and true device/provider limitations.
- [x] Update repository map, architecture and compatibility references.
- [x] Run repository map checker and `git diff --check`.
- [x] Final code review for migration compatibility, cache bounds, session isolation and accidental secret persistence. Did not apply migration to a configured application database or call a real provider.
