# W02安全增量合入分析

2026-10-30；只读比较 `integration-work/v01` 与 `integration-work/w02-integration` 的实际文件内容，不以Git提交记录推定未提交快照。排除.git、node_modules、虚拟环境、缓存与构建产物；仅写本报告。当前V01已经包含最新主线语音/安全/媒体校验/前端恢复改动；W02携带的旧V01不可整体覆盖。

## 结论与合入边界

以 `integration-work/v01` 为目标基线，只引入“行程提案的持久工具执行”增量。W02不是另一套完整更新版本：其chat、voice、vision、播放器、预算等大量差异是旧实现，覆盖会撤回最新功能与安全修复。保留V01现有全部新增文件与测试。

W02新增12个源码/迁移/测试文件：

- `backend/alembic/versions/f1b4c9d76e20_add_tool_execution.py`
- `backend/app/api/tool_execution.py`
- `backend/app/models/tool_execution.py`
- `backend/app/repositories/tool_execution.py`
- `backend/app/schemas/tool_execution.py`
- `backend/app/services/tool_execution/{__init__,commands,handlers,registry,runner,worker}.py`
- `backend/app/tests/test_tool_execution_acceptance.py`

以上新文件可作为完整单元引入后审查；共享文件必须逐段合并，不能复制整棵backend/frontend。

## 能力、契约及关键共享文件

| 位置 | 应引入的W02增量 | 必须保留的目标侧行为/风险 |
|---|---|---|
| `backend/app/api/router.py` | 注册tool_execution router | 保留现有chat replay等路由；新router内路径已含tour-sessions，避免二次重复prefix |
| `backend/app/models/__init__.py`、`backend/alembic/env.py` | 导入ToolJob/Step/Attempt/Event/CommandReceipt等模型供metadata识别 | 保留最新ChatLog语音metadata模型 |
| `backend/app/models/tour_session.py` | ItineraryProposal增加base_snapshot_json、execution_job_id | 不回退V01已有模型字段 |
| `backend/app/api/tour_sessions.py` | proposals POST由同步执行变为202+原子预留proposal/job；增加GET proposals及恢复查询 | 原样保留budget的current_stop_remaining_minutes参数；保留已有草稿digest、progress version、provenance、catalog与owner/site校验 |
| `backend/app/repositories/tour_session.py` | reserve/complete支持commit=False、find_proposal_replay、proposal携带base_snapshot/execution状态、list_proposals；修订/进度变化标记job失效、清理session关联任务 | W02涉及多个现有写路径，漏一个会让旧任务继续写入；不能把reserve/job分成两个commit；维持V01幂等、版本冲突与应用提案的校验 |
| `frontend/src/api/itinerary.js` | 增加execution retry接口及proposal列表接口 | 保留AbortSignal及现有budget参数构造 |
| `frontend/src/stores/tourSessions.js` | openSession恢复未完成提案、resumeProposal轮询、retryProposal、base_snapshot恢复 | 不能覆盖V01 latestRequest/proposalSnapshot/cloneJson等工具；保留当前点剩余时长输入、旧请求隔离、草稿变化防误应用 |
| `frontend/src/views/tourist/ChatView.vue` | waiting_user状态、明确重复调用费用风险后重试及恢复卡 | 保留刚合入的主线重播、倍率语速、metrics、会话隔离、route/map布局、V01意图识别与diff组件 |
| `frontend/src/views/tourist/RouteView.vue` | 必要的提案执行状态入口 | 保留V01预算和当前点剩余时长控件，不能覆盖整文件 |

`backend/app/services/tool_execution/handlers.py`当前仅注册itinerary.proposal v1；retry_safe=False、max_attempts=1、recovery_mode=manual_retry。模型调用前持久标记external_call，异常结果可能unknown，不能声称外部调用exactly-once或自动无风险重试。worker是独立进程：`python -m app.services.tool_execution.worker`（cwd backend），FastAPI main.py并未启动该worker。仅接入API而没有worker会使任务停在queued。

## 迁移：必然出现的双head

W02迁移 `f1b4c9d76e20` 的down_revision为 `5c81a1e74f2b`，新增tool_jobs、tool_steps、tool_attempts、tool_events、tool_command_receipts等持久化记录及proposal关联字段。目标V01已有merge revision `8ab42c17d3e9`，parents为 `c3b7e1d9a62f`（chat语音metadata）和 `5c81a1e74f2b`。

把W02迁移原样加入后，head将为8ab42c17d3e9和f1b4c9d76e20。应新增无DDL merge revision合并这两个head，保留旧revision与依赖关系，不修改已存在迁移的down_revision来伪造线性历史。新merge revision命名应由实施时生成并验证，本文不预设ID。

