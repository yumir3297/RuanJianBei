# W02 执行记录

日期：2026-10-30。分支：`codex/w02-v01-integration`。代码基线：V01 已提交版本 `098553f34cf4991240742661c4174e41f60ef0c6`，并将其原工作树的未提交源代码快照复制到本分支；未复制测试与 `sources/`。原 V01、原 W02 内核工作树和主工作区均未修改。

## 已写入的代码

- 持久执行模型、Alembic revision `f1b4c9d76e20`、typed enqueue、固定版本 registry、单 `run` step runner、独立 worker 与游客范围查询/取消/重试 API。
- 首个生产 handler 为 V01 `itinerary.proposal`。V01 API 完成身份、CSRF、景区目录、草稿摘要和进度校验后，创建 proposal reservation 与 W02 job；两者在同一事务提交。
- worker 调用 V01 现有意图解析和候选校验。候选提案与 job 成功状态在同一事务提交；提案保存服务端规范化草稿基线、游客提交摘要和关联 job ID。
- 游客提交摘要用于 V01 确认边界；任务另保存规范化快照摘要，避免服务端重建来源/证据后误判原始草稿不匹配。
- 游客关页只停止轮询，worker 继续处理。重开游览可恢复最近的执行中、待确认或可审阅提案；`waiting_user` 显示外部调用结果不明及重复调用费用风险，用户确认后才能重试。
- job 绑定行程修订、进度版本与目录摘要。行程/进度变更会失效活动 job；V01 apply 仍由游客明确确认，并重新核对当前目录、行程与进度。
- PostgreSQL 领取用 `FOR UPDATE SKIP LOCKED`；SQLite 使用条件更新，限单 worker。当前 itinerary handler 不允许自动重试，避免不确定供应商结果时静默重复调用。

## 尚未完成

- 全量 backend suite 未运行。进程崩溃恢复、取消竞争、SQLite 并发、PostgreSQL 多 worker、真实模型供应商调用、手机浏览器和弱网均未验证。
- 目前只有一个 `run` step 和游客 itinerary handler；运营内容生产、发布流程、通用任务面板、事件裁剪与 30 天 job 清理尚未实现。
- W02 提案 job 的输入包含单次游客改线请求及结构化草稿，受 1 MiB 上限约束；不复制聊天历史、照片、音频或供应商凭据。

## 2026-10-30 轻量验收结果

- 在隔离 SQLite 数据库应用到 `f1b4c9d76e20`，核对五张 W02 表、索引和外键；回退到 `5c81a1e74f2b` 后 W02 表全部移除且 V01 `itinerary_proposals` 保留。
- 选取 V01 行程/身份/提案相关测试并加入两条 W02 验收用例，合计 `36 passed`。测试覆盖 worker 领取并启动 attempt、proposal 首次创建/相同幂等请求重放/不同内容冲突；V01 测试文件从原 `v01-worktree` 执行，未复制到本分支。
- 验收测试定位并修复两个问题：SQLAlchemy 目标有效性子查询被外层 join 错误自动相关；proposal 幂等重放 rollback 后读取过期身份 ORM 属性。对应修复在 repository 查询和 proposal API 中。
- `npm ci --no-audit --no-fund` 后 `npm run build` 成功，转换 2,200 个模块；Vite 提示若干 chunk 大于 500 kB。
- 本地桌面浏览器通过 Vite + 关闭模型预热的 API 进程连接隔离 SQLite：路线页可打开，空白游览创建成功，列表刷新和页面 reload 后游览仍出现在列表；推荐降级显示离线预设路线。浏览器原有的当前游览 ID 在临时数据库中不存在时先显示无法打开提示，刷新列表后恢复，属于隔离验收环境中的旧 ID。
- 本轮没有运行真实模型供应商或 W02 worker 端到端浏览器流程，也未覆盖 PostgreSQL 多 worker、崩溃/取消故障注入、手机浏览器和弱网。

## 实施裁定

- API 保持 `/api/tour-sessions/{session_id}/executions/...`，使用 W01 游客身份、景区和游览归属校验；不提供任意工具的通用创建接口。
- 采用 V01 作为首个实际 handler，因为它有真实业务候选、明确的游客确认边界和已发布目录校验。为避免跨层双写，提案预留/任务入队及候选/任务完成分别共用数据库事务。
- 外部模型调用开始前持久化 `may_have_run`。worker 在此外部调用前中断可重新排队；开始后结果不确定则进入 `waiting_user`，不能自动重试。
- 单 `run` step 满足当前 V01 提案的阶段边界；未来多阶段导入、发布或讲解流程需先定义领域事务适配器。
- 本轮按用户要求执行轻量验收；36 条目标测试通过，不代表完整 W02 故障矩阵或全量 backend suite 通过。

## 静态核验

- `git diff --check`：通过；未跟踪文本文件逐行检查未发现行尾空白。
- Python AST：24 个变更 Python 文件通过；`node --check`：6 个变更 JavaScript 文件通过。
- `python3 scripts/check_repo_map.py`：通过，共核对 8 份文档和 82 条已注册 HTTP 路由。
- 本轮 targeted pytest：36 passed；`npm run build`：成功；SQLite Alembic upgrade/downgrade：成功。
- 前端构建存在 Vite bundle 大小提示；本地浏览器 smoke 仅覆盖游览创建/列表/reload，没有覆盖 worker 恢复任务卡。自动化故障恢复、PostgreSQL 多 worker 和真实供应商行为仍未运行验证。
