# Worktree 改动逐路径核对（2026-11-05）

2026-11-05 后续 AI 架构阶段：从集成 `83d342a` 将最终 HTTP TTS 尾段选择、FIFO drain 与 epoch gate 收入 `StreamTurn`；指定回归 261 passed、compileall/diff check 通过，详情见 `PROGRESS.md`。本阶段不改变原 checkout 或 worktree 的 Git 状态；原始未提交路径和保全快照继续保留。

2026-11-05 后续 AI 架构阶段：本阶段从集成 `7adb18c` 开始，完成 StreamTurn 装配/清理边界和 GeneratorExit 行为测试；最新验证结果、Pipeline 剩余职责及源码文件行数见 `PROGRESS.md`。Worktree 基线重新确认后原 checkout 95 路径、V01/W02/W02-V01 49/35/39，5 个快照保持；阶段提交同步原仓库同名集成 ref，不合入原活动 checkout。

基线：原工作树 `code/RuanJianBei` 分支 `codex/repository-map`，HEAD `672a104`；集成树 `integration-work/v01` 分支引用由本地 fetch 同步。扫描到 95 个 porcelain 状态路径。未读取或修改 `sources/`，未执行合并、清理或 prune。

2026-11-05 最新复核：原 checkout 仍为 `672a104` / 95 个未提交路径；V01、W02、W02/V01 集成分别为 `098553f`/49、`a8c2837`/35、`098553f`/39。保全快照 refs `codex/preserved-uncommitted-2026-11-04@4acaa53`、`codex/main-preserved-snapshot@e115eab`、`codex/v01-preserved-snapshot@3805943`、`codex/w02-preserved-snapshot@48ef626`、`codex/w02-integration-preserved-snapshot@5433557` 均存在。集成 HEAD 与原仓库同名集成 ref 目前均为 `6015817`；集成副本仅有未跟踪的 `frontend/node_modules` 本机链接。`/private/tmp/ai-guide-phase3` 仍 prunable 且未清理；`sources/` 无 Git 状态。本轮扩展回归 257 passed、1 条 Starlette 弃用警告，compileall 和 diff check 通过。逐路径分类见下表；所有活动 worktree 与快照均保留。

2026-11-05 本轮复核：原 checkout 仍为 `672a104` / 95 状态路径；V01、W02、W02/V01 集成 worktree 分别为 49、35、39 个状态路径，HEAD 仍为 `098553f`、`a8c2837`、`098553f`。原仓库的五个保全快照 refs（主 checkout 两个、V01、W02、W02/V01 集成）均可解析；本轮开始时原仓库 `codex/competition-integration` ref 与集成 checkout 均为 `3687e7f`，随后提交 `ef51a88` 并从集成副本 fetch 同步该 ref。`sources/` 状态为空；`frontend/node_modules` 保持为集成副本的本机链接；`/private/tmp/ai-guide-phase3` 仍显示 prunable，未执行 prune。路径级既有语义判定见下表和进度日志，本轮没有将快照内容覆盖到集成树，也没有合并到原 checkout。当前仍未决的是完整迁移冲突审查、真实 Alembic migration 往返、真实 provider/设备验收；整库 pytest 收集存在 6 个导入错误，见进度记录。

2026-11-05 复核：原工作树仍在 `672a104` 且 porcelain 数仍为 95；原仓库本地 `codex/competition-integration` 引用与集成树 `codex/competition-integration@0ec66ef` 相同（架构索引更新后提交为 `f4d9f47`，其后续推进见开发进度）。活动 V01/W02/W02-V01 worktree HEAD 和路径数量仍分别为 `098553f`/49、`a8c2837`/35、`098553f`/39；已不存在的 `/private/tmp/ai-guide-phase3` 仍是 prunable 登记，未 prune。原 checkout 的 95 条未提交内容与此核对前相同；集成树的 `frontend/node_modules` 本机依赖链接仍未跟踪。

判定规则：当前文件字节与集成树对象一致才标记“已合并”；同路径内容不同时不推断语义等价；目录状态行递归比较当前文件集合。快照命中仅证明保全，不证明已集成。

在集成分支 `f6f5921` 后复核：原 checkout 95 个状态路径、V01 49、W02 35、W02/V01 集成 39；当前集成树已推进 mux epoch fence helper，详细提交见 `PROGRESS.md`。`sources/` 无状态变化。不得据此推断所有路径已语义合并；下表中明确标注的迁移/schema、行程 API/模型、文档/前端差异仍需逐项决策。

