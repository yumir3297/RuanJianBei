# 多景区数字人导览平台改造方案（草案）

日期：2026-10-02。状态：方案讨论稿，尚未实施。

## 1. 产品目标与设计边界

面向缺少定制预算的景区，通过一套通用产品提供数字人语音导览。景区运营人员通过后台选择形象与音色、填写品牌信息、上传知识和素材、启用并配置功能，获得自己的游客入口。通用平台默认界面不带某个景区的地名、宗教、建筑或人物特征。具体景区的游客页面应当展示其已经配置的品牌与内容。

保留已经确定的交互关系：数字人居中、语音优先、功能位于两侧、文字记录按需展开。景区内容和扩展模块发生变化时，数字人舞台不被重新挂载或挤压。桌面与手机共享业务逻辑，由布局适配展示位置。

交付方式尚待用户明确：共享平台多景区，或每景区独立部署。本方案采用一致的 SiteContext 和景区配置协议支持两者。第一轮建立配置与模块边界；共享平台对外上线前必须完成后端权限、数据、缓存与检索的景区隔离。

## 2. 已核实的耦合位置

| 部分 | 当前证据 | 改造方向 |
| --- | --- | --- |
| 游客品牌和文案 | frontend/src/views/tourist/ChatView.vue、frontend/src/App.vue | 品牌名称、标题、页脚、问题入口、服务电话来自景区配置 |
| 景点、分类、路线、问题 | frontend/src/constants/touristCatalog.js；ExploreView.vue、RouteView.vue、QuizView.vue | 迁为结构化内容，统一由景区内容接口提供；本地示例包只用于显式演示 |
| 场景背景和欢迎文案 | frontend/src/composables/useScenicBackground.js；backend/app/services/display_assets.py | 游客读取已发布配置，缺省使用中性背景和欢迎文案 |
| 数字人身份 | useAvatar.js、avatar-presets/index.js、utils/avatarConfig.js；backend/app/services/llm/prompt_builder.py | 模型资产、导游姓名、人设和音色分别配置，解除模型键与姓名、宗教风格绑定 |
| 天气 | frontend/src/composables/useWeather.js | 使用景区坐标；服务供应商调用及凭据放在后端 |
| 游客配置读取 | frontend/src/api/admin.js；backend/app/api/admin.py | 形象和背景当前通过受保护的管理接口读取；新增公开、只读、仅含已发布字段的游客接口 |
| 问答业务规则 | qa/pipeline.py、qa/faq_semantic_gate.py、qa/followup_suggestions.py、rag/query_rewriter.py | 别名、实体、追问与特殊答案从当前景区内容生成 |
| ASR 与欢迎语音 | backend/app/core/config.py；services/tts/welcome_cache.py | 热词从当前景区名称、景点及别名生成；欢迎语音缓存纳入景区与文案版本 |
| 景区隔离基础 | models/knowledge.py、models/avatar_config.py；services/rag/base.py、rag/vector_store.py | 所检查模型与 RetrievalScope 没有景区归属；全量重建向量集合须改为景区限定 |
| 问答与客户端缓存 | models/qa_cache.py；frontend/src/stores/chat.js、interaction.js | 当前问答缓存按问题唯一、浏览器状态用全局键；需加入景区范围与内容版本 |
| 管理身份 | backend/app/api/auth.py | 当前管理令牌表达全局 admin；共享平台需用户与景区成员关系及角色权限 |

README 当前描述也以灵山作为产品主体，产品文档与演示资料应分开维护。

## 3. 参考的成熟模式

以下来源用于借鉴设计模式，不表示要把这些产品接入现有工程。

- Shopify：JSON templates 与 section/block schema 把页面组成、设置、顺序和可用模块变成配置。借鉴其运营人员选模块、改内容、排顺序的体验。
  https://shopify.dev/docs/storefronts/themes/architecture/templates/json-templates
  https://shopify.dev/docs/storefronts/themes/architecture/sections/section-schema
- Backstage：扩展具备稳定身份、挂载点、输入输出、配置约束，并支持扩展覆盖。借鉴模块注册、组件替换和明确接口。
  https://backstage.io/docs/frontend-system/architecture/extensions/
  https://backstage.io/docs/frontend-system/architecture/extension-overrides/
- Directus：结构化内容集合、字段与按条目限制的权限。借鉴景区内容编辑与运营权限管理。
  https://directus.com/docs/guides/data-model/collections
  https://directus.com/docs/guides/auth/access-control
- Azure Architecture Center：多租户存储隔离存在不同成本与复杂度，建议按需求选择，使用配置及功能开关适配客户。借鉴共享计算与隔离景区内容的设计。
  https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data

## 4. 方案选择

| 路径 | 能做到什么 | 适用判断 |
| --- | --- | --- |
| 仅抽取 JSON 配置 | 更换文案、颜色、图片、内容 | 可以作为迁移起点，无法单独满足行为及组件替换 |
| 配置协议 + 模块注册 + 现有后台内容管理 | 更换内容、控制启停、替换呈现和行为、统一发布 | 推荐作为本项目目标结构 |
| 远程微前端与第三方插件市场 | 多团队独立发布运行代码 | 当前维护、兼容与部署成本较高，待实际需要再扩展 |

