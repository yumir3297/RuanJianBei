# Worktree 改动逐路径核对（2026-11-05）

基线：原工作树 `code/RuanJianBei` 分支 `codex/repository-map`，HEAD `672a104`；集成树 `integration-work/v01` 分支引用由本地 fetch 同步。扫描到 95 个 porcelain 状态路径。未读取或修改 `sources/`，未执行合并、清理或 prune。

2026-11-05 复核：原工作树仍在 `672a104` 且 porcelain 数仍为 95；原仓库本地 `codex/competition-integration` 引用与集成树 `codex/competition-integration@0ec66ef` 相同（架构索引更新后提交为 `f4d9f47`，其后续推进见开发进度）。活动 V01/W02/W02-V01 worktree HEAD 和路径数量仍分别为 `098553f`/49、`a8c2837`/35、`098553f`/39；已不存在的 `/private/tmp/ai-guide-phase3` 仍是 prunable 登记，未 prune。原 checkout 的 95 条未提交内容与此核对前相同；集成树的 `frontend/node_modules` 本机依赖链接仍未跟踪。

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

## V01/W02 活动 worktree 差异

字节相同才记为已合并；不同实现不按祖先关系或功能名称推断等价。目录按文件递归比较，并排除 Python cache 文件。

### V01（`v01-worktree`）

当前 HEAD `098553f`，49 个 porcelain 状态路径；保全快照 `v01-preserved-snapshot`。分类统计：25 同路径存在但内容不同；需语义审查；24 已合并（当前内容与集成树相同）.