2026-11-05 后续复核：原 checkout 仍 `672a104` / 95 状态路径；集成树与原仓库同名引用在 `4ad111e` 后同步，V01/W02/W02-V01 状态路径仍为 49/35/39。快照分支仍存在，`/private/tmp/ai-guide-phase3` 仍 prunable 未清理，`sources/` 无状态变化。

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
| ` M` | `backend/app/tests/test_pipeline.py` | 保留两侧测试版本；主 checkout 的 `test_direct_answer_appends_inline_citation_when_sources_exist` 期待按 retrieval `evidence_id` 自动拼接 `[证据1]`，集成版对应测试改为 `test_direct_answer_preserves_text_when_sources_exist`。当前 `_ensure_inline_citations` 不添加该标记，CONTRACTS 明确 source IDs 只追踪知识版本、不证明片段支持回答或已完成逐句引用核验；分类为后续证据契约替代，未移植旧断言。集成版另增加 FAQ/RAG/epoch/画像/路由回归 | 快照含该文件；集成树含该文件；集成对应行为测试 1 passed |
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

当前 HEAD `098553f`，49 个 porcelain 状态路径；保全快照 `v01-preserved-snapshot`。以下按每个路径列出字节比较和语义判定；未完成的审查保留明确标记，不以分支祖先关系推断已合入。

