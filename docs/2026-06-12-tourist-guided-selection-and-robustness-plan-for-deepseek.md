# 游客主动选择驱动的景区鲁棒对话技术方案（提交 DeepSeek）

- 编写日期：2026-06-12
- 项目根目录：`D:\桌面\软件杯`
- 方案定位：在当前 FAQ + Cache + RAG + Reranker 架构上，增加游客主动选择与真实景区鲁棒性能力
- 当前状态：仅完成技术方案，尚未修改代码
- 审查对象：DeepSeek / 项目负责人

## 1. 方案目标

在现有自由文本和后续语音交互之外，增加“游客主动选择驱动对话”能力，让游客可以主动选择：

1. 想了解的景点。
2. 想咨询的话题。
3. 想规划的路线。
4. 游览时间、同行人群和兴趣偏好。
5. 语音识别结果是否正确。
6. 回答后想继续追问的方向。

主动选择不是简单的快捷按钮，而是一个结构化的交互控制层：

```text
游客主动选择
  -> SelectionContext
  -> 会话状态与实体追踪
  -> 领域路由
  -> FAQ / RAG / POI / 实时工具
  -> 证据充分性判断
  -> 受约束回答
  -> 下一步推荐选项
```

该设计同时服务于以下真实景区问题：

1. 大模型可能编造事实。
2. 户外噪音和方言影响语音识别。
3. 多轮对话容易丢失上下文。
4. 厕所、天气、交通等知识盲区。
5. 节假日高并发压力。
6. 情感连接不足导致游客不信任。
7. 游客不知道该问什么，或表达不清楚。

## 2. 当前项目真实基础

### 2.1 已完成

1. FastAPI 后端与 Vue 3 + Pinia 前端骨架。
2. FAQ 88 条，支持内存匹配。
3. 问答缓存支持内存 LRU + 数据库存储，默认 TTL 7 天。
4. Knowledge 38 条，Knowledge Chunk 66 条。
5. `BAAI/bge-small-zh-v1.5` + ChromaDB 真实检索。
6. `BAAI/bge-reranker-base` 真实重排。
7. Reranker 异常时支持 BM25 与原向量顺序降级。
8. QueryRewriter 已支持少量别名和简单指代补全。
9. `ChatRequest` 已包含：
   - `session_id`
   - `input_mode`
   - `text_only`
   - `context.last_subject`
   - `context.history_summary`
10. 路线推荐后端已支持兴趣、可用时间、人群和避开拥挤偏好。
11. 知识管理后端已经具备查询、新增、修改和删除接口。
12. TTS、ASR、Avatar 已有抽象接口，但仍是 stub。

### 2.2 当前缺口

1. 游客端只有自由文本框和语音占位按钮。
2. 没有景点选择器、话题选择器、路线向导和快捷追问。
3. 路线推荐有后端接口，但没有游客端独立页面。
4. 会话上下文主要由前端传入，没有服务端会话状态。
5. `last_subject` 仅支持少数固定句式，不足以覆盖真实多轮对话。
6. 没有领域路由，所有非 FAQ 问题都会进入同一 RAG 链路。
7. 没有厕所、服务点等 POI 数据模型。
8. 没有天气、交通、票务等实时 Provider。
9. LLM 仍是占位实现，没有证据约束和回答校验。
10. ASR、TTS、Avatar 仍是占位实现。
11. Reranker 当前准确率达到 100%，但 CPU P95 为 6079.41ms，尚未确定性能方案。

