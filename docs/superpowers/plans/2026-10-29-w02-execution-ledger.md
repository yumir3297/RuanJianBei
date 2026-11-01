# W02 执行记录

> 历史记录：此文件保留 W02 初始开发时的状态，不是当前功能清单或约束。当前集成和验证边界见 [W02 集成记录](../../development/W02_INTEGRATION.md) 与 [开发进度](../../development/PROGRESS.md)。

日期：2026-10-29。分支：`codex/w02-durable-execution`。基线：W01 `a8c283771e3176f3c05fb95ef76631f57566bc15`。

## 已写入的内核代码

- 新增 `tool_jobs / tool_steps / tool_attempts / tool_events / tool_command_receipts` 模型和 Alembic revision `f1b4c9d76e20`，下游基线为 W01 head `e9f4c2b8016a`。
- 增加受限的 typed enqueue command、固定版本 handler registry、一个 `run` step 的 runner 和独立 worker 命令。当前 registry 为空；未接入真实业务流程。
- 增加游客游览范围的列表、详情、事件、取消和重试 API。没有任务创建 HTTP 路由，也没有前端任务卡。
- 使用 W01 游客身份、site/session ownership、Cookie/CSRF 和 revision。更新 revision 会使旧活动任务 stale；软删除取消活动任务；永久删除清除关联执行记录。
- worker 对 PostgreSQL 使用 `FOR UPDATE SKIP LOCKED` 领取；SQLite 使用条件更新，部署限制为单 worker。结果写入要求仍持有当前 fence 和目标 revision。
- 自动重试默认关闭，handler 必须显式声明安全后才允许有界重试；未知外部结果进入 `waiting_user`，人工重试需要确认重复风险。

## 未完成的产品闭环

- 没有真实 handler、业务创建命令入口、游览/运营执行 UI 或 O01 内容生产接入。
- `progress_version` 仅记录，不校验；W01 当前没有独立进度修订。job/event 30 天清理和事件裁剪尚未实现。
- migration 未应用；自动化测试、进程崩溃恢复、取消竞争、SQLite 并发和 PostgreSQL 多 worker 均未运行验证。
- 本次只按约束做静态编译与 diff whitespace 检查；不能据此声称 migration、恢复或端到端功能通过。

## 实施裁定

- Ruling: API 采用 `/api/tour-sessions/{session_id}/executions/...`，以 W01 游览范围校验身份、景区和目标版本；设计 §8 给出此接口，优先于计划早期列出的通用 `/api/tool-jobs/{job_id}`。如果后续确需跨游览统一运营查询，需要单独的运营鉴权 API。
- Ruling: 首批 handler 仅支持一个固定 `run` step；先交付可验证的任务/租约/fence 边界，不凭空引入 DAG 或业务成果写入。代价是目前无法展示多阶段业务进度，需后续按业务 adapter 扩展。
- Ruling: 不新增或运行自动化测试，遵守本任务的开发者约束；验证范围因此停在静态检查，计划中的行为验收仍未完成。
- Ruling: 不派发新的 review 子代理，遵守本任务的开发者约束；以下作者自查弱于独立审查。

## 静态核验

- `python3 -m compileall -q backend/app backend/alembic/versions/f1b4c9d76e20_add_tool_execution.py`：通过，退出码 0；仅证明 Python 语法可编译。
- `git diff --check`：通过；该命令检查 tracked diff。新文件的 whitespace 尚未由该命令覆盖。
- `scripts/check_repo_map.py`、migration、自动化测试、数据库和并发/恢复验证：未运行。
