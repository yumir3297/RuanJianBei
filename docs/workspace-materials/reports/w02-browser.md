# W02本地浏览器验收记录：浏览器环境未开放

2026-10-30；当前集成副本HEAD `4054485`。本轮未修改业务文件、未启动面向真实凭据的服务、未访问生产数据库。

**结论：尚不能声明真实浏览器完整链路验收通过。** 已完成浏览器能力检查和当前源码的隔离API/worker复核；真实页面操作被Work本地浏览器开关阻断，不是已证实的应用缺陷。

## 浏览器环境检查

发现可调用的浏览器宿主执行工具及本机Browser技能，按技能初始化浏览器并选择本地测试URL：

```js
const { setupBrowserRuntime } = await import("/Users/yumir/.codex/plugins/cache/openai-bundled/browser/26.1023.51421/scripts/browser-client.mjs");
const agent = await setupBrowserRuntime();
const browser = await agent.browsers.getForUrl("http://127.0.0.1:18765/");
nodeRepl.write(await browser.documentation());
```

工具明确返回：`Local browser use is disabled in Work settings`。随后按技能读取bootstrap-troubleshooting文档，同样返回该禁用错误。没有获得tab、DOM或截图；没有实际访问上述URL；没有擅自切换为外部Playwright、系统Chrome或其他浏览器以绕过此设置。

继续条件：用户在Work设置中启用本地浏览器访问，再重试浏览器连接。该开关属于宿主用户配置，当前工具没有权限自行启用。

## 本轮确实运行的隔离验收

cwd `integration-work/v01/backend`：

```sh
/Users/yumir/RuanJianBei/backend/.venv/bin/python -m pytest \
  app/tests/test_w02_runtime_review.py \
  app/tests/test_tool_execution_acceptance.py \
  app/tests/test_tour_proposal_catalog_staleness.py \
  app/tests/test_tool_worker_lifecycle.py -q --tb=short
```

结果：**14 passed in 1.98s**，无xfail/skip。

这些测试明确使用fake provider及临时SQLite库，不读取真实.env；CLI子进程使用干净cwd、显式临时DATABASE_URL及最小环境。覆盖：

- API创建proposal/job返回202，同key重放不新建任务、不同内容409、事务失败整体回滚。
- 独立worker真实子进程连接临时库、处理队列并退出；另有fake registry下worker.serve成功执行。故意未注册的fake工具受控失败不能计为真实AI调用成功。
- API→生产itinerary handler/ToolRunner→fake模型→查询ready→景点撤回→apply 409，版本/进度/事件不被修改。
- 租约过期恢复、外部调用前中断恢复、旧fence拒绝、owner/site隔离；外部结果unknown禁止自动重试、显式确认后允许重试。
- 外部调用后cancel标记unknown费用风险，旧任务完成被拒绝；CLI无任务和初始化异常均释放SQLite连接并退出。

这些结果不覆盖浏览器点击、刷新后Pinia状态恢复、卡片可见性或交互时序，不应写成“浏览器端到端通过”。历史运行审阅原始缺陷及修复证据见`reports/w02-runtime-review.md`。

## 已准备的真实页面验收顺序（待浏览器开放）

1. 使用新建临时目录及SQLite库；API和独立worker显式指向同库。启动脚本在临时目录运行，供应商设置仅使用标明FAKE的本地服务或测试替身，禁止加载工程真实.env；前端以临时Vite配置反代隔离API，避免连接默认8000现存服务。
2. 浏览器打开隔离前端，点“路线”→“新建空白游览”，添加休息点、保存。记录session ID、version和页面截图，确认身份cookie正常且仅访问测试库。
3. worker暂停时在对话请求明确行程修改，确认POST proposals为202、页面显示“后台生成/停止等待不会取消后台任务”，数据库job为queued；此时刷新，页面恢复同一个proposal/job而不重复提交。
4. 启动独立worker，fake provider返回可验证constraints修改；观察queued→running→ready，页面显示diff且保存前tour version不变；刷新仍可恢复ready提案。
5. 点“确认并保存新版本”，确认恰增加一个revision、约束变化符合diff；重复点击或回放相同key不增加第二个版本。
6. 再创建任务，点“停止等待”并确认任务仍在后台执行；刷新/“检查后台提案”能恢复。该按钮按当前文案是停止客户端等待，不应当成服务器取消。服务端cancel另用真实UI入口（若存在）或隔离API验证，区分两者。
7. 让fake provider模拟“可能收到调用但响应丢失”，观察waiting_user及“可能重复产生调用费用”提示；刷新不能自动重试，只有点击明确确认按钮才发confirm_duplicate_risk=true。
8. 在生成中修改游览或进度，确认旧结果stale而不能直接保存；切换游览后旧轮询不污染当前页面。检查控制台错误与网络状态，保存截图及脱敏事件序列。
9. 退出测试前按记录的PID停止自己创建的API、worker、前端进程，释放数据库连接；不使用宽泛pkill，不操作其他已运行服务。

静态入口已确认：ChatView有waiting_user费用提示、显式确认重试、ready保存、后台执行提示与停止等待；RouteView有“新建空白游览”“检查后台提案”；tourSessions store有restoreProposal/resumeProposal/retryProposal及保存current tour ID的逻辑。这只是后续操作定位，不代替浏览器验证。

本轮没有新增可复现的浏览器业务缺陷，因为浏览器尚未能连接。唯一阻断为宿主禁用本地浏览器，完整浏览器验收仍待执行。