验证必须使用临时数据库：空库upgrade head、V01旧head升级、W02旧head升级；确认chat metadata和W02表/列同时存在；分别验证downgrade返回原head不会意外移除另一支功能。检查SQLite外键cascade与PostgreSQL schema，不能只用create_all代替Alembic验证。

## 不应从W02回拷的文件

以下文件虽然两边不同，但没有W02工具执行的必要增量，应默认保留目标版：

- `backend/main.py`、`core/config.py`：W02缺目标版生产安全校验、capacity、音频时长探测、图片像素上限等。
- `backend/app/api/{chat,vision,voice}.py`、`schemas/chat.py`、`models/chat_log.py`、`repositories/chat_log.py`、`services/qa/{pipeline,stream_events}.py`与TTS文件：W02缺最新重播、媒体校验、容量/幂等保护及相应测试。
- `backend/app/services/itinerary/progress.py`：W02删estimated_current_stop及保守估算说明，属于旧行为，不是工具执行依赖。
- `frontend/src/{stores/chat.js,composables/useAudioPlayer.js,composables/useSSEStream.js}`与`api/{chat,voice,vision,narration,knowledgePublications}.js`：保留最新主线；W02只需通过tourSessions层触发任务，无需回退这些文件。特别保留刚修复的publication传入key复用。
- MapView、SpotNarrationCard及guide CSS：仅在恢复卡新增样式确有需要时摘取小段；保留最新播放器签名、速率单位、地图布局。W02使用旧百分比语速，目标已使用倍率，误拷会造成100倍速或双重调速。

## 风险与检查重点

1. 原子创建：proposal预留、job、operation幂等记录、execution_job_id应同事务成功或回滚；请求重放不得新建job。W02处理IntegrityError后的rollback/replay需要保留。
2. 陈旧结果：V01已有catalog staleness与草稿校验；W02新增revision/progress/fence校验需叠加，不能互相替代。模型完成时目标游览可能被修改、删除、恢复，结果不得覆盖新内容。
3. 跨会话：恢复轮询需绑定捕获的sessionId及request generation；切换游览、取消等待、刷新后旧返回不得回写新游览。停止浏览器等待与服务器cancel job是两种状态，UI需明确。
4. uncertain外部结果：waiting_user重试必须由用户明确确认，不能仅因为刷新/轮询错误便传confirm_duplicate_risk=true。
5. 清理：删除/清空/过期purge路径需一致清理任务与事件；owner/site隔离同时覆盖list/get/events/retry/cancel，CSRF用于写操作。
6. 并发：repository有PostgreSQL skip_locked与fence更新逻辑，但静态存在不证明多worker正确，SQLite通过也不能代替PostgreSQL故障注入。

## 实施与验证顺序

1. 固定当前V01基线与现有测试结果，在集成副本新增12文件，先合模型导入、迁移与router。
2. 分别合repository原子事务/失效钩子，再把proposals API切到异步202，不改budget和chat/voice/vision链路。
3. 只摘取API/store/UI的恢复、查询、显式重试；沿用目标的latestRequest和proposalSnapshot工具；为新增能力补测试。
4. 独立worker在fake handler下验证排队→claim→完成→刷新恢复；真实模型调用需单独验收和授权。

后端优先测试：新增`test_tool_execution_acceptance.py`（当前只有2个测试函数）、现有`test_tour_session_api.py`、`test_tour_session_repository.py`、`test_tour_progress_and_proposals.py`、`test_tour_proposal_catalog_staleness.py`、`test_itinerary_progress.py`、`test_tour_budget_api.py`、`test_itinerary_provenance.py`、`test_chat_replay_api.py`、`test_production_security_config.py`。现有W02“36条目标测试”不等于36条独立工具执行测试，应报告实际收集结果。

补充W02测试应覆盖并发重放、payload变更409、外部调用unknown禁止自动重试、lease到期/fence拒绝旧worker提交、任务取消、目标版本变化、跨site/owner访问与purge；不能仅复制旧V01测试替换目标新断言。

前端运行完整`npm test`及构建，重点`proposal-snapshot`、`proposal-apply-state`、`request-generation`、`tour-budget-api`、`progress-refresh`、`chat-stream`、`chat-replay`、`audio-player`、`audio-playback-session`、`publication-api-integration`。为resumeProposal增加切游览/乱序/刷新恢复/等待取消用例。原生浏览器验收proposal queued/worker中断/waiting_user/显式风险确认/ready/apply与刷新闭环。

本次为静态规划，没有启动worker、执行迁移或重跑测试，也没有修改任一源码文件。
