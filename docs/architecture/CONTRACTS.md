# 当前接口与状态边界

当前以实际代码和 OpenAPI 为准；下列是集成核对提纲，不是已统一的新协议。

- 问答：`backend/app/api/chat.py`、`services/qa/stream_events.py` 定义 SSE；消费者是 `frontend/src/composables/useSSEStream.js` 和 `stores/chat.js`。协议修改要同时核对服务端、解析及消费者，保留停止、重试与迟到结果隔离。
- 游览：`api/tour_sessions.py`、`repositories/tour_session.py` 管理 owner/site、修订和游览进度；客户端 `stores/tourSessions.js` 维护手动草稿与服务端版本，不能让提案恢复覆盖用户编辑。
- 剩余时间：进行中的游客可通过 `set_remaining_budget` 进度命令明确确认 1–720 分钟；新截止时间以服务端接收时间为锚，进度版本与事件同时更新，幂等重放不重置锚点。它不同于行程草稿的总时长；自然语言提案与此命令的联合确认尚未实现。
- 执行：`api/tool_execution.py` 和 `services/tool_execution/registry.py` 定义受控任务，`runner.py` 管理租约与 fence；外部结果未知时等待用户确认重复调用风险。每个任务、会话、交互和数字人表现的状态不同，不应把它们压成一个共享对象。
- 证据：知识发布与检索链路由 `services/knowledge/`、`services/rag/` 和 QA pipeline 承担；需继续验证来源与消息绑定、发布后的缓存与语音失效。
- RAG 来源事件保留检索结果中可用的 `entry_id`、`revision_id` 和 `chunk_id`，均可为空；数据库回退、历史缓存和 FAQ 可能没有片段 ID。它们用于追踪知识版本，不代表来源真实、片段支持回答或已完成逐句引用核验。旧索引元数据不因升级自动修复，须隔离检查并重建。
- 全量索引重建与新版发布使用同一索引目录的跨进程写锁；旧 processed-data 导入及旧版本进程未纳入锁，真实 Chroma/多进程及 Windows 仍未验收。重建时暂须停掉所有写入与发布 worker，细节见 `docs/development/PROGRESS.md`。
- 图片问答：`vision_context.confirmation` 可携带游客明确选择的 `site_id`、`spot_code`、`published_revision_id`；服务端重新核验当前站点已发布目录后才限定检索。未确认时开放检索并提示；选项已更新、下架或跨站点时拒绝。选中景点不证明照片识别正确，且知识库当前仅支持单站点边界。
- W02 迁移、启动和未验证边界见 [集成记录](../development/W02_INTEGRATION.md)。新增协议须说明版本、序列化、错误和取消语义，并增加兼容测试。
