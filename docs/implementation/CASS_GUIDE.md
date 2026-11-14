# CASS-Guide：情境感知与安全协同导览

本实现按比赛展示场景落地“基于情境感知与双通道事件驱动架构的自适应导览信息流”：将游客选择的剩余时间与服务端天气/气象预警输入统一决策，再由确定性安全规则控制优先级；同一结果显示在游客舞台的情境面板上。原始方案与创新表述见[讨论分支设计稿](https://github.com/yumir3297/RuanJianBei/blob/feat/location-guide-opt/docs/%E8%AE%A8%E8%AE%BA%E4%BC%98%E5%8C%96/CASS-Guide-Development-Plan.md)。

## 当前实现

- 前端 `frontend/src/guide/context.js` 构造带来源、时间、精度和模拟/真实区分的情境快照。新鲜且精度不高于 80 米的真实设备定位可与带依据的 GCJ-02 已发布景点坐标匹配，在 250 米内给出附近讲解候选；游客需主动选择，坐标只在本地参与匹配，不把原始 GPS 发给 CASS 决策 API，也不作为到场或安全证明。模拟定位不会产生附近实景候选。
- 前端 `frontend/src/guide/scheduler.js` 提供单一导览状态 reducer/controller：有效安全事件取消等待中的普通服务并提升到前台；迟到决策被 generation 忽略；地图隐藏会取消请求并暂停情境服务。提示需要游客确认；确认后先重新核验，仍有效的预警不会恢复讲解。
- 前端 `GuideContextStatus.vue` 为游客提供主动开启、时间/兴趣/已发布景点选择、游览版本和播放状态输入、当前情境评估及本地求助入口；“按此情境生成讲解”通过现有问答/RAG/TTS 播放链生成结果。演示流程包含“时间策略→模拟客流变化与避拥挤提案”及“模拟预警抢占→手动确认→手动恢复→明确生成讲解”；数据性质明确标注，不发送真实求助。
- 后端 `POST /api/guide/decision` 不调用模型、不写行程；按服务端天气源和明确有效期评估预警，普通降雨不会触发安全事件。新鲜的和风天气雨雪图标会作为非安全性 `weather_adaptation` 输入讲解提示词，要求讲解利落、避免建议长时间驻足，并禁止模型推断景点室内属性、开放状态或安全状态。天气采用景区默认位置实况，不声称是游客脚边天气。30 分钟及以下选择简短讲解，正在播放时延后；响应带规则 ID、理由、证据引用、数据性质、有效期和需确认的建议动作。`GET /api/guide/bootstrap` 返回开关、已发布目录和资料状态。
- CASS 面板提供离线可重现的“雨天讲解适配”演示，明确显示模拟天气、不作为安全证据；兴趣仍由游客选择并写入景点问答请求。情境面板的确定性测试覆盖演示点击、信息呈现与 V01 提案事件入口。
- K01 已发布目录响应新增可空坐标系、环境类别及来源引用。未知环境保持 `unknown`，不从景点名称推断室内外；未经坐标系和证据核验的目录项不参与附近景点候选。
- CASS 默认关闭，通过服务端配置 `CASS_ENABLED=true` 开启；仅演示需要额外设置 `CASS_DEMO_ENABLED=true`。配置关闭时旧讲解和问答路由保持原行为。

## 创新点与实现对应

本项目的创新定位是成熟技术在景区连续游览场景中的协同应用，不宣称自研基础模型、RAG 框架或安全算法。答辩时可按下面的对应关系讲“为什么这项技术在本场景里产生了可见变化”。

| 场景应用创新点 | 在本项目中的具体实现 | 可展示行为 | 验证依据 |
|---|---|---|---|
| **面向游览任务的多源情境融合**：把游客需求、景区环境与行程状态组织为同一决策输入，并保留证据时效与数据性质 | [前端情境快照](../../frontend/src/guide/context.js) 汇集剩余时间、兴趣、所选景点和定位状态；[CASS API](../../backend/app/api/guide_context.py) 读取已发布目录并调用现有天气服务；[确定性策略](../../backend/app/services/guide_context/policy.py) 校验服务端天气来源、请求时间和 `obsTime`。附近景点候选只使用新鲜真实定位和带依据的已发布坐标 | 游客选择时间/兴趣后展示决策理由与规则；合格真实定位可建议附近已核验景点；雨雪实况或模拟天气在面板标明来源和性质 | [情境规则和 API 测试](../../backend/app/tests/test_guide_context_policy.py)、[前端情境测试](../../frontend/tests/guide-context.test.mjs)、[面板交互测试](../../frontend/tests/guide-context-component.test.mjs) |
| **生成式服务与确定性安全规则双通道协同**：生成模型组织讲解和提案，规则通道控制来源边界、时效和安全事件优先级 | [规则策略](../../backend/app/services/guide_context/policy.py) 只接受有效严重气象预警；[事件调度器](../../frontend/src/guide/scheduler.js) 负责取消普通输出、预警抢占、去重和手动恢复；普通雨雪只影响讲解提示，不升级为安全事件 | 点击模拟预警，看到普通讲解被安全提醒抢占；游客确认后系统仍等待重新核验或手动恢复，不由模型自行判断“安全” | [调度器测试](../../frontend/tests/guide-scheduler.test.mjs)、[后端安全策略测试](../../backend/app/tests/test_guide_context_policy.py)、Vue 面板交互测试 |
| **跨交互载体的连续导览与人工确认闭环**：同一情境决策连接既有问答、数字人/语音播放和版本化行程提案，而不是另建孤立 AI 流程 | [情境面板](../../frontend/src/components/guide/GuideContextStatus.vue) 通过 `ChatView` 的既有处理器发起景点讲解与提案；提案复用 V01 `tourStore.requestProposal`、差异预览、版本检查和确认保存 | 演示“情境讲解→天气/客流建议→路线差异→游客确认”；确认前路线不变，确认后才保存新版本 | [ChatView 接入](../../frontend/src/views/tourist/ChatView.vue)、[提案与会话回归](../../backend/app/tests/test_tour_progress_and_proposals.py)、[比赛演示脚本](CASS_DEMO_SCRIPT.md) |

以上表述对应当前已实现和可演示范围。实时客流、危险区围栏、后台接警与现场救援不属于当前实现，不应纳入已完成创新效果的表述。

## 接口与边界

`GET /api/guide/bootstrap` 返回 `available/enabled/demo_enabled/site_id/catalog/catalog_digest/verified_local_resources`。`POST /api/guide/decision` 接收白名单偏好、已发布景点修订和目录摘要、可选位置提示、游览版本、播放状态和演示场景标识；景点修订变更会要求刷新目录，关键天气证据由服务端重新获取。浏览器位置仅是客户端提示，不能证明真实到场。首版无危险区数据与已核验本地资源时，不产生危险区事件，求助入口也不会声称已通知或已受理。

时间不足时可以显式请求当前 V01 游览的路线调整提案；提案沿用已有差异预览和版本保护，并须游客确认才应用。降雨目前只适配讲解节奏，不自动改线；模拟客流只展示可重复的提案建议，不冒充实时数据。真实危险区围栏、核验后的应急联系方式和完整离线体验仍需结合可信数据与后续验收扩展。当前短/常规讲解决策通过显式按钮带入已发布景点问答；系统不会静默改写游客行程。模拟预警仅供可重复演示。

技术选型、源码映射与验证边界见 [CASS 比赛版完善调研](../research/2026-11-07-cass-competition-completion.md)、[比赛演示脚本](CASS_DEMO_SCRIPT.md) 和 [CASS 验收记录](CASS_ACCEPTANCE.md)。

天气适配按和风天气官方 `iconCode` 区间识别降雨（300–399）与降雪（400–499），同时核验 `fetched_at` 和天气 `obsTime` 均在 15 分钟内；未知图标、缺少观测时间或过期数据不触发适配。天气代码可由供应商更新，遇到未映射代码时保持不适配。[和风天气天气现象编码](https://dev.qweather.com/docs/start/icons/)

## 测试

在 `frontend/` 执行 `npm test`。后端 CASS 规则/API/schema 测试可执行 `python -m pytest app/tests/test_guide_context_policy.py app/tests/test_guide_context_api.py -q`；完整 API/数据库/构建和真机检查见 [CASS 验收记录](CASS_ACCEPTANCE.md)。
