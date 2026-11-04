# Worktree 改动逐路径核对（2026-11-05）

基线：原工作树 `code/RuanJianBei` 分支 `codex/repository-map`，HEAD `672a104`；集成树 `integration-work/v01` 分支引用由本地 fetch 同步。扫描到 95 个 porcelain 状态路径。未读取或修改 `sources/`，未执行合并、清理或 prune。

判定规则：当前文件字节与集成树对象一致才标记“已合并”；同路径内容不同时不推断语义等价；目录状态行递归比较当前文件集合。快照命中仅证明保全，不证明已集成。

| 状态 | 路径 | 判定 | 证据 |
|---|---|---|---|
| ` M` | `AGENTS.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `README.md` | 文档内容不同；按限定范围不迁移此产品介绍 | 快照含该文件；集成树含该文件 |
| ` M` | `backend/.env.example` | 同路径模板不同，未迁移；保留两侧配置供逐项校验 | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/api/chat.py` | 已被后续集成实现替代（原工作树缺少当前可见性、视觉目录绑定与语义 FAQ 初始化） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/api/vision.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/api/voice.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/core/config.py` | 已被后续集成实现替代（原工作树删去站点/知识导入配置） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/models/chat_log.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/repositories/chat_log.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/schemas/chat.py` | 已被后续集成实现替代（原工作树缺少视觉确认和证据修订字段） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/services/qa/pipeline.py` | 已被后续集成实现替代（原工作树缺少当前快路径、证据绑定及请求 epoch/状态保护） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/services/qa/stream_events.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/services/tts/factory.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/services/tts/streaming.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/services/tts/volcengine.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/tests/test_chat_stream_api.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/tests/test_pipeline.py` | 旧基线测试不同于当前集成测试；未移植以免替换 epoch/FAQ/RAG 回归 | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/tests/test_tts_factory.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/tests/test_vision_api.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/tests/test_visitor_memory_api.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/app/tests/test_voice_api.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `backend/main.py` | 已被后续集成实现替代（原工作树移除后台 worker 与 FAQ/模型降级就绪检查） | 快照含该文件；集成树含该文件 |
| ` M` | `docs/ARCHITECTURE.md` | 文档内容不同；按限定范围不迁移旧架构文档 | 快照含该文件；集成树含该文件 |
| ` M` | `docs/COMPATIBILITY.md` | 文档内容不同；按限定范围不迁移兼容性文档 | 快照含该文件；集成树含该文件 |
| ` M` | `docs/REPO_MAP.md` | 文档内容不同；按限定范围不迁移仓库地图 | 快照含该文件；集成树含该文件 |
| ` M` | `docs/plans/2026-10-27-feature-roadmap.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/AGENTS.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/package.json` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/api/chat.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/api/narration.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/api/vision.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/api/voice.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/assets/guide-page.css` | 保留快照，不迁移（当前任务不含前端改版） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/components/SpotNarrationCard.vue` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/composables/useAudioPlayer.js` | 保留快照，不迁移（当前任务限定后端 AI 架构与 Worktree 审核） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/composables/useSSEStream.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/stores/chat.js` | 保留快照，不迁移（当前任务限定后端 AI 架构与 Worktree 审核） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/views/tourist/ChatView.vue` | 保留快照，不迁移（当前任务不含前端改版） | 快照含该文件；集成树含该文件 |
| ` M` | `frontend/src/views/tourist/MapView.vue` | 保留快照，不迁移（当前任务不含前端改版） | 快照含该文件；集成树含该文件 |
| `??` | `backend/alembic/versions/c3b7e1d9a62f_add_chat_speech_metadata.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/api/bounded_body.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/api/capacity.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/services/audio_duration.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/services/capacity.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/services/idempotency.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/services/tts/replay_cache.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/services/tts/speech_profile.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/services/vision/image_headers.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/fixtures/` | 目录递归比较：内容与集成树相同 | 当前文件 3；与集成树相同 3、不同 0、集成缺少 0、集成额外 0；快照路径 3 |
| `??` | `backend/app/tests/test_audio_duration.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_bounded_body.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_capacity.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_chat_log_repository.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_chat_replay_api.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_idempotency.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_production_security_config.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_stream_knowledge_integration.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_tts_replay_cache.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `backend/app/tests/test_tts_speech_profile.py` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/plans/2026-10-28-ai-workbench-backlog.md` | 计划文档有版本差异；本轮不迁移，保留快照待相关实现整合时参考 | 快照含该文件；集成树含该文件 |
| `??` | `docs/research/` | 目录递归比较：内容与集成树相同 | 当前文件 2；与集成树相同 2、不同 0、集成缺少 0、集成额外 0；快照路径 2 |
| `??` | `docs/selling-points/` | 目录递归比较：内容与集成树相同 | 当前文件 3；与集成树相同 3、不同 0、集成缺少 0、集成额外 0；快照路径 3 |
| `??` | `docs/superpowers/plans/2026-10-28-ai-stream-validation.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-28-k01-stream-integration.patch` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-28-resilient-ai-stream.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-28-shared-playback-round1.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-ai-input-idempotency.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-chat-speech-profile.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-judge-experience-acceptance.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-nonwav-duration.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-production-auth-hardening.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-tourist-answer-replay.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-tourist-speech-rate.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-v01-editable-itinerary.md` | V01 计划文档有版本差异；本轮不迁移文档，代码差异另核 | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-w01-tour-session-workspace.md` | W01 计划文档有版本差异；保留快照，当前不扩展范围 | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/plans/2026-10-29-w02-durable-execution.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-27-knowledge-workspace-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-28-resilient-ai-stream-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-ai-input-idempotency-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-chat-speech-profile-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-nonwav-duration-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-production-auth-hardening-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-tour-session-workspace-design.md` | W01 设计文档有版本差异；保留快照，当前不扩展范围 | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-tourist-answer-replay-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-tourist-speech-rate-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-v01-editable-itinerary-design.md` | V01 设计文档有版本差异；保留快照，代码差异另核 | 快照含该文件；集成树含该文件 |
| `??` | `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/src/utils/adaptiveAudioBuffer.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/src/utils/chatMetrics.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/src/utils/chatReplay.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/src/utils/idempotencyKey.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/src/utils/latestRequest.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/src/utils/publicationRecovery.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/src/utils/speechRatePreference.js` | 已合并（当前内容与集成树逐字节相同） | 快照含该文件；集成树含该文件 |
| `??` | `frontend/tests/` | 目录递归比较：15 个文件逐字节相同、1 个不同，集成树另有 22 个；保留两侧版本，本轮不迁移前端测试 | 当前文件 16；与集成树相同 15、不同 1、集成缺少 0、集成额外 22；快照路径 16 |
