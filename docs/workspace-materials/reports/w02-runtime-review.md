# W02实际运行链独立安全审阅

审阅基线：`integration-work/v01`，HEAD `ec3f7a6`；日期2026-10-30。只新增`backend/app/tests/test_w02_runtime_review.py`及本报告，未修实现、未读真实凭据、未访问生产数据库、未调用真实模型。

所有新增测试均为 **fake provider**：4种数据库场景使用pytest临时SQLite文件；worker CLI子进程使用最小环境、显式DATABASE_URL/PYTHONPATH及干净cwd，避免加载项目.env。独立CLI的review.fake工具故意未在生产registry注册，期望受控失败，绝不能把它说成真实AI供应商调用成功。真实itinerary handler路径另由现有catalog staleness测试以fake模型执行。

## 可复现缺陷

### W02-R1 / P2：执行尝试已开始但外部调用尚未发出时崩溃，恢复后任务永久失败

复现：创建retry_safe=False、max_attempts=1任务→claim→start_attempt→不调用mark_external_call→让租约过期→maintain→由新ToolRunner执行。实际终态`failed / attempt_limit`，fake provider调用计数为0；预期这次明确尚未调用外部服务的中断可以恢复，或至少进入有可用重试路径的状态。

根因：`backend/app/repositories/tool_execution.py:396-432`维护将not_started步骤重新设为queued，但保留已增长的attempt_count；`:552-555`新start_attempt因max_attempts=1拒绝，`services/tool_execution/runner.py:62-66`转为attempt_limit。manual_retry只允许有限错误reason，attempt_limit不在其范围（repository约950行），因此用户也不能沿原job恢复，只能新建提案。

安全性边界：未观察到重复外部调用；这是可用性/恢复承诺缺陷。修复应区分“外部未发出而中断”和已实际尝试，继续维持外部结果unknown不得自动重试的约束，不能简单无限增加max_attempts。

证据：新测试`test_restart_after_attempt_before_external_call_is_recoverable`。基线曾以strict xfail保留已知失败，`--runxfail`显示真实失败断言`('failed', 'attempt_limit', [])`。

### W02-R2 / P2：SQLite worker --once已处理任务，但进程无法退出

独立子进程执行`python -m app.services.tool_execution.worker --once --worker-id isolated-review-cli`，显式连接临时SQLite库。数据库任务已变为`failed/handler_version_unsupported`，证明领取和执行周期已完成，但15秒首次观察及后续5秒有界复现均未退出。

对照仅在同样serve(once=True)的async finally中加入`await engine.dispose()`，进程正常退出。`backend/app/services/tool_execution/worker.py:56-62`当前只asyncio.run(serve(...))，没有dispose，全局engine使用aiosqlite连接线程。这会使一次性运维/冒烟命令挂起，SQLite评审部署进程退出也需检查。

新测试`test_worker_cli_once_reads_explicit_isolated_database[False]`在基线为strict xfail；True参数是显式dispose对照并通过。测试5秒到期后kill其创建的子进程并await communicate回收。首次探测版本尚无cleanup；随后通过升级权限精确pgrep核验唯一worker-id及命令结尾，两次均无匹配进程，因此无需kill；没有使用广泛pkill或触碰其他worker。

## 已验证的保护

- 真实`worker.serve(once=True)`使用fake注册执行器，完成queued→running→succeeded，结果只对匹配owner/site可见。
- claim后、start_attempt前租约过期：maintain恢复queued，旧lease提交被拒绝，新worker可完成，fake调用恰为1次。
- 外部调用开始后用户cancel：job为cancelled，reason明确external_outcome_unknown；旧lease完成返回False，新worker不再领取。
- 既有W02验收验证错误fence无法覆盖新worker、target revision变化导致stale、unknown不得自动领取及显式重复风险确认后才能retry。
- 既有proposal API测试验证202受理、同key重放同proposal/job、不同payload冲突，enqueue已flush后失败可整体回滚。
- 既有catalog staleness测试真实经过API→生产registry/handler/runner（fake模型）→GET ready→景点撤回→apply 409，保留tour版本/进度/事件不变断言。

## 启动配置与部署边界

worker为独立进程，不由FastAPI lifespan自动启动。应从backend目录启动，或显式PYTHONPATH指定backend；API和worker必须使用同一个DATABASE_URL及site/模型配置。settings从cwd下.env加载，因此更换工作目录而没有显式环境配置会改变生效配置。

当前README、DEVELOPMENT和ARCHITECTURE没有可直接使用的W02 worker启动/监督/健康检查说明（研究和设计文档有独立worker要求）。生产/评审部署需要明确同时运行API+worker，而不是仅启动uvicorn；API就绪状态也不能证明worker在线。此为静态部署证据缺口，没有冒用真实配置验证供应商。

取消保证的是本地状态与后续结果被fence拒绝，不等于供应商端请求撤回/退款。当前heartbeat默认10秒发现失去lease后取消本地执行，不能宣传立即停止外部计费。SQLite单worker测试不能证明PostgreSQL skip_locked多worker竞争、死锁或实际进程崩溃后供应商状态；本轮未访问PostgreSQL生产或本地已有库。

## 运行命令及结果

cwd：`integration-work/v01/backend`；解释器：`/Users/yumir/RuanJianBei/backend/.venv/bin/python`。

```sh
python -m pytest app/tests/test_w02_runtime_review.py -q --tb=short
python -m pytest app/tests/test_w02_runtime_review.py -q --runxfail --tb=short
python -m pytest app/tests/test_tool_execution_acceptance.py app/tests/test_tour_proposal_catalog_staleness.py -q
```

基线新增独立测试：4 passed、2 xfailed（两项已知缺陷，非跳过运行）；随后`--runxfail`实测2 failed、4 passed，完整重现两项缺陷。既有验收及catalog链路6 passed。缺陷修复由其他代理负责，后续结果见下方记录。

审阅没有发现并证明新的跨owner/site越权或旧fence覆盖成功；这不等于完整安全证明。未验证真实供应商、手机浏览器或PostgreSQL多worker。

## 修复后复核记录

- W02-R1由另一代理修复repository后，本审阅移除该测试xfail并重跑runtime+acceptance：10 passed、1 xfailed（剩余R2）；其中外部unknown禁止自动重试及显式确认测试通过。R1基线缺陷仍保留上述记录以便追溯，当前已回归通过。
- W02-R2由另一代理在CLI资源所有权边界增加finally dispose并补充空队列/初始化异常退出测试后，本审阅撤销剩余xfail。最终runtime review + 原验收 + catalog链路 + worker lifecycle四测试文件 **14 passed in 1.97s**，无xfail/skip。独立审阅自身仅改新测试及本报告，两个实现修复由对应代理完成。