## 3. 总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│ 游客交互端                                                   │
│ 文本输入 | 语音输入 | 景点选择 | 话题选择 | 路线向导 | 快捷追问 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Interaction Orchestrator                                    │
│ SelectionContext | ASR确认 | 会话状态 | 实体追踪 | 冲突处理    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ DomainRouter                                                │
│ FAQ | 景点知识RAG | 路线推荐 | POI | 天气 | 交通 | 边界回答     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Evidence Layer                                              │
│ FAQ证据 | Chroma证据 | POI证据 | 实时Provider证据 | 版本/时间戳 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Answer Policy                                               │
│ EvidenceGate | LLM受约束生成 | AnswerVerifier | 主动坦承边界   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 输出层                                                      │
│ 文本 | Sources | 快捷下一步 | TTS | 数字人表情/口型           │
└─────────────────────────────────────────────────────────────┘
```

## 4. 游客主动选择交互设计

## 4.1 首屏目标选择

游客进入系统后，先显示有限且清晰的目标入口：

```text
我想了解景点
帮我规划路线
查找厕所/餐饮/休息点
查看天气与交通
了解演出/开放时间
直接向导游提问
```

作用：

1. 减少游客不知道怎么提问的问题。
2. 提前确定领域，减少错误检索。
3. 高频需求不必全部进入 LLM。
4. 为低文化程度、儿童和老年游客降低使用门槛。

## 4.2 景点主动选择

提供两种形式：

1. 景点卡片/搜索列表。
2. 景区地图上的可点击 POI。

选择景点后显示可继续选择的话题：

```text
景点介绍
历史文化
建筑特色
游览时长
附近景点
附近服务设施
适合拍照的位置
无障碍信息
继续自由提问
```

示例：

```text
游客选择：灵山大佛
游客选择：历史文化
系统生成结构化意图：
domain = scenic_knowledge
active_attraction = 灵山大佛
topic = history
```

系统可以直接显示标准问题建议：

```text
灵山大佛什么时候建成？
灵山大佛为什么有 88 米高？
灵山大佛有哪些文化寓意？
```

## 4.3 路线偏好向导

复用当前 `RecommendRequest`，通过分步选择收集：

```text
可用时间：2 / 4 / 6 小时
同行人群：独自 / 情侣 / 家庭亲子 / 老年人 / 团队
兴趣：历史文化 / 自然风光 / 建筑艺术 / 祈福体验 / 摄影
体力偏好：轻松 / 适中 / 深度
是否避开拥挤：是 / 否
是否需要无障碍路线：是 / 否
```

游客得到路线后，可主动选择某一站继续对话：

```text
选择路线 -> 选择路线节点 -> 查看节点讲解 -> 询问附近设施
```

## 4.4 语音识别确认选择

语音识别置信度不足时，不直接进入问答：

```text
系统识别为：灵山大佛有多高

[正确，继续]
[选择景点：灵山大佛]
[重新说一次]
[改用文字]
```

如果 ASR 给出多个候选：

```text
您说的是：
[灵山大佛]
[灵山梵宫]
[五印坛城]
```

这样主动选择可以承担语音纠错，不需要让 LLM 猜测错误文本。

## 4.5 回答后的快捷追问

每次回答完成后，系统根据当前领域和实体生成 2–4 个下一步选项：

```text
继续了解历史
查看附近景点
加入我的路线
查找附近厕所
换一个景点
结束本话题
```

快捷追问只能来自受控模板或知识元数据，不应由 LLM 无限制自由生成。

## 4.6 选择轨迹展示

游客端显示当前选择面包屑：

```text
灵山胜境 > 灵山大佛 > 历史文化
```

游客可以点击任意层级切换或清除：

```text
清除话题
更换景点
重新选择路线
返回自由提问
```

这可以减少“系统到底在回答哪个景点”的不透明感。

## 5. SelectionContext 数据设计

建议不要继续无限扩展现有两个字符串字段，而是增加结构化上下文：

```python
class SelectionContext(BaseModel):
    mode: Literal[
        "free_chat",
        "attraction",
        "route",
        "poi",
        "weather",
        "traffic",
    ] = "free_chat"

    selected_attraction_id: str | None = None
    selected_attraction_title: str | None = None
    selected_topic: str | None = None
    selected_route_id: str | None = None
    selected_poi_type: str | None = None
    selected_question_id: str | None = None

    interests: list[str] = []
    audience_type: str | None = None
    available_hours: int | None = None
    avoid_crowded: bool | None = None
    accessibility_required: bool | None = None

    asr_text_confirmed: bool | None = None
    selection_source: Literal[
        "user_click",
        "voice_confirmation",
        "conversation_followup",
        "system_default",
    ] = "user_click"

    revision: int = 1
