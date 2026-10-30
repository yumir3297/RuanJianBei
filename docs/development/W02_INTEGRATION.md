# W02 集成记录

2026-10-30，集成到 `codex/competition-integration` 的 V01、K01、W01 和 F01 快照。行程提案通过持久任务异步执行；浏览器恢复查询，重试外部调用结果不明的任务必须明确确认风险。浏览器停止等待不等同于取消服务端任务。运行 worker：在 `backend/` 使用 `python -m app.services.tool_execution.worker`，API 进程不自动启动 worker。

迁移 `f1b4c9d76e20` 的父节点调整为整合语音与行程迁移的 `8ab42c17d3e9`，此调整以 W02 原迁移尚未部署到持久数据库为前提。已有独立 W02 数据库时不得直接假设能平滑升级，须先检查其 alembic_version 与实际 schema，单独制定迁移方案。隔离 SQLite 已验证新链升级及 W02 回退再升级。

自动化覆盖原子回滚、租约 fence、旧版本失效、跨游览迟到响应、未知外部调用需确认重试。测试使用 fake 模型，不证明真实供应商或完整浏览器流程可用。PostgreSQL 多 worker 竞争、崩溃恢复、手机和弱网仍待验收。
