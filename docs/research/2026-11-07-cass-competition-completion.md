# CASS 比赛版完善：技术调研与开发范围建议

日期：2026-11-07。状态：完成官方资料和当前源码核对，形成开发建议；本文不代表新增功能已实现，也不替代后续实施结果。

## 1. 目标与结论

按用户明确的比赛定位，优先交付可展示的场景创新和稳定的基础流程。采用 Vue/Pinia + FastAPI/Pydantic + 既有 RAG/TTS + W02 持久提案，补齐“情境变化—解释决策—生成建议—人工确认—更新游览”的信息流。无需训练模型、证明新算法或先部署完整现场安全平台。

建议文书定位：**基于事件驱动与双通道协同架构，面向景区现场变化设计融合情境证据、受控生成和人工确认的自适应导览信息流。** 普通服务通道负责讲解和行程建议，规则通道负责预警优先级和中断；通过版本校验保护游客已经确认的行程。创新落在技术如何围绕场景协作，以及可见的服务变化。

“双通道”“情境增强 RAG”“人在回路”“持久化工作流”都必须对应代码行为。LangGraph/XState 仅作为模式调研依据，当前代码没有依赖它们，不可写成已接入；没有持续数据反馈的仿真场景不可称数字孪生，没有多个自治 Agent 不可称多智能体协同。

## 2. 当前源码事实

| 位置 | 已有能力 | 本轮发现的缺口 |
|---|---|---|
| `backend/app/services/guide_context/policy.py` | 预算短讲解、播放忙时延后、有效严重气象预警优先 | 兴趣没有参与规则；天气/客流到普通服务建议尚未打通 |
| `backend/app/api/guide_context.py` | 发布目录修订检查、服务端天气、情境摘要 | 游览 ID/版本只是回显上下文，未通过所有者身份加载权威游览；不能作为改线授权依据 |
| `frontend/src/guide/context.js` | 坐标质量/来源区分、兴趣与讲解长度拼接 | 讲解时长是提示目标，不是精确音频时长保证；当前主要经文本请求传入 |
| `frontend/src/guide/scheduler.js` | reducer、generation 迟到隔离、取消与预警中断 | 确认后将事件 ID 永久记入 dismissed 列表；仍有效同 ID 可能无法再次进入中断状态；多个事件按到达次序处理，未统一按优先级选取 |
| `frontend/src/composables/useGuideContext.js` | 调度和请求封装 | controller 返回被忽略的旧响应后 composable 仍可能赋给 result；需同时防止旧 UI 结果和旧讲解动作 |
| `GuideContextStatus.vue` | 开关、预算、兴趣、演示预警、本地求助说明 | 卡片以状态文本为主；缺少可操作建议、原因说明、事件时间线和绑定决策时的输入快照 |
| `ChatView.vue` / `tourSessions.js` | 中断现有输出、`requestProposal(text)`、提案预览/确认/过期检查 | 尚无 CASS 建议到现有提案的入口 |
| `tool_execution/handlers.py` | 只注册 `itinerary.proposal`，独立 worker 持久执行 | 模型或 worker 不可用时不能把建议显示为已生成提案 |

以上为静态源码核对，疑似缺陷需在开发时先用针对性测试确认。当前 CASS 改动尚未提交，应保留现有工作树，不通过复制旧分支覆盖。

## 3. 技术调研与选型

### 3.1 事件驱动与状态机

[CloudEvents 规范](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)定义了事件标识、来源、类型等字段及 source/id 唯一性。借鉴其字段设计，CASS 内部事件补充 `event_id/source/type/occurred_at/expires_at/schema_version/data_mode`，另设业务 `priority`；不宣称整个 HTTP/SSE 协议符合 CloudEvents。