| 状态 | 路径 | 分类 | 对照证据 |
|---|---|---|---|
| ` M` | `backend/app/api/tour_sessions.py` | 后续实现替代候选：现集成测试覆盖源测试并新增提案回放/目录过期用例；保留快照，不覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/__init__.py` | 已被集成模型注册扩展替代；保留源版本用于核对迁移引用 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/tour_session.py` | 被后续模型/版本约束实现替代候选；具体 schema 迁移仍需审计 | snapshot=yes; integration=yes |
| ` M` | `backend/app/repositories/tour_session.py` | 后续仓储包含提案 reservation、锁和版本 fence；不以旧文件覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/schemas/itinerary.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `backend/app/services/itinerary/progress.py` | 后续进度版本及状态 fence 实现不同；相关行为由集成回归覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/tests/test_itinerary_progress.py` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `backend/app/tests/test_tour_session_api.py` | 集成测试包含源测试用例并增加覆盖；旧测试实现由后续用例替代 | snapshot=yes; integration=yes |
| ` M` | `docs/ARCHITECTURE.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/COMPATIBILITY.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/REPO_MAP.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/plans/2026-10-28-ai-workbench-backlog.md` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `docs/superpowers/plans/2026-10-29-v01-editable-itinerary.md` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `frontend/src/api/tourSessions.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-page.css` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-tools.css` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `frontend/src/composables/useAudioPlayer.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/chat.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/tourSessions.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/ChatView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/MapView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/RouteView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/5c81a1e74f2b_add_tour_progress_and_proposals.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/candidates.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/intent.py` | 后续实现不同；需逐项核验意图覆盖，暂不移植 | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/provenance.py` | 后续来源校验实现不同；需逐项核验约束覆盖，暂不移植 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_itinerary_intent.py` | 9 个源测试、10 个集成测试；名称不完全相同，具体断言待审 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_itinerary_provenance.py` | 2 个源测试、6 个集成测试；需核对具体断言后确认替代关系 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_tour_budget_api.py` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_tour_progress_and_proposals.py` | 20 个集成测试包含源 10 个用例并新增恢复/预算/来源校验场景；后续实现替代 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_tour_proposal_catalog_staleness.py` | 后续目录版本验证实现不同；保留快照，语义由集成 staleness 测试验证 | snapshot=yes; integration=yes |
| `??` | `frontend/src/api/itinerary.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/cloneJson.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/itineraryIntent.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/itineraryProposalDiff.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/progressRefresh.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/proposalApplyState.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/proposalSnapshot.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/requestGeneration.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/tourBudgetParams.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/audio-playback-session.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/clone-json.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/itinerary-intent.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/itinerary-proposal-diff.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/progress-refresh.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/proposal-apply-state.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/proposal-snapshot.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/request-generation.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `frontend/tests/tour-budget-api.test.mjs` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |

### W02（`code/w02-worktree`）

当前 HEAD `a8c2837`，35 个 porcelain 状态路径；保全快照 `w02-preserved-snapshot`。分类统计：25 同路径存在但内容不同；需语义审查；6 已合并（当前内容与集成树相同）；4 目录内有相同/不同/新增文件，需逐项核验.

| 状态 | 路径 | 分类 | 对照证据 |
|---|---|---|---|
| ` M` | `backend/alembic/env.py` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/router.py` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/tour_sessions.py` | 后续实现替代候选：现集成测试覆盖源测试并新增提案回放/目录过期用例；保留快照，不覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/__init__.py` | 已被集成模型注册扩展替代；保留源版本用于核对迁移引用 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/tour_session.py` | 被后续模型/版本约束实现替代候选；具体 schema 迁移仍需审计 | snapshot=yes; integration=yes |
| ` M` | `backend/app/repositories/tour_session.py` | 后续仓储包含提案 reservation、锁和版本 fence；不以旧文件覆盖 | snapshot=yes; integration=yes |
| ` M` | `docs/ARCHITECTURE.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/COMPATIBILITY.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/REPO_MAP.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/plans/2026-10-28-ai-workbench-backlog.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/api/tourSessions.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-tools.css` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/composables/useAudioPlayer.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/chat.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/tourSessions.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/ChatView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/MapView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/RouteView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/5c81a1e74f2b_add_tour_progress_and_proposals.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/f1b4c9d76e20_add_tool_execution.py` | 被集成 migration merge 替代，不能单独移植：源父 revision=`e9f4c2b8016a`，集成父 revision=`8ab42c17d3e9`；集成版同时添加 itinerary proposal execution 字段 | snapshot=yes; integration=yes |
| `??` | `backend/app/api/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/models/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/repositories/tool_execution.py` | 后续 repository 实现不同；集成树含幂等回放、lease/fence 与取消处理测试，未覆盖旧文件 | snapshot=yes; integration=yes |
| `??` | `backend/app/schemas/itinerary.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/schemas/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/` | 目录内有相同/不同/新增文件，需逐项核验 | 4 个源码/资料文件；相同=1、不同=3、集成缺少=0、集成额外=3（排除 Python cache） |
| `??` | `backend/app/services/tool_execution/` | 目录内有相同/不同/新增文件，需逐项核验 | 6 个源码/资料文件；相同=0、不同=6、集成缺少=0、集成额外=0（排除 Python cache） |
| `??` | `docs/research/` | 目录内有相同/不同/新增文件，需逐项核验 | 1 个源码/资料文件；相同=0、不同=1、集成缺少=0、集成额外=1（排除 Python cache） |
| `??` | `docs/selling-points/` | 目录内有相同/不同/新增文件，需逐项核验 | 1 个源码/资料文件；相同=0、不同=1、集成缺少=0、集成额外=2（排除 Python cache） |
| `??` | `docs/superpowers/plans/2026-10-29-v01-editable-itinerary.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/plans/2026-10-29-w02-durable-execution.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/plans/2026-10-29-w02-execution-ledger.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `frontend/src/api/itinerary.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/requestGeneration.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |

### Migration lineage 语义核验