```

`ChatRequest` 扩展为：

```python
class ChatRequest(BaseModel):
    query: str
    session_id: str
    input_mode: Literal["text", "voice"]
    text_only: bool
    context: ConversationContext | None
    selection: SelectionContext | None
```

## 6. 上下文冲突与优先级

必须避免旧选择污染新问题。

建议优先级：

```text
1. 游客本轮明确文字中的实体
2. 游客本轮主动点击的选择
3. 服务端当前 active entity
4. 前端传入的历史 context
5. 系统默认值
```

示例：

```text
当前选择：灵山大佛
游客输入：五印坛城有什么特色？
```

必须切换主体到“五印坛城”，不能仍以“灵山大佛”过滤检索。

冲突规则：

1. 本轮文字实体与选择一致：正常执行。
2. 本轮文字实体与选择冲突：以文字实体为准，并更新选择状态。
3. 本轮只有“它、多高、附近”等指代：使用当前 active entity。
4. 无法唯一解析：返回 clarification 事件，让游客主动选择。
5. 长时间未活动或游客点击“新话题”：清空 active entity。

## 7. 服务端会话状态

当前上下文主要依赖前端传递，建议新增：

```text
SessionContextService
```

服务端保存：

```text
session_id
active_domain
active_attraction_id
active_attraction_title
active_topic
selected_route_id
preference_tags
audience_type
recent_entities
recent_turns
history_summary
last_sources
selection_revision
expires_at
```

存储策略：

1. 开发阶段可使用数据库。
2. 高并发阶段使用 Redis，数据库保留必要日志。
3. 活跃会话 TTL 建议 30 分钟。
4. 最近原文只保存 3–5 轮，其余压缩为摘要。
5. 选择变化产生新的 revision，避免前端旧请求覆盖新状态。

## 8. Interaction Orchestrator

新增：

```text
backend/app/services/interaction/orchestrator.py
```

职责：

1. 合并本轮文字、主动选择和服务端会话状态。
2. 提取或更新当前实体。
3. 检测冲突与歧义。
4. 决定是否需要 clarification。
5. 将标准化后的 `ResolvedInteractionContext` 交给领域路由。

输出示例：

```json
{
  "domain": "scenic_knowledge",
  "intent": "ask_history",
  "active_attraction": {
    "id": "attraction_lingshan_buddha",
    "title": "灵山大佛"
  },
  "topic": "history",
  "normalized_query": "灵山大佛 历史文化",
  "needs_clarification": false,
  "selection_revision": 4
}
```

## 9. DomainRouter

主动选择可显著提高路由确定性：

```text
mode=attraction -> 景点 FAQ / RAG
mode=route -> RecommendEngine
mode=poi -> ScenicPOIRepository
mode=weather -> WeatherProvider
mode=traffic -> TrafficProvider
mode=free_chat -> 意图分类后路由
```

建议新增：

```text
backend/app/services/interaction/domain_router.py
```

路由结果必须包含：

```text
domain
handler
reason
confidence
requires_realtime_data
```

主动选择产生的 domain confidence 可以视为高，但不能替代事实证据。

## 10. 主动选择与 RAG 的关系

### 10.1 选择用于过滤和改写

游客选择景点后：

1. 在 QueryRewriter 中补入景点实体。
2. 在 Chroma 查询时使用 metadata filter。
3. 优先检索该景点对应 chunk。
4. 必要时再放宽到全景区知识。

建议检索流程：

```text
第一层：selected_attraction_id 范围内检索
第二层：第一层证据不足时，全知识库补充检索
```

这是“两级检索”的具体实现。

### 10.2 选择不能作为证据

例如游客点击“灵山大佛 88 米”，前端标签本身不能作为回答依据。

正确流程：

```text
选择“灵山大佛”
-> 用于限定检索范围
-> 从官方 chunk 检索到“88 米”
-> 回答引用官方 chunk
```

禁止：

```text
直接把前端按钮文字当作事实写入答案
```

## 11. 针对六类真实景区问题的技术方案

## 11.1 问题一：大模型编造事实

### 当前基础

1. FAQ、Cache、Chroma、Reranker 已接入。
2. Sources 已返回标题、摘要、来源和分数。
3. LLM 仍是 stub。

### 技术方案

新增：

```text
EvidenceGate
EvidenceBundle
AnswerPolicy
AnswerVerifier
```

完整流程：

```text
主动选择限定领域/景点
-> FAQ 或两级 RAG
-> EvidenceGate 判断证据充分性
-> 证据充分才进入 LLM
-> LLM 只能依据 EvidenceBundle
-> AnswerVerifier 检查数字、时间、地点和引用
-> 不足时主动坦承
```

`EvidenceBundle`：

```json
{
  "domain": "scenic_knowledge",
  "selection": {
    "attraction": "灵山大佛",
    "topic": "history"
  },
  "documents": [
    {
      "chunk_id": "ke_13_001",
      "title": "灵山大佛",
      "content": "...",
      "source": "官方资料.docx",
      "score": 0.98,
      "knowledge_version": 3
    }
  ],
  "sufficient": true
}
```

证据不足时：

```text
目前景区资料中没有足够信息回答这个问题。
您可以选择：
[查看景点基础介绍]
[换一个问题]
[提交给景区补充]
```

验收：

1. 所有事实回答必须有来源。
2. 无证据问题不得编造。
3. 数字、时间和地点必须可在证据中定位。
4. 主动选择不能被记录为事实来源。

## 11.2 问题二：户外噪音和方言

### 当前基础

1. `input_mode` 已支持 voice。
2. ASR 接口已预留，但仍是 stub。
3. 前端已有语音按钮占位。

### 技术方案

```text
WebRTC降噪/回声消除
-> VAD
-> 流式ASR
-> 景区热词增强
-> ASR置信度闸门
-> 主动确认/景点选择
-> 正式问答
```

景区热词来源：

1. Knowledge title。
2. aliases。
3. Route title 和 guide points。
4. POI 名称。
5. 管理端维护的常见误识别映射。

置信度策略建议：

```text
>= 0.75：直接进入问答
0.50–0.75：显示文本，请游客确认
< 0.50：要求重说、选择景点或改用文本
```

低置信确认事件：

```json
{
  "type": "clarification",
  "data": {
    "reason": "low_asr_confidence",
    "recognized_text": "灵山大佛有多高",
    "options": [
      {"type": "confirm_text", "label": "正确，继续"},
      {"type": "select_attraction", "id": "lingshan_buddha", "label": "灵山大佛"},
      {"type": "retry_voice", "label": "重新说一次"},
      {"type": "switch_text", "label": "改用文字"}
    ]
  }
}
```

主动选择成为语音失败时的正式降级通道。

## 11.3 问题三：多轮对话上下文丢失

### 当前基础

1. 有 `last_subject` 和 `history_summary`。
2. QueryRewriter 只能处理少量固定追问。

### 技术方案

1. 服务端保存会话状态。
2. 主动选择更新 active entity。
3. 每轮提取景点、路线、POI 和话题实体。
4. 指代消解使用最近 active entity。
5. 文字实体与旧选择冲突时，以本轮文字为准。
6. 回答后返回当前选择和建议追问。

示例：

```text
游客选择：灵山大佛
游客：它多高？
系统：灵山大佛高 88 米……
游客点击：附近景点
系统：以灵山大佛为中心查询附近景点……
游客：五印坛城呢？
系统：切换 active entity 为五印坛城。
```

验收：

1. 连续 5 轮不丢失主体。
2. 切换景点后旧主体不再污染检索。
3. 刷新页面后同一 session 可以恢复当前选择。
4. 新话题操作可以彻底清空上下文。

## 11.4 问题四：厕所、天气、交通等知识盲区

### 当前基础

1. Knowledge 管理 API 已存在。
2. 没有 POI 模型和实时 Provider。

### 技术方案

主动选择首屏直接提供领域入口，避免将所有问题错误送入景点 RAG。

新增 POI 模型：

```text
ScenicPOI
poi_id
name
poi_type
description
longitude
latitude
nearby_attraction_id
accessible
opening_status
source
updated_at
```

`poi_type`：

```text
toilet
restaurant
rest_area
medical
service_center
parking
exit
accessible_facility
```

新增 Provider：

```text
WeatherProvider
TrafficProvider
TicketProvider
OperationScheduleProvider
```

实时回答必须包含：

```text
数据来源
更新时间
适用地点
是否可能变化
```

知识盲区回答：

```text
当前资料中没有该信息。
[查看景区服务设施]
[切换到天气查询]
[切换到交通查询]
[向管理端提交待补充问题]
```

管理端补充：

1. POI 管理。
2. 快捷问题模板管理。
3. 话题分类管理。
4. 知识版本与索引更新。
5. 未回答问题列表。

## 11.5 问题五：节假日高并发

### 当前基础

1. FAQ 优先。
2. Cache 默认 7 天。
3. 当前内存 LRU 上限 128。
4. Reranker CPU P95 约 6.08 秒，是最大风险。

### 技术方案

主动选择可以将大量请求转为确定性快速通道：

```text
主动选择标准问题
-> FAQ/模板答案
-> 不走 Reranker
-> 不走 LLM
```

建议通道优先级：

```text
1. 标准选项 + FAQ
2. 标准选项 + 缓存
3. 路线推荐/POI确定性服务
4. 高置信 Chroma
5. 条件式 Reranker
6. LLM
```

高并发措施：

1. Redis 会话与分布式缓存。
2. SingleFlight 防止热门问题并发重复生成。
3. FAQ、路线、POI 和预生成 TTS 缓存。
4. Embedding、Reranker、LLM 独立并发限制。
5. 超载降级：
   - 关闭数字人复杂动画。
   - 关闭 TTS，只返回文本。
   - 条件式跳过 Reranker。
   - 只开放 FAQ、缓存、POI 和路线。
6. 主动选择选项和答案做 CDN/前端静态缓存。

必须统计真实命中率，不能直接宣称 FAQ 一定覆盖 60%。

验收指标：

```text
主动选择快速通道 P95 < 300ms
FAQ P95 < 100ms
缓存 P95 < 100ms
系统过载时仍可返回降级答案
热门问题不会重复触发多个 LLM 请求
```

## 11.6 问题六：情感连接不足

### 当前基础

1. Avatar 和 TTS 有抽象接口。
2. Avatar 当前固定 `neutral`。
3. 行为摘要已进入后台。

### 技术方案

主动选择提供更可控的情感场景：

```text
游客选择“亲子游” -> friendly / lively
游客选择“历史文化” -> calm / respectful
游客选择“需要帮助” -> concerned / reassuring
游客选择“祈福体验” -> warm / solemn
```

新增：

```text
SentimentAnalyzer
DialogueStylePlanner
TTSStyleMapper
AvatarEmotionPlanner
```

处理顺序：

```text
先生成事实正确的答案
-> 再根据游客情绪与主动选择调整表达风格
-> 映射到 TTS 韵律
-> 映射到数字人表情和动作
```

情感层不得改变：

1. 数字。
2. 时间。
3. 地点。
4. 开放状态。
5. 来源。

Avatar Payload 建议：

```json
{
  "emotion": "friendly",
  "intensity": 0.65,
  "visemes": [],
  "gestures": ["nod"],
  "timeline": []
}
```

## 12. 前端模块方案

建议新增：

```text
frontend/src/components/interaction/GoalSelector.vue
frontend/src/components/interaction/AttractionPicker.vue
frontend/src/components/interaction/TopicSelector.vue
frontend/src/components/interaction/QuickQuestionChips.vue
frontend/src/components/interaction/SelectionBreadcrumb.vue
frontend/src/components/interaction/ClarificationCard.vue
frontend/src/components/interaction/RouteWizard.vue
frontend/src/components/interaction/POIPicker.vue
frontend/src/stores/interaction.js
```

现有 `ChatView.vue` 变为组合容器：

```text
顶部：当前选择 Breadcrumb
左侧：聊天内容
底部：自由输入 + 快捷问题
右侧：景点/话题/路线选择面板
移动端：选择面板改为底部抽屉
```

用户可以随时：

```text
继续自由提问
点击快捷问题
切换景点
切换话题
清除上下文
确认 ASR 文本
进入路线向导
```

## 13. 后端 API 方案

## 13.1 交互初始化

```http
GET /api/interaction/bootstrap
```

返回：

```json
{
  "goals": [],
  "featured_attractions": [],
  "topics": [],
  "quick_questions": [],
  "poi_types": [],
  "route_preferences": {}
}
```

## 13.2 更新选择状态

```http
PUT /api/sessions/{session_id}/selection
```

请求：

```json
{
  "selection": {},
  "expected_revision": 3
}
```

使用 revision 防止旧页面覆盖新状态。

## 13.3 获取会话状态

```http
GET /api/sessions/{session_id}/context
```

## 13.4 清除或切换话题

```http
DELETE /api/sessions/{session_id}/context
POST /api/sessions/{session_id}/new-topic
```

## 13.5 聊天请求扩展

继续使用：

```http
POST /api/chat/stream
```

但增加 `selection` 字段，并新增 SSE 事件：

```text
selection_state
clarification
suggestions
domain_route
evidence_status
```

## 14. 数据模型方案

建议新增：

```text
SessionContext
ScenicPOI
InteractionOption
QuickQuestionTemplate
SelectionEvent
UnansweredQuestion
KnowledgeVersion
```

### SelectionEvent

用于统计游客如何使用主动选择：

```text
id
session_id
event_type
option_type
option_id
previous_value
new_value
source
created_at
```

用途：

1. 判断最常被选择的景点和话题。
2. 计算主动选择快速通道命中率。
3. 分析 ASR 纠错次数。
4. 发现游客最常遇到的知识盲区。

## 15. 缓存键和知识版本

主动选择加入后，缓存键不能只使用 normalized query。

建议：

```text
cache_key = hash(
    normalized_query,
    active_domain,
    selected_attraction_id,
    selected_topic,
    selected_route_id,
    language,
    knowledge_version,
)
```

实时天气和交通：

1. 使用短 TTL。
2. 缓存键包含地点和时间范围。
3. 不能复用 7 天问答缓存。

知识更新后：

1. 增加 `knowledge_version`。
2. 新版本自动使旧答案缓存失效。
3. 重建受影响的 Chroma chunk。

## 16. 安全与隐私边界

1. 不保存原始语音，除非用户明确同意。
2. 会话状态只保存完成服务所需的偏好和实体。
3. 不收集身份证、手机号等非必要信息。
4. 选择日志用于匿名统计，不存储敏感个人数据。
5. 天气、交通等 Provider 失败时显示数据不可用，不伪造。
6. 管理端修改快捷问题和知识时需要权限控制与审计日志。

## 17. 实施阶段建议

### Phase 0：先解决 Reranker 性能决策

当前阻塞：

```text
准确率 = 100%
Reranker P95 = 6079.41ms
```

在 DeepSeek 给出性能方案前，不应直接进入真实 LLM。

### Phase 1：主动选择最小闭环

1. 新增 `SelectionContext`。
2. 新增 Interaction Store。
3. 实现 GoalSelector、AttractionPicker、TopicSelector。
4. ChatRequest 携带 selection。
5. 后端将选择用于 QueryRewriter 和日志。
6. 返回受控快捷追问。

该阶段暂不加入复杂地图和实时 Provider。

### Phase 2：服务端会话与冲突处理

1. SessionContext 数据模型。
2. Interaction Orchestrator。
3. 实体提取和指代消解。
4. revision 与 TTL。
5. 新话题和清空上下文。

### Phase 3：领域路由与知识盲区

1. DomainRouter。
2. ScenicPOI。
3. Weather/Traffic Provider 接口。
4. Clarification 和边界回答。
5. 管理端 POI/快捷问题维护。

### Phase 4：真实 LLM 与证据链

1. EvidenceGate。
2. EvidenceBundle。
3. 受约束 LLM Prompt。
4. AnswerVerifier。
5. 100 题端到端评测。

### Phase 5：高并发能力

1. Redis。
2. SingleFlight。
3. 分层缓存。
4. 并发限制。
5. 过载降级。

### Phase 6：ASR 与主动确认

1. VAD。
2. 流式 ASR。
3. 景区热词。
4. 置信度闸门。
5. 主动选择确认。

### Phase 7：TTS、情感与数字人

1. 真实 TTS。
2. 情感分析和风格规划。
3. 音素/viseme 时间轴。
4. 数字人表情与动作。

## 18. 验收指标

## 18.1 主动选择

```text
游客 3 次点击内可以进入指定景点话题
选择状态更新 P95 < 200ms
选择与文字冲突解析正确率 >= 95%
选择后检索目标景点 Recall@5 >= 95%
主动选择不能作为事实来源
```

## 18.2 多轮上下文

```text
5 轮连续追问实体保持正确率 >= 95%
切换景点后的旧实体污染率 = 0
新话题清空成功率 = 100%
```

## 18.3 证据与可靠性

```text
事实回答有来源比例 = 100%
无证据主动坦承比例 = 100%
100 题事实准确率 >= 90%
```

## 18.4 语音鲁棒性

```text
低置信 ASR 不直接进入问答
主动确认后错误景点进入率 < 2%
ASR 失败时文本/选择降级成功率 = 100%
```

## 18.5 高并发

```text
FAQ / Cache / 主动选择快速通道 P95 < 300ms
同问题 SingleFlight 合并成功
过载降级期间核心文字服务可用
```

## 18.6 最终体验

```text
FAQ 语音回答 < 2s
RAG + LLM 首 token < 2.5s
文本回答可见 < 3s
语音和数字人首段反馈 < 5s
```

最终延迟预算需在 Reranker 性能方案确定后重新校准。

## 19. 请求 DeepSeek 审查的问题

请重点回答：

1. 将游客主动选择设计为独立 `SelectionContext` 是否合理，还是应并入现有 `ConversationContext`？
2. “文字实体 > 本轮选择 > 服务端 active entity > 历史 context”的优先级是否正确？
3. 主动选择限定景点后，是否应使用 Chroma metadata filter 做第一层检索？
4. 第一层景点检索证据不足后再全局检索的两级策略是否合理？
5. 受控快捷问题应存数据库、配置文件还是由知识元数据动态生成？
6. SessionContext 开发阶段使用数据库、生产阶段使用 Redis 的迁移方案是否合理？
7. Selection revision 是否有必要，还是会造成过度设计？
8. 路线推荐是否应继续作为独立确定性服务，而不是交给 LLM？
9. POI、天气、交通是否应全部通过 DomainRouter 与 RAG 分离？
10. 当前 Reranker 性能未解决时，是否可以先实现 Phase 1 主动选择闭环，还是应完全停止？
11. 主动选择能否作为条件式 Reranker 的可靠路由依据？
12. 上述验收指标是否合理，哪些需要调整？
13. 整体阶段顺序是否符合赛题最终数字人导游要求？
14. 是否遗漏真实景区中必须考虑的交互异常或降级路径？

## 20. 希望 DeepSeek 输出格式

```text
一、总体可行性判断
二、游客主动选择层的架构审查
三、六类鲁棒性方案逐项审查
四、需要删除或简化的设计
五、必须补充的设计
六、推荐的实施顺序
七、下一阶段允许修改的具体文件
八、每阶段验收指标
九、Reranker 性能问题与主动选择开发是否可以并行
十、是否同意进入 Phase 1
```

## 21. 当前停止边界

在 DeepSeek 审查和用户确认前：

1. 不修改 ChatRequest 和数据库模型。
2. 不新增前端选择组件。
3. 不修改 RAG metadata filter。
4. 不新增 Redis、实时 Provider 或 ASR 依赖。
5. 不进入真实 LLM。
6. 不调整 Reranker 参数或模型。

本轮仅完成方案文档。
