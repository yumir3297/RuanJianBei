# W02 工具执行与任务恢复：调研与接入依据

日期：2026-10-29。状态：完成资料与局部源码阅读；隔离分支已实现 W02 持久内核代码，未运行外部项目，也未接入生产业务 handler。
用户已选择：现有数据库 + 小型执行器。内核范围及缺口见 [W02 设计](../superpowers/specs/2026-10-29-w02-durable-execution-design.md)和[实施计划](../superpowers/plans/2026-10-29-w02-durable-execution.md)。

## 1. 调研结论

W02 应提供持久执行记录、明确的重试边界和恢复前校验，复用 Vue/Pinia、FastAPI、SQLAlchemy 与业务服务。普通问答保持现有流式链路；长任务由独立 worker 执行，浏览器负责查询和操作。

首要区别是：恢复浏览器展示、恢复已保存业务成果、恢复后台计算是三种能力。保存 job_id 或开启 asyncio.Task 不足以同时提供这三种能力。

## 2. 一手资料和源码阅读

以下 GitHub 链接本次通过连接器读取；均为阅读当日 main 分支，未固定外部提交，不作为可复现实测基线。若后续采用依赖，必须另行固定版本并核对许可证。本次不复制外部实现。

| 资料 | 本次实际阅读 | 借鉴及边界 |
|---|---|---|
| [Temporal Python 样例](https://github.com/temporalio/samples-python/blob/main/hello/hello_cancellation.py) | `never_complete_activity`、`CancellationWorkflow.run`；另读 [retry 样例](https://github.com/temporalio/samples-python/blob/main/hello/hello_activity_retry.py) | 长操作应有超时和合作式取消。项目采用有界重试，不照搬样例的长期重试配置 |
| [Temporal Activity 定义](https://docs.temporal.io/activity-definition) | 幂等章节 | 调度可靠不代表外部副作用只发生一次；业务写入仍需幂等 |
| [DBOS 恢复源码](https://github.com/dbos-inc/dbos-transact-py/blob/main/dbos/_recovery.py) | `_recover_workflow`、`recover_pending_workflows` | 恢复也走统一领取入口，避免恢复线程和普通 worker 各自运行一遍 |
| [DBOS 系统库源码](https://github.com/dbos-inc/dbos-transact-py/blob/main/dbos/_sys_db.py) | `reenqueue_for_recovery` 及 `call_function_as_step` 局部 | 数据库条件更新、已有执行结果复用；不是阅读或验证了整个 DBOS 并发实现 |
| [DBOS 工作流保证](https://docs.dbos.dev/python/tutorials/workflow-tutorial) | workflow ID、确定性、保证章节 | 区分步骤重试与事务提交保证；不能把数据库事务的保证扩展为所有供应商调用的保证 |
| [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) | checkpoint 与 pending writes 章节；[基类源码](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py) 的 `CheckpointTuple`、`put_writes/aput_writes` | 单步结果与整趟任务状态分开保存，复用已完成且仍适用的步骤 |
| [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | 恢复节点与人工输入章节 | 人工确认应绑定明确候选；恢复可能从节点开头重执行，不能在确认前夹带不可重复写入 |
| [Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html) | acknowledgment、幂等、worker 丢失和超时段落 | 队列重投不等于业务恰好一次；只引入 Celery 不能代替业务恢复设计 |
| [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | 用途与 caveat | 可用于响应后的同进程工作；本项目的持久领取和恢复必须另行落库 |
| [PostgreSQL SELECT](https://www.postgresql.org/docs/current/sql-select.html) | locking clause 的 `SKIP LOCKED` | 可用于任务表并发领取；不是通用一致性读取，也不代替租约与写回检查 |
| [SQLite 隔离](https://sqlite.org/isolation.html) | 单写者、`BEGIN IMMEDIATE` | SQLite 验证路径与 PostgreSQL 不同，不能用 SQLite 单 worker 通过证明生产多 worker 正确 |

## 3. 本项目核对结果

当前主目录 HEAD 为 `672a104`，存在大量其他任务的未提交改动。本次只读业务代码，不移动或合入其他工作树。

| 能力 | 证据 | 接入决定 |
|---|---|---|
| ASR/视觉幂等 | `backend/app/services/idempotency.py`，5 分钟进程内 task/结果协调 | 保留短请求优化；不能当持久任务表或跨进程唯一约束 |
| 容量保护 | `backend/app/services/capacity.py` | 只限制进程并发；后台 worker 要另有共享领取和排队限制 |
| 发布请求恢复 | `frontend/src/utils/publicationRecovery.js` | 保留同一逻辑操作的键与选择版本；查询服务端后再决定后续动作 |
| SSE 和停止隔离 | `frontend/src/composables/useSSEStream.js`、`frontend/src/stores/chat.js` | 继续承担实时问答；不将断开 SSE 等同取消持久作业 |
| 数据库 | `backend/app/db/session.py`、`backend/requirements.txt` | 复用 SQLAlchemy/Alembic，明确 PostgreSQL 和 SQLite 差异 |
| W01 | 只读核查 `codex/w01-tour-sessions`，HEAD `a8c2837` 的 models/repository/API | 已有 Cookie 身份、归属过滤、修订唯一约束、条件更新、7 天持久幂等回执；不代表已合入主目录或本次已验收 |
| V01 | 主工作区中的 V01 设计草案 | 提案、进度和确认由 V01 拥有；其“崩溃后失败、不承诺后台继续”保持不变，除非另行批准变更 |
| K01 | 主工作区中的知识工作区设计和发布恢复补丁 | 首批只做任务投影和业务适配；未读取 K01 当前实现，不虚构其字段、租约或 API 已可复用 |

W01 的 TourSession 是业务任务，不能用作每次模型/工具执行的 job。聊天 session_id 也不能当作游客授权凭据。W02 不能把后台查看统计的权限扩展为读取游客照片和位置。

## 4. 方案比较与选择

| 路径 | 适配收益 | 成本与局限 | 结论 |
|---|---|---|---|
| 现有 SQL + 小型执行器 | 能沿用业务事务、权限和版本；部署组件较少 | 我们负责领取、租约、重试、升级兼容与故障验证 | 用户已选择 |
| DBOS | 直接利用持久执行与步骤记录 | 需要验证依赖、数据库边界、SQLAlchemy 事务及现有迁移整合 | 保留为将来评估路径 |
| Temporal | 适合复杂长周期、跨服务执行 | 增加服务和 worker 运维；领域权限/版本仍需自己实现 | 首轮不引入 |

LangGraph 可用于以后复杂意图流程，但现有确定流程没有引入图框架的必要；Celery 可成为未来调度后端，不能替代领域状态与确认。

## 5. 作为创新卖点的开发方向

建议名称：**面向现场变化的连续伴游恢复**。

组合价值来自“任务步骤 + 行程修订 + 游览事实 + 知识发布版本 + 人工确认”一起校验。通用持久执行已有成熟先例；本项目应证明景区场景下恢复仍然正确，而非宣称发明任务队列。

1. 恢复有依据：展示真实步骤、结果和失败点，不用模型推理文本模拟执行进度。
2. 恢复不覆盖：游客手动改线、完成/跳过景点后，旧结果必须重新校验，必要时转为待复核。
3. 恢复不复活过期知识：保存历史引用，读取与应用仍检查当前发布可见性。
4. 恢复不默认重做所有计算：已保存且输入与内容版本仍适用的步骤可复用；不确定的付费调用先核查或征得重试决定。
5. 游客与运营可以共享执行证据结构，同时各自保留成果归属和发布权限。

## 6. 评测与演示建议

对照：A 现有请求级恢复；B 持久作业但整任务重试；C 持久步骤 + 版本校验。相同输入、故障注入点、provider mock 与代码版本；真实供应商调用另测并记录成本。

冻结 30 个验收场景：领取/重启 6、重复/结果不确定 6、取消/迟到 6、人工编辑/进度/发布变化 6、身份/删除/事件恢复 6。开发样本与冻结样本分开。

指标：恢复成功率、成果重复数、旧结果覆盖数、已游事实保持率、内容失效阻断率、重复步骤/供应商调用数、恢复时延 p50/p95、每成功任务用量。仅拒绝所有恢复不能获得高恢复质量结论，需报告可恢复样本的实际完成率。

演示：已完成检索 → 生成讲解时中断 worker → 游客在另一标签页完成一个点 → 恢复显示已完成步骤 → 对旧进度提示复核 → 新确认后继续。另演示运营下架引用内容，恢复时停止沿用。

这些是待实现、待测量的目标。没有硬件、网络、数据库、版本与故障日志，不写性能提升比例；赛题评分规则尚未归档，不能断言创新得分。