- V01 `5c81a1e74f2b_add_tour_progress_and_proposals.py` 在源与集成树字节相同；集成 revision `8ab42c17d3e9` 将它与 speech metadata migration `c3b7e1d9a62f` 合并。
- W02 快照 revision `f1b4c9d76e20` 的父为 `e9f4c2b8016a`，且不添加 `itinerary_proposals.base_snapshot_json` / `execution_job_id`。集成树同 revision 改为父 `8ab42c17d3e9`，并增加这两列及索引；之后 `6e1a4c7d9b20` 检查/补齐遗失的 speech metadata，`7d2e93a5b601` 与 `91a0c5e2f347` 分别拒绝已知不完整的 W02/knowledge schema。此为有意处理分叉迁移历史的后续实现，旧 W02 migration 必须保留在快照，不得单独 cherry-pick。
- 临时 Python 环境没有 Alembic `command` API（`test_speech_metadata_migration.py` 收集时报 `ImportError`），故没有声称本轮实跑 Alembic 升级。该迁移链真实数据库往返仍待具备 Alembic 的隔离环境；此限制不影响单独运行的 W02 执行验收/worker 测试。

### W02/V01 集成副本（`code/w02-integration`）

当前 HEAD `098553f`，39 个 porcelain 状态路径；保全快照 `w02-integration-preserved-snapshot`。分类统计：29 同路径存在但内容不同；需语义审查；8 已合并（当前内容与集成树相同）；2 目录内有相同/不同/新增文件，需逐项核验.

| 状态 | 路径 | 分类 | 对照证据 |
|---|---|---|---|
| ` M` | `backend/alembic/env.py` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/router.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/tour_sessions.py` | 后续实现替代候选：现集成测试覆盖源测试并新增提案回放/目录过期用例；保留快照，不覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/__init__.py` | 已被集成模型注册扩展替代；保留源版本用于核对迁移引用 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/tour_session.py` | 被后续模型/版本约束实现替代候选；具体 schema 迁移仍需审计 | snapshot=yes; integration=yes |
| ` M` | `backend/app/repositories/tour_session.py` | 后续仓储包含提案 reservation、锁和版本 fence；不以旧文件覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/schemas/itinerary.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `backend/app/services/itinerary/progress.py` | 后续进度版本及状态 fence 实现不同；相关行为由集成回归覆盖 | snapshot=yes; integration=yes |
| ` M` | `docs/ARCHITECTURE.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/COMPATIBILITY.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/REPO_MAP.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/plans/2026-10-28-ai-workbench-backlog.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/superpowers/plans/2026-10-29-v01-editable-itinerary.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/api/tourSessions.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-tools.css` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/composables/useAudioPlayer.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/chat.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/tourSessions.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/ChatView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/MapView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/RouteView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/5c81a1e74f2b_add_tour_progress_and_proposals.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/f1b4c9d76e20_add_tool_execution.py` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/app/api/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/models/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/repositories/tool_execution.py` | 后续 repository 实现不同；集成树含幂等回放、lease/fence 与取消处理测试，未覆盖旧文件 | snapshot=yes; integration=yes |
| `??` | `backend/app/schemas/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/candidates.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/intent.py` | 后续实现不同；需逐项核验意图覆盖，暂不移植 | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/provenance.py` | 后续来源校验实现不同；需逐项核验约束覆盖，暂不移植 | snapshot=yes; integration=yes |
| `??` | `backend/app/services/tool_execution/` | 目录内有相同/不同/新增文件，需逐项核验 | 6 个源码/资料文件；相同=4、不同=2、集成缺少=0、集成额外=0（排除 Python cache） |
| `??` | `backend/app/tests/test_tool_execution_acceptance.py` | 原 W02 工作树无此文件；测试仅见于后续 W02/V01 快照并扩充于当前集成树 | snapshot=yes; integration=yes |
| `??` | `docs/research/2026-10-29-w02-durable-execution-research.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/selling-points/` | 目录内有相同/不同/新增文件，需逐项核验 | 1 个源码/资料文件；相同=0、不同=1、集成缺少=0、集成额外=2（排除 Python cache） |
| `??` | `docs/superpowers/plans/2026-10-29-w02-durable-execution.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/plans/2026-10-29-w02-execution-ledger.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `frontend/src/api/itinerary.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/requestGeneration.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