[XState actor 模式](https://stately.ai/docs/actors)适合显式建模事件和生命周期。当前 reducer 已具备相关基础，建议先继续使用 reducer，统一优先级仲裁、确认与解除的区别、取消效果和请求代次；暂不引入第二套状态系统。未来状态层级显著增加时，再考虑单模块迁移到经过兼容性核对的稳定 XState 版本。

### 3.2 人工确认与持久化工作流

[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)和[interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)展示了通过状态保存、中断和外部确认继续执行的模式。仓库 W01/V01/W02 已实现相近业务基础；直接复用当前任务、提案与版本协议，避免为 CASS 增设独立 checkpoint 数据库和重复 worker。

职责划分：规则生成“为何建议调整”的结构化建议；模型通过已有 itinerary proposal 生成受限修改；现有校验器核对目录、版本、预算和锁定约束；游客查看差异后确认。CASS 不直接执行模型文本，也不从无主游览 ID 写行程。

### 3.3 情境增强 RAG

复用仓库已发布目录和 QA/RAG/TTS。情境用于选择篇幅、主题重点和服务动作；事实仍来自当前已发布知识。下一步传入稳定 `spot_code + published_revision_id` 并经现有解析器校验，减少仅靠景点名称字符串定位。新增情境字段时同时检查缓存资格/键与流式来源绑定，防止短讲解与常规回答错误复用。

首版用固定策略表，模型只处理讲解和提案语言：时间紧→短讲解；亲子兴趣→通俗主题；降雨→提供有已知室内属性景点的调整建议；拥挤演示→建议调整尚未游览的景点顺序。不得由名称推断室内外，不把演示拥挤度变成官方客流。

### 3.4 空间区域与天气证据

[Turf booleanPointInPolygon](https://turfjs.org/docs/api/booleanPointInPolygon)可对 GeoJSON Polygon/MultiPolygon 做点包含判断。仅在开发区域演示时评估按函数引入；所有几何数据统一坐标系，再增加精度、采样时间、边界滞回/连续样本判断。点在多边形内本身不等于可靠到场或危险判断。

[QWeather Alert 官方说明](https://dev.qweather.com/en/docs/api/warning/)支持生效/失效、严重性和预警更新等信息。仓库当前使用 `/weatheralert/v1/current/{lat}/{lon}`；开发时核对当前接口字段、解除/更新与部分上游失败。live provider 使用服务端数据；demo provider 使用固定场景时钟和事件，不混成同一真实证据。

### 3.5 离线技术

[Workbox precaching](https://developer.chrome.com/docs/workbox/modules/workbox-precaching)可支持带修订的静态预缓存。完整 PWA 会影响站点更新和缓存行为，建议后续独立交付。先提供 CASS 面板内的网络失败状态、保留当前可读文字和手动重试；全新断网打开站点、离线地图和实时预警不属于这一能力。

## 4. 技术组合与可展示证据

| 可用的技术表述 | 实际落点 | 评委能看到什么 |
|---|---|---|
| 多源情境融合 | 预算、兴趣、发布目录、天气/显式演示客流的统一快照 | 同一景点切换预算/兴趣后，策略与讲解重点变化 |
| 双通道事件驱动协同 | 服务建议与安全规则分离，统一调度仲裁 | 讲解过程中预警出现，原输出停止，提醒前置 |
| 证据约束的情境增强 RAG | 景点稳定身份、发布修订、来源引用 | 讲解改变表达，仍能查看知识来源 |
| 人在回路的持续伴游 | CASS 建议接入 V01/W02，差异确认后应用 | 拥挤演示触发改线建议，游客确认后更新原行程 |
| 可解释服务编排 | 规则 ID、原因、输入摘要、动作和结果 | 轻量时间线显示“感知—决策—确认—结果” |

以上均为交付目标；最后两项及完整第一/第三项需补齐后才写成已实现。文书可强调组合应用创新，不承诺未经测量的准确率、响应时延或现场安全保障。

## 5. 建议开发范围与顺序

### CASS-01：先稳定当前演示链路

修改 `scheduler.js`、`useGuideContext.js`、`GuideContextStatus.vue` 和对应测试：

- 确认只是已读；有效预警持续阻止普通服务，解除必须经重新核验或明确演示事件。
- 多事件按优先级选取，低级事件不能覆盖高级事件；同事件更新和解除有明确语义。
- 响应只在当前 generation/输入快照有效时更新 UI；停止、关闭、切换和重新选择景点使旧建议失效。
- 防止已有中断状态时点击讲解按钮；把“服务就绪”和“正在播放”分开。

这是高收益的最小可靠性工作，不扩展认证、部署平台或框架。

### CASS-02：情境决策卡与场景 provider

修改 `guide_context` schema/policy/API，新增独立 provider 和 suggestion 模块；前端新增建议卡/时间线组件，保持 `GuideContextStatus` 只做装配。

建议响应契约：`decision_id/context_digest/generated_at/expires_at/rule_ids/reasons/evidence_refs/suggestions/data_mode`。建议具有 `suggestion_id/action/target_spot_codes/catalog_digest/blocked_reason`；这是待实施契约，字段不可当作已有 API。

live、manual、demo 的来源必须明确。只有服务端 demo 开关允许 scenario ID；演示场景服务端固定，不允许浏览器随意提交“真实预警”。首批场景只做常规、时间不足、模拟降雨、模拟拥挤、预警中断、网络失败六组。缺少室内元数据时显示一般建议，不推荐具体“避雨景点”。

时间线仅显示简短业务事件，不显示模型思维链或完整定位日志；默认有界内存保存，重置演示可清空，不宣称刷新后持久恢复。

### CASS-03：建议到行程提案

修改 `ChatView.vue`、`tourSessions.js`，新增独立建议适配器；必要时扩展 `tour_sessions.py` 现有 proposal 输入，保留所有者/CSRF/版本校验。

点击“生成调整方案”后复用现有 `requestProposal(text)`，打开现有差异卡，确认仍走 `applyProposal`。服务端需重新核验建议白名单与当前目录、游览/进度版本；客户端 suggestion ID/context digest 不能替代授权。模拟事件影响真实游览前，提示当前建议基于演示情境并由游客明确发起。

未打开 V2 游览时引导打开路线工具；worker 未启动或模型失败时保留建议和原行程，显示未生成。开始后“剩余时间”是 `finish_by` 的预算语义；本轮 CASS 选择器只控制讲解，不能顺带更新行程预算。若要调整实际截止时间，使用已有独立预算确认入口，不把自然语言与预算联合确认冒充已完成。

### CASS-04：形成完整比赛演示

完成一段 2–3 分钟流程：普通讲解→时间缩短→模拟客流变化→调整提案与确认→预警抢占→确认仍需核验→恢复。提供一键重置；逐步解释来源、原因和结果，正常游客界面不堆开发参数。

规则与卡片支持确定性回放，生成环节继续用实际模型和现有知识。现场模型不可用时可以重播明确标注的演示记录；不可把预存答案/预存提案伪装成本次实时生成。多轮回放证明演示流程稳定，不等于真实游客效果评测。

### 后续独立扩展

真实 GeoJSON/官方联系方式、后台接警、实时客流、完整离线包分别依赖资料、接收流程或缓存方案。先预留 provider/资源接口；有资料后按项接入。比赛首轮可用明确标注的区域/客流演示表现算法与信息流，不能把这些列为已接入真实数据。

## 6. 精简而必要的验证

新增针对性回归覆盖：有效预警确认后仍阻止生成；高低预警同时到达；旧请求晚回；手动改草稿后旧建议失效；目录更新拒绝旧提案；模型/worker 失败不改行程。复用已有用例，不建设论文评测集或覆盖率指标工程。

完成代码后运行 `frontend/` 的 `npm test`、`npm run build`；在 `backend/` 跑 CASS 与本轮涉及的 itinerary/tour proposal 测试；根目录跑地图校验、脚本测试与 `git diff --check`。若改 QA 协议/缓存，扩大到对应 QA/流式回归。

浏览器最少人工走一遍文字问答、语音播放与停止、地图开合、V01 提案确认和 CASS 六场景，确认基础演示未回退。设备/供应商没有实际测试就记录为未测，不写成已通过。该范围服务于明显故障排查，不要求先完成全套真实现场验收。

## 7. 开工材料与判断

现有设计：`docs/讨论优化/CASS-Guide-Development-Plan.md`。
当前边界：`docs/implementation/CASS_GUIDE.md`、`docs/implementation/CASS_ACCEPTANCE.md`。
接口约束：`docs/architecture/CONTRACTS.md`，尤其剩余时间、提案持久化和发布修订。

建议下一轮优先交付 CASS-01～04，形成比赛可展示闭环，再更新实现说明和验收结果。本文仅做研究与范围建议；未安装框架、未调用付费模型、未修改业务代码或现场数据。
