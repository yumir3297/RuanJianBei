# 当前架构索引

代码核对基线为 `codex/competition-integration` 分支（核对于 2026-11-05）；具体提交以 Git 历史和 [开发进度](../development/PROGRESS.md) 为准。问答仍由显式 `QAPipeline` 驱动，FAQ/缓存/RAG 快速通道与 SSE、HTTP/流式 TTS 并行调度；情绪、表达策略和游客记忆是每次流请求的 ContextVar 状态。`pipeline.py` 现为 989 行，主生成循环依然负责 epoch fence、LLM/TTS mux、回答与事件顺序、降级补读、缓存及持久化；这些关键路径尚未整体移出 Pipeline。此索引描述源码结构，不代表真实供应商或设备已验收。完整入口见 [功能地图](../REPO_MAP.md)。

```mermaid
flowchart LR
  UI[Vue 游客端：文字、图片、语音、地图] --> API[FastAPI 路由]
  API --> QA[QAPipeline：意图、FAQ、缓存、RAG、生成]
  QA --> SSE[SSE 文字与语音事件]
  SSE --> Player[播放器及 Three.js / VRM 数字人]
  API --> Tour[行程与游览版本]
  Tour --> DB[(数据库：提案与工具任务)]
  Worker[独立工具 worker] --> DB
  Worker --> Model[模型供应商 / 行程提案]
  API --> Knowledge[草稿、发布、检索索引]
```

- `backend/app/api/router.py` 注册聊天、识景、语音、知识和游览任务；`services/qa/pipeline.py` 与 `intent_router.py` 是问答执行入口。无状态画像提取位于 `services/qa/request_profile.py`，确定性路线回答位于 `services/qa/route_fast_path.py`，整小时预算解析位于 `services/qa/route_constraints.py`；`services/qa/vision_evidence.py` 将游客确认与当前发布目录、检索范围绑定，`services/qa/answer_fast_paths.py` 将最新开放时间/票价不可核实规则、FAQ 直接回答、受众改写证据和共享缓存资格解析为独立决策，`services/qa/evidence_retrieval.py` 将检索片段和带修订/分块 ID 的来源记录成对返回，`services/qa/speech_event_adapter.py` 将 TTS 数据转换为 SSE 音频、字幕和数字人事件。
- 流生命周期辅助件现拆在 `services/qa/stream_lifecycle.py`（`StreamProducerGroup` 管理 LLM/TTS producer task 与流式 session 的取消、join、关闭；`AudioTaskGroup` 管理并发 HTTP 音频任务）、`stream_mux.py`（LLM/TTS mux 状态和交付决策）、`streaming_tts_buffer.py` / `streaming_tts_controller.py`（流式 TTS 文本缓冲、发送、finish 和异常降级）、`queued_stream_events.py`（HTTP TTS 生成的 SSE 音频事件队列）及 `stream_answer.py`（答案累计与可播句切分）。Pipeline 保留兼容入口，并继续控制 epoch 检查、mux 消费循环、FAQ/RAG 的文字与来源事件顺序、流式/HTTP TTS 调度与偏移、缓存和持久化；FAQ、缓存、RAG、证据绑定和降级路径必须在后续拆分中保持。
- 复杂行程操作由持久任务 worker 处理，普通问答不进入通用 Supervisor。后续架构选择仍是显式 Pipeline，不引入运行时 Agent 框架。
- `services/tool_execution/worker.py` 是单独进程；执行器不是自动嵌入 API。它目前只注册 `itinerary.proposal`，不能称为通用多 Agent 平台。
- `frontend/src/stores/tourSessions.js` 负责任务与提案恢复；`useAudioPlayer.js` 管理互斥播放与内容时间轴；`ThreeAvatar.vue` 是 Three.js/VRM 视图。口型是基于文本拼音，非音频驱动模型。
- 已有真实供应商适配，但默认配置包含 stub。历史单次调用不代表当前环境的真实供应商已经可用；景区材料真实性与许可、真实 GPS/客流和手机浏览器能力需分别核验。

`63855db` 后，Pipeline、聊天 SSE 与游客记忆相关回归共 55 passed、1 warning；其中共享 Pipeline 并发回归在旧实现下按预期失败，在请求状态隔离实现下通过。完整集成分支回归尚未重跑；替身测试也不能证明真实模型、语音或移动浏览器可用。历史 SQLite 迁移往返及 PostgreSQL 双会话专项结果见 [W02 集成记录](../development/W02_INTEGRATION.md)，不代表生产数据库升级或多进程故障恢复已验收。

集成分支位于独立副本 `integration-work/v01`；V01、W01、W02、K01 的功能提交均已进入集成历史，其中 durable itinerary execution 后续又增加取消/外部调用 fence、提案幂等重放、目录锁与 worker 生命周期修正。V01 和两个 W02 原始 worktree 仍有未提交差异；相关快照分支保留为 `3805943`、`48ef626`、`5433557`，W02 较早快照与集成版的共享文件有差异，不能作为覆盖来源。`/private/tmp/ai-guide-phase3` worktree 路径已不存在，Git 将它标为 prunable；对应功能分支已在集成历史中，本次没有清理该登记。原主工作区 95 个未提交路径仍保留，快照为 `4acaa53` 和 `e115eab`，尚未将集成结果合回原工作区。`frontend/node_modules` 是本机软链接，不属于源码提交。主工作区 AI/SSE/TTS 流式差异大多已在集成版由后续提交实现；主工作区旧基线还缺少集成版的请求状态隔离、知识版本 fence、图片确认核验和路线约束保护，因此不可用主工作区文件覆盖集成版。合回原工作区前仍须重新核对原目录与目标迁移状态。