推荐继续采用 Vue + FastAPI，建立模块化的单体应用。运营人员选择平台预置模块和配置；开发者增加兼容模块并发布到注册表。正常景区接入无需改业务代码或重新构建前端。

## 5. 配置、内容和能力边界

### 景区配置

SiteProfile 包括 siteId/slug、品牌名称/Logo、主题令牌、地理坐标、页眉与页脚文案、欢迎语、导游身份、形象资源引用、音色与语速、服务电话、功能配置、已发布版本。

模型外观和导游身份应独立：同一个现代形象可以服务森林公园或工业博物馆，姓名、人设和讲解语气分别配置。默认用中性字体、通用现代导游、无地标背景；古典、民族、宗教等风格作为可选景区主题或形象包。

### 内容资源

内容统一管理为 Attraction、Taxonomy、Route、Topic、KnowledgeDocument、FAQ、ServiceContact。采用稳定 ID 与可编辑标签，路线引用景点 ID；分类不固定为佛像、寺庙；前端筛选项由当前景区分类生成。景点别名与 ASR 热词由同一数据源生成。

知识事实、开放时间和票务来自景区发布内容；平台角色配置描述语气和身份，不能覆盖事实必须有依据的通用规则。发布状态、来源和有效期可用于筛选游客可见内容。

### 模块能力

模块描述至少包括：instanceId、type、apiVersion、title、icon、slot、enabled、order、config、configSchema、requiredCapabilities。配置中的 type 只映射到平台批准的组件注册表。

挂载位置是 leftRail、rightRail、stageOverlay、mobileSheet 等有限插槽。左侧列表模块可以替换为地图，文化故事可以替换为自然科普或工业历史；右侧支持服务、活动、天气或文字记录。默认维持中央数字人主舞台的可用面积。

每个模块通过统一 GuideContext 接收当前景区、公开内容服务、可用能力、会话忙碌状态和布局模式。通过 ask、selectAttraction、selectRoute、openPanel 等动作与主流程通信，不直接操纵音频队列或其他模块内部状态。ask 可传 query 与 attractionId/routeId/topicId，景区归属由后端校验。

内容替换、模块开关与顺序调整属于运营配置；组件及服务供应商替换由开发者实现适配器。新增功能逻辑仍需开发和发布，现有模块的配置调整不需要重新编译。

模块缺数据时提供诚实空状态，未知类型在管理端提示、游客端跳过；未知配置主版本拒绝发布。模块卸载必须释放计时器、订阅与请求。KeepAlive 状态按 siteId、instanceId、版本隔离，避免复用另一景区的筛选结果。禁用的模块不能被旧 URL 强行打开。

## 6. 建议组件结构

```text
frontend/src/
  guide/
    shell/          GuideShell、AvatarStage、VoiceControls、TranscriptPanel
    context/        useSiteContext、useGuideContext
    modules/        registry、ModuleHost、模块协议
    adapters/       avatar、voice、weather、content
  sites/
    schema/         公共配置类型与校验
    defaults/       中性默认值
    demo/           显式演示配置，不作为生产失败回退
  views/admin/
    SiteSettings、ModuleSettings、ContentManage、PublishPreview
```

ChatView 当前承担舞台、录音、音频、识景、文字记录和工具装配，先抽取显示组件与会话编排 composable，再由 GuideShell 装配。已有录音、ThreeAvatar、音频同步和问答存储可继续复用。

形象适配协议统一输入 speaking/listening/emotion/visemes/action，统一输出 ready/error 与能力声明。初期选择平台验证过的模型库。自定义 VRM/GLB 需要骨骼、表情、口型映射及构图参数校验，不能承诺任意模型上传即可正常驱动。

## 7. 示例公共配置（草案，不是现有 API）

```json
{
  "schemaVersion": 1,
  "siteId": "sample-park",
  "publishedVersion": 3,
  "brand": {"name": "示例景区", "logoAssetId": null},
  "theme": {"preset": "neutral", "primary": "#355D52"},
  "guide": {
    "name": "小游",
    "avatarAssetId": "generic-modern",
    "voiceId": "gentle-female",
    "welcomeText": "欢迎来到这里，我会陪你探索沿途的故事。"
  },
  "modules": [
    {"instanceId": "explore", "type": "attractions.list", "apiVersion": 1, "slot": "leftRail", "enabled": true, "order": 10, "config": {}},
    {"instanceId": "routes", "type": "routes.recommended", "apiVersion": 1, "slot": "leftRail", "enabled": true, "order": 20, "config": {}},
    {"instanceId": "stories", "type": "topics.cards", "apiVersion": 1, "title": "自然科普", "slot": "leftRail", "enabled": true, "order": 30, "config": {"collectionId": "nature-topics"}}
  ]
}
```

游客只读取白名单公开字段，不取得供应商凭据、后台路径或草稿。景区内容按需加载，启动 bootstrap 主要提供品牌、舞台、已发布模块与版本。

