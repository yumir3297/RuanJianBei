# 当前架构索引

代码核对基线 `fba5cbe`，2026-11-01；后续提交以 Git 历史和 [开发进度](../development/PROGRESS.md) 为准。此索引描述源码结构，不代表真实供应商或设备已验收。完整入口见 [功能地图](../REPO_MAP.md)。

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

- `backend/app/api/router.py` 注册聊天、识景、语音、知识和游览任务；`services/qa/pipeline.py` 与 `intent_router.py` 是问答执行入口。FAQ、缓存、RAG 和降级路径需在后续优化中保留。
- `services/tool_execution/worker.py` 是单独进程；执行器不是自动嵌入 API。它目前只注册 `itinerary.proposal`，不能称为通用多 Agent 平台。
- `frontend/src/stores/tourSessions.js` 负责任务与提案恢复；`useAudioPlayer.js` 管理互斥播放与内容时间轴；`ThreeAvatar.vue` 是 Three.js/VRM 视图。口型是基于文本拼音，非音频驱动模型。
- 已有真实供应商适配，但默认配置包含 stub。历史单次调用不代表当前环境的真实供应商已经可用；景区材料真实性与许可、真实 GPS/客流和手机浏览器能力需分别核验。

`fba5cbe` 本地隔离测试：后端 473 通过、3 跳过；前端 132 通过。跳过项和真实服务边界见进度记录；测试包含替身，不能证明真实模型、语音或移动浏览器可用。历史 SQLite 迁移往返及 PostgreSQL 双会话专项结果见 [W02 集成记录](../development/W02_INTEGRATION.md)，不代表生产数据库升级或多进程故障恢复已验收。

集成分支位于独立副本 `integration-work/v01`，原工作区仍有未提交修改，尚未将集成结果合回原工作区。`snapshot-main` 是原主工作区 Git 可见修改的保全快照；合回前还须重新核对原目录是否变化、各数据库迁移状态与运行环境，不能用快照覆盖用户当前文件。