| 状态 | 路径 | 分类 | 对照证据 |
|---|---|---|---|
| ` M` | `backend/app/api/tour_sessions.py` | 旧 API 内联同步调用 `ItineraryIntentService`；集成版改为同事务创建 proposal reservation 与 `itinerary.proposal` durable job，返回 202，测试覆盖 replay/stale progress；属于后续实现替代，不覆盖快照 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/__init__.py` | 已被集成模型注册扩展替代；保留源版本用于核对迁移引用 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/tour_session.py` | 已由 durable proposal schema 替代：集成版增加 `base_snapshot_json`/`execution_job_id`，merge migration 与 recovery/replay 测试证明用途；Alembic upgrade/downgrade 仍未实跑 | snapshot=yes; integration=yes |
| ` M` | `backend/app/repositories/tour_session.py` | 后续仓储包含提案 reservation、锁和版本 fence；不以旧文件覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/schemas/itinerary.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `backend/app/services/itinerary/progress.py` | 后续进度版本及状态 fence 实现不同；相关行为由集成回归覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/tests/test_itinerary_progress.py` | 已被集成版覆盖并扩展：保留 V01 原有进度用例，另增加估算时长保持 unverified、当前剩余为 0 但已过截止时间仍冲突两项行为 | snapshot=yes; integration=yes |
| ` M` | `backend/app/tests/test_tour_session_api.py` | 集成测试包含源测试用例并增加覆盖；旧测试实现由后续用例替代 | snapshot=yes; integration=yes |
| ` M` | `docs/ARCHITECTURE.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/COMPATIBILITY.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/REPO_MAP.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/plans/2026-10-28-ai-workbench-backlog.md` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `docs/superpowers/plans/2026-10-29-v01-editable-itinerary.md` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `frontend/src/api/tourSessions.js` | 已合并（与集成树逐字节相同） | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-page.css` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-tools.css` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `frontend/src/composables/useAudioPlayer.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/chat.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/tourSessions.js` | V01 的行程编辑/提案 store 已扩展为 durable proposal 恢复与重试：从服务端恢复最新提案、并列时间戳显式选择、waiting_user 不自动重试；同时加入 open/save/progress/budget 请求代际保护及保存期间草稿并发编辑协调。差异与 durable worker/schema 后续实现一致；store/helper 定向 Node 行为集 43 passed，覆盖提案恢复/风险确认/迟到响应/并发草稿/进度预算刷新；归类为后续集成扩展，保留 V01 快照 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/ChatView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/MapView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/RouteView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/5c81a1e74f2b_add_tour_progress_and_proposals.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/candidates.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/intent.py` | 源实现被后续实现替代：集成版基于规范化后的 candidate 计算 diff；没有移植旧文件 | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/provenance.py` | 源实现被后续实现替代并扩展：集成版处理景点替换、目录修订变更、AI 时长归属和受影响路线段证据失效；没有移植旧文件 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_itinerary_intent.py` | 后续测试覆盖源用例并增加候选规范名/diff 断言；额外行为由集成实现覆盖 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_itinerary_provenance.py` | 后续测试保留源覆盖并增加 4 个来源/替换场景，且强化旧来源 revision 变化时的时长降级断言 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_tour_budget_api.py` | 已被集成版覆盖并扩展：保留预算查询/显式剩余时长 API 用例，并增加剩余时间命令的幂等重放、progress_version 和无效值校验 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_tour_progress_and_proposals.py` | 20 个集成测试包含源 10 个用例并新增恢复/预算/来源校验场景；后续实现替代 | snapshot=yes; integration=yes |
| `??` | `backend/app/tests/test_tour_proposal_catalog_staleness.py` | 后续目录版本验证实现不同；保留快照，语义由集成 staleness 测试验证 | snapshot=yes; integration=yes |
| `??` | `frontend/src/api/itinerary.js` | 快照只含提案创建/读取/应用；集成版增加持久 proposal 列表和 execution retry API，以 `Idempotency-Key`、CSRF token 和显式重复调用风险确认连接 durable worker；backend 当前提供对应 endpoints，worker 测试覆盖未知外部结果只能人工确认后重试。归类为后续 W02 集成扩展，不迁回旧客户端 | snapshot=yes; integration=yes |
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

当前 HEAD `a8c2837`，35 个 porcelain 状态路径；保全快照 `w02-preserved-snapshot`。以下按每个路径列出字节比较和语义判定；未完成的审查保留明确标记，不以分支祖先关系推断已合入。

| 状态 | 路径 | 分类 | 对照证据 |
|---|---|---|---|
| ` M` | `backend/alembic/env.py` | 仅 SQLAlchemy 模型导入换行/折行，不改变 Alembic metadata 内容 | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/router.py` | 集成版后续登记 itinerary 与 knowledge import/publication 路由；W02 旧行路由在当前集成树保留，旧文件不可覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/tour_sessions.py` | 旧 API 内联同步调用 `ItineraryIntentService`；集成版改为同事务创建 proposal reservation 与 `itinerary.proposal` durable job，返回 202，测试覆盖 replay/stale progress；属于后续实现替代，不覆盖快照 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/__init__.py` | 集成版扩展注册知识 workspace、V01 progress/proposal 模型和 tool execution 模型；后续模型注册实现替代，保留源版本 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/tour_session.py` | 集成版在 ItineraryProposal 增加 `base_snapshot_json` 与 `execution_job_id`；对应 merge/W02 migration 和 proposal recovery 测试覆盖字段用途；DB migration upgrade 仍未实跑 | snapshot=yes; integration=yes |
| ` M` | `backend/app/repositories/tour_session.py` | 后续仓储包含提案 reservation、锁和版本 fence；不以旧文件覆盖 | snapshot=yes; integration=yes |
| ` M` | `docs/ARCHITECTURE.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/COMPATIBILITY.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/REPO_MAP.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/plans/2026-10-28-ai-workbench-backlog.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/api/tourSessions.js` | W02/W02-V01 版本未传当前站点剩余分钟；集成版通过 `buildTourBudgetParams` 仅在有值时传 `current_stop_remaining_minutes`，保留显式 0。后端 Query 接受 `ge=0`，现有 Node 行为测试验证 null/undefined 省略及 0/正值保留（1 passed）；归类为与已集成剩余预算 API 对齐的后续扩展 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-tools.css` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/composables/useAudioPlayer.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/chat.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/tourSessions.js` | 集成版复用 `cloneJson`、proposal snapshot stale 检查、异步 apply 草稿协调和 progress refresh helpers；并加入 durable proposal 恢复/重试、open/save/progress/budget 请求代际保护、并发草稿保留。W02 store 与较新的 W02/V01 副本对比均没有这些最终协调边界；store/helper 定向 Node 行为集 43 passed，覆盖对应提案、迟到响应、保存与进度竞争 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/ChatView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/MapView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/RouteView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/5c81a1e74f2b_add_tour_progress_and_proposals.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/f1b4c9d76e20_add_tool_execution.py` | 被集成 migration merge 替代，不能单独移植：源父 revision=`e9f4c2b8016a`，集成父 revision=`8ab42c17d3e9`；集成版同时添加 itinerary proposal execution 字段 | snapshot=yes; integration=yes |
| `??` | `backend/app/api/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/models/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/repositories/tool_execution.py` | 后续实现扩展旧 repository：加入任务创建时 progress_version 检查、progress fence、事务内 flush/commit 选项和 unknown 外部结果处理；新增隔离 SQLite 测试覆盖创建时拒绝旧 progress 以及排队后进度更新时 claim 不发放 lease，真正同时 claim/进度提交的 race 仍未专项验证 | snapshot=yes; integration=yes |
| `??` | `backend/app/schemas/itinerary.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/schemas/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/` | 已逐项核验：`candidates.py` 与集成版逐字节相同；旧 `intent.py` 的 `result.diff` 被集成版按规范化 candidate 重算 diff 替代；`progress.py` 后续增加剩余预算命令、估算时长/过期截止时间判定；`provenance.py` 后续增加景点替换、目录修订及受影响路线段证据失效和 AI 时长归属。对应测试覆盖 `test_itinerary_intent.py`、`test_itinerary_progress.py`、`test_tour_budget_api.py`、`test_itinerary_provenance.py`；W02 旧差异保留在快照，不覆盖当前实现 | 4 个源文件；相同=1、不同=3、集成缺少=0；集成另有 `catalog.py`、`mutations.py`（排除 Python cache） |
| `??` | `backend/app/services/tool_execution/` | 六个文件已逐项比较：`commands.py`/`registry.py`/`runner.py` 扩展 `commit=False` 下的同事务结果持久化，`handlers.py` 注册持久 itinerary proposal worker，`worker.py` 在 CLI event loop 退出前 dispose engine；`__init__.py` 仅空白差异。已有回滚、proposal 重放、未知外部结果、worker CLI 生命周期覆盖；旧目录不覆盖集成目录 | 6 个源码/资料文件；相同=0、不同=6、集成缺少=0、集成额外=0（排除 Python cache） |
| `??` | `docs/research/` | 目录内有相同/不同/新增文件，需逐项核验 | 1 个源码/资料文件；相同=0、不同=1、集成缺少=0、集成额外=1（排除 Python cache） |
| `??` | `docs/selling-points/` | 目录内有相同/不同/新增文件，需逐项核验 | 1 个源码/资料文件；相同=0、不同=1、集成缺少=0、集成额外=2（排除 Python cache） |
| `??` | `docs/superpowers/plans/2026-10-29-v01-editable-itinerary.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/plans/2026-10-29-w02-durable-execution.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/plans/2026-10-29-w02-execution-ledger.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `frontend/src/api/itinerary.js` | W02 快照尚无 proposal list/retry 客户端；集成版增加 durable worker 列表和重试调用，服务端及 `test_unknown_external_result_requires_explicit_retry_confirmation` 覆盖风险确认。该功能属于 W02 集成后的持久任务能力，不从旧快照覆盖 | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/requestGeneration.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |

### Migration lineage 语义核验

- V01 `5c81a1e74f2b_add_tour_progress_and_proposals.py` 在源与集成树字节相同；集成 revision `8ab42c17d3e9` 将它与 speech metadata migration `c3b7e1d9a62f` 合并。
- W02 快照 revision `f1b4c9d76e20` 的父为 `e9f4c2b8016a`，且不添加 `itinerary_proposals.base_snapshot_json` / `execution_job_id`。集成树同 revision 改为父 `8ab42c17d3e9`，并增加这两列及索引；之后 `6e1a4c7d9b20` 检查/补齐遗失的 speech metadata，`7d2e93a5b601` 与 `91a0c5e2f347` 分别拒绝已知不完整的 W02/knowledge schema。此为有意处理分叉迁移历史的后续实现，旧 W02 migration 必须保留在快照，不得单独 cherry-pick。
- 临时 Python 环境没有 Alembic `command` API（`test_speech_metadata_migration.py` 收集时报 `ImportError`），故没有声称本轮实跑 Alembic 升级。该迁移链真实数据库往返仍待具备 Alembic 的隔离环境；此限制不影响单独运行的 W02 执行验收/worker 测试。

### W02 execution 源码差异核验

- 对照 `code/w02-worktree/backend/app/services/tool_execution/` 与集成目录的 6 个源码文件。集成版通过 `commit=False`、handler `persist_result` 和 runner 在完成 job 前调用 persister，将 proposal 完成与 execution 结果放在同一事务；`test_proposal_api_replays_same_request_and_conflicts_on_changed_payload` 还注入 enqueue 后失败并断言 proposal/job 回滚。旧 registry/runner 无这条事务回调路径，标为“已被后续实现扩展”，不复制覆盖。
- 集成 repository 增加 progress version 校验、目标 progress fence、锁及 unknown 外部结果路径。`test_changed_target_invalidates_running_lease...`、错误 fence、取消竞态、unknown retry 和 W02 runtime review 分别覆盖任务目标、lease/fence、取消/外部结果及 worker 恢复。此前未发现 create_job stale progress 的直接测试；本轮新增 `test_create_job_rejects_stale_tour_progress_version`，隔离 SQLite 验证进度已从 0 到 1 时拒绝旧 version 并不留下 ToolJob（1 passed）。claim 阶段恰逢 progress 改变的单独并发 race 仍需补测，因此 repository 差异只部分完成验证。
- 集成 repository 增加 progress version 校验、目标 progress fence、锁及 unknown 外部结果路径。`test_changed_target_invalidates_running_lease...`、错误 fence、取消竞态、unknown retry 和 W02 runtime review 分别覆盖任务目标、lease/fence、取消/外部结果及 worker 恢复。此前未发现 stale progress 的直接测试；本轮新增 `test_create_job_rejects_stale_tour_progress_version`（提交时拒绝旧版本且无 ToolJob）与 `test_queued_job_is_fenced_when_tour_progress_changes_before_worker_claim`（已排队后进度更新不发 lease，维护后标记 `target_progress_changed`），两个隔离 SQLite 测试均通过。claim 与 progress 提交真正同时竞争的时序仍未专项覆盖。
- `worker.py` 的 `_run_cli` finally dispose 由 `test_worker_cli_once_reads_explicit_isolated_database` 的 dispose/no-dispose 子进程路径覆盖。Migration 分叉仍按上文不可单独 cherry-pick 处理。

### W02 schema / router 差异补充核验

- W02 `models/tour_session.py` 与集成版唯一业务字段差异是 `ItineraryProposal.base_snapshot_json` 与 `execution_job_id`。前者用于恢复/核对 proposal 原始行程，后者链接持久任务；`test_tour_progress_and_proposals.py` 覆盖损坏 base snapshot 时 `diff_verifiable=False` 且拒绝 apply，`test_tool_execution_acceptance.py` 覆盖 proposal API 重放时 job ID 稳定。这些字段由集成版 f1 migration 补入，旧 W02 f1 migration 不含字段且父 revision 不同，所以标记为“被合并迁移及后续集成实现替代”，不能 cherry-pick 覆盖。
- W02 `alembic/env.py` 仅导入列表格式差异；`api/router.py` 在集成版增加 itinerary 与 knowledge import/publication 路由；`models/__init__.py` 注册 V01/knowledge/tool execution 模型。对应行为/注册属于已合并的后续子项目，不把 W02 文件覆盖到当前集成版。真实 Alembic upgrade/downgrade 仍因当前临时环境缺 Alembic command API 未验证。

### W02/V01 集成副本（`code/w02-integration`）

当前 HEAD `098553f`，39 个 porcelain 状态路径；保全快照 `w02-integration-preserved-snapshot`。以下按每个路径列出字节比较和语义判定；未完成的审查保留明确标记，不以分支祖先关系推断已合入。

| 状态 | 路径 | 分类 | 对照证据 |
|---|---|---|---|
| ` M` | `backend/alembic/env.py` | 仅 SQLAlchemy 模型导入换行/折行，不改变 Alembic metadata 内容 | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/router.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `backend/app/api/tour_sessions.py` | 旧 API 内联同步调用 `ItineraryIntentService`；集成版改为同事务创建 proposal reservation 与 `itinerary.proposal` durable job，返回 202，测试覆盖 replay/stale progress；属于后续实现替代，不覆盖快照 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/__init__.py` | 集成版扩展注册知识 workspace、V01 progress/proposal 模型和 tool execution 模型；后续模型注册实现替代，保留源版本 | snapshot=yes; integration=yes |
| ` M` | `backend/app/models/tour_session.py` | 已由 durable proposal schema 替代：集成版增加 `base_snapshot_json`/`execution_job_id`，merge migration 与 recovery/replay 测试证明用途；Alembic upgrade/downgrade 仍未实跑 | snapshot=yes; integration=yes |
| ` M` | `backend/app/repositories/tour_session.py` | 后续仓储包含提案 reservation、锁和版本 fence；不以旧文件覆盖 | snapshot=yes; integration=yes |
| ` M` | `backend/app/schemas/itinerary.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| ` M` | `backend/app/services/itinerary/progress.py` | 后续进度版本及状态 fence 实现不同；相关行为由集成回归覆盖 | snapshot=yes; integration=yes |
| ` M` | `docs/ARCHITECTURE.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/COMPATIBILITY.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/REPO_MAP.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/plans/2026-10-28-ai-workbench-backlog.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `docs/superpowers/plans/2026-10-29-v01-editable-itinerary.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/api/tourSessions.js` | 与 W02 旧客户端相同，缺少当前站点剩余分钟查询参数；集成版补入可省略空值且保留 0 的 `current_stop_remaining_minutes`，后端 Query 与 Node 测试（1 passed）覆盖契约 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/assets/guide-tools.css` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/composables/useAudioPlayer.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/chat.js` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/stores/tourSessions.js` | 集成版在较新的 W02/V01 store 上增加 open/save/progress/budget 请求代际保护、重复时间戳提案选择、waiting_user 手动重试确认和异步编辑协调；43 项定向 Node 行为测试全部通过，覆盖迟到响应、草稿保留、进度刷新和提案恢复/重试边界 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/ChatView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/MapView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| ` M` | `frontend/src/views/tourist/RouteView.vue` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/5c81a1e74f2b_add_tour_progress_and_proposals.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/alembic/versions/f1b4c9d76e20_add_tool_execution.py` | 被集成 migration merge 替代，不能单独移植：源父 revision=`e9f4c2b8016a`，集成父 revision=`8ab42c17d3e9`；集成版同时添加 proposal execution 字段 | snapshot=yes; integration=yes |
| `??` | `backend/app/api/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/models/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/repositories/tool_execution.py` | 后续实现扩展旧 repository：幂等回放、lease/fence、取消、同事务持久化和 progress version 保护；两项隔离 SQLite stale progress 行为测试已补，真正同时 claim/进度提交的 race 未专项验证 | snapshot=yes; integration=yes |
| `??` | `backend/app/schemas/tool_execution.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/candidates.py` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/intent.py` | 源实现被后续实现替代：集成版基于规范化后的 candidate 计算 diff；没有移植旧文件 | snapshot=yes; integration=yes |
| `??` | `backend/app/services/itinerary/provenance.py` | 源实现被后续实现替代并扩展：集成版处理景点替换、目录修订变更、AI 时长归属和受影响路线段证据失效；没有移植旧文件 | snapshot=yes; integration=yes |
| `??` | `backend/app/services/tool_execution/` | 后续执行目录已扩展同事务 proposal persistence、正式 handler 和 worker engine 生命周期；与 W02 表中六文件语义审计一致，未覆盖旧目录 | 6 个源码/资料文件；相同=4、不同=2、集成缺少=0、集成额外=0（排除 Python cache） |
| `??` | `backend/app/tests/test_tool_execution_acceptance.py` | 原 W02 工作树无此文件；测试仅见于后续 W02/V01 快照并扩充于当前集成树 | snapshot=yes; integration=yes |
| `??` | `docs/research/2026-10-29-w02-durable-execution-research.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/selling-points/` | 目录内有相同/不同/新增文件，需逐项核验 | 1 个源码/资料文件；相同=0、不同=1、集成缺少=0、集成额外=2（排除 Python cache） |
| `??` | `docs/superpowers/plans/2026-10-29-w02-durable-execution.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/plans/2026-10-29-w02-execution-ledger.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `docs/superpowers/specs/2026-10-29-w02-durable-execution-design.md` | 同路径存在但内容不同；需语义审查 | snapshot=yes; integration=yes |
| `??` | `frontend/src/api/itinerary.js` | W02/V01 副本已有 proposal list/retry API；集成版再增加 request `AbortSignal` 传递，并在客户端强制 `confirmDuplicateRisk === true` 后才发送 retry。后端 retry schema/repository 和未知外部结果人工确认测试与之对应；归类为集成增强，不是未合并功能 | snapshot=yes; integration=yes |
| `??` | `frontend/src/utils/requestGeneration.js` | 已合并（当前内容与集成树相同） | snapshot=yes; integration=yes |