建议公开入口 /s/:slug；二维码直接进入对应景区。单景区部署可以让 /tourist 映射已配置的默认景区。找不到景区应显示明确错误，不能悄悄回到灵山。

建议公开 API：GET /api/sites/:slug/bootstrap、GET /api/sites/:slug/attractions、routes、topics。管理 API 由用户身份与成员关系确定可管理的景区。具体路径在实施计划中统一现有接口迁移策略。

## 8. 后台与发布体验

景区配置步骤：基本信息 → 选择数字人及声音 → 导入景区知识与图文 → 启用模块并选择模板 → 桌面/手机与语音预览 → 发布二维码。

配置支持草稿、校验、预览、发布与回滚。发布前校验模型兼容性、内容引用、服务电话、模块依赖；品牌、模块配置与内容版本组成一致的发布快照。索引准备好再切换公开版本，避免新卡片引用旧知识。没有路线内容时关闭路线模块，没有天气坐标时隐藏天气，不显示其他景区的备用数据。

景区包支持导入/导出品牌、公开素材、结构化内容、模块设置与版本声明。包中不包含 API Key、管理身份或游客聊天日志；导入先形成草稿、校验引用与资源路径，再由运营发布。大知识库内容按集合存储，前端不把全部数据塞入单个 JSON。

## 9. 共享平台的景区隔离要求

共享平台的基础标识是 siteId。数据库中的景点、路线、FAQ、知识分块、形象选择、素材、访客、对话、反馈、运营统计及管理成员关系必须带归属。后台授权不能只相信请求参数中的 siteId。

公开发布内容可按景区入口读取；会话和反馈使用绑定景区的服务端会话上下文。选中的实体、路线和资料要校验归属。所有检索路径（向量、关键词、FAQ、缓存及降级）必须限定当前景区，缺上下文时拒绝检索。

初期可共享关系数据库并强制使用景区范围查询；Chroma 可用景区及知识版本独立 collection，平台统一维护数量与索引生命周期。向量重建限定景区版本，不能调用共享集合的全量替换影响其他景区。后续按规模评估共享集合及严格过滤。

缓存键至少包含景区、内容/提示词版本，以及回答相关的模型、音色、语种、选择上下文等；欢迎语音加欢迎文案哈希。浏览器保存的会话和选择状态也按景区区分。切换景区时停止音频、录音与请求，释放摄像头并丢弃旧请求返回，清除旧模块状态。

后台角色建议从平台管理员、景区管理员、内容编辑开始。AI、TTS、ASR、天气供应商通过服务适配器调用，凭据存于服务端。共享模型推理资源，按景区配置限额与并发，防止某一景区耗尽公共服务。

## 10. 按收益分阶段实施

1. 通用前端与公共配置：中性品牌/文案/主题，新增游客公开配置入口，抽取 GuideShell/AvatarStage/VoiceControls，保留数字人居中布局；把灵山保留为显式演示景区。
2. 数据与模块替换：统一景点、路线与问题数据来源；建立模块注册表、标准动作与配置校验；支持开关、排序、模板替换；迁移预设数据到景区内容。
3. 后台自助与发布：接入已有形象/素材管理，增加基本信息、内容编辑、模块选择、草稿预览、发布回滚及景区包导入导出。
4. 共享平台基础：若选择共享部署，这一阶段应在多景区对外开放前完成；增加身份与成员授权，打通 API/SQL/RAG/缓存/素材/会话隔离，迁移旧数据到明确的演示景区归属。

各阶段可分开交付。第一轮可先演示不同景区配置如何改变页面，不能把仅前端切换主题宣称为已实现完整多租户。

成本方向：同一套代码和计算能力、预置可用数字人、常见讲解复用缓存、内容导入降低人工录入量；AI 提取的数据先由运营确认再发布。不承诺未经测量的接入工时、费用或模型兼容率。

## 11. 验收标准

- 两个明确标注为示例的不同类型景区包，例如自然公园与工业展馆，能用同一前端切换名称、背景、形象、声音、分类和内容；不用修改通用业务组件。
- 模块可以关闭、调序和替换实现，左右模块变化不重新加载数字人；小屏维持语音主入口。
- 默认或未配置状态不出现灵山、太湖、佛教类别及其服务热线；无数据时不回退到另一景区的景点、路线或事实。
- 更换导游姓名和欢迎文案后，显示、LLM 身份和欢迎语音一致；旧欢迎缓存失效。
- 已发布游客配置可匿名读取；草稿、管理功能和供应商凭据不可由游客配置接口取得。
- 同名景点、相同问题、旧会话、旧本地缓存和错误实体 ID 不造成跨景区引用。共享平台需专门验证全部检索及降级路径。
- 导入不兼容的配置、错误资源、未知模块时有可理解的校验提示，当前已发布服务继续可用。

尚待确认：第一阶段以共享平台多景区交付，还是独立部署交付。它决定隔离阶段的实施顺序，不影响前端模块协议的核心方向。
