# Codex 鲁棒性与游客主动选择方案 — 审查修正确认

> 审查时间：2026-06-12。对照 `08-鲁棒性增强与游客主动选择技术方案.md` 和 `2026-06-12-tourist-guided-selection-and-robustness-plan-for-deepseek.md`，给出修正意见。Codex 请按本文档的简化方案执行。

---

## 一、总体评价

**方向正确，粒度失控。** 核心思想——游客主动选择驱动对话——完全正确。但引入了 5 个新抽象层（Interaction Orchestrator、DomainRouter、EvidenceGate、AnswerPolicy、AnswerVerifier）、7 个新数据模型、Redis 迁移计划，远超赛题实际需要的范围。

```
当前系统只有 3 个实际领域（FAQ、RAG、Recommend），不是 10 个。
每个领域目前只有一个 handler。
5 层抽象是为了一个 if/elif 能解决的问题。
```

---

## 二、保留项（Codex 方案中正确且必须采纳的设计）

### ✅ 保留 1：SelectionContext 结构化模型

Codex 的 `SelectionContext` 比 `08 文档` 中的 2 个平铺字段更好：

```python
# 采用 Codex 方案 ─ 不要用平铺字段
class SelectionContext(BaseModel):
    mode: Literal["free_chat", "attraction", "route", "poi"] = "free_chat"
    selected_attraction_id: str | None = None
    selected_attraction_title: str | None = None
    selected_topic: str | None = None
    selected_route_id: str | None = None
    interests: list[str] = []
    audience_type: str | None = None
    available_hours: int | None = None
    avoid_crowded: bool | None = None
```

`ChatRequest` 添加一个字段：

```python
class ChatRequest(BaseModel):
    # ... 现有字段不变 ...
    selection: SelectionContext | None = None  # 新增
```

### ✅ 保留 2：上下文冲突优先级

```text
1. 本轮文字中明确出现的实体
2. 本轮主动点击的选择
3. 服务端当前 active entity
4. 前端传入的历史 context
5. 系统默认值
```

示例：

```text
游客选择了"灵山大佛"，但输入"五印坛城有什么特色？"
→ 必须切换主体到五印坛城
```

### ✅ 保留 3：回答后快捷追问

每次回答完成后，系统根据当前领域和实体生成 2-4 个下一步选项：

```text
继续了解历史 | 查看附近景点 | 加入我的路线 | 查找附近厕所
```

**约束**：快捷追问只能来自受控模板或知识元数据，不能让 LLM 自由生成。

### ✅ 保留 4：选择面包屑展示

```text
灵山胜境 > 灵山大佛 > 历史文化
```

### ✅ 保留 5：选择不能作为事实来源

前端按钮文字不能作为回答依据。选择只用于限定检索范围，事实必须来自官方 chunk。

### ✅ 保留 6：含选择上下文的缓存键

```python
cache_key = hash(normalized_query, active_domain, selected_attraction_id, selected_topic)
```

---

## 三、删除 / 简化项

### ❌ 删除 1：Interaction Orchestrator + DomainRouter + EvidenceGate 五层抽象

**原方案**：

```text
InteractionOrchestrator → 合并选择+会话状态 → ResolvedInteractionContext
DomainRouter → route to FAQ/RAG/POI/Weather/Traffic → handler + confidence
EvidenceGate → 判断证据充分性 → EvidenceBundle
AnswerPolicy → 受约束生成
AnswerVerifier → 事后校验
```

**修正方案**：全部合并到 `pipeline.py` 内部方法：

```python
# pipeline.py — 加 3 个内部方法，不新增独立文件

class QAPipeline:
    async def _resolve_interaction(self, request: ChatRequest) -> ResolvedContext:
        """合并 selection + 文字实体 + 冲突解析"""
        ...

    async def _route_domain(self, ctx: ResolvedContext) -> DomainResult:
        """if/elif 路由到 FAQ / RAG / Recommend"""
        ...

    async def _verify_answer(self, answer: str, documents: list) -> VerificationResult:
        """事后校验数字/时间/地点/引用"""
        ...
```

**不新增文件**：`orchestrator.py`、`domain_router.py`、`evidence_gate.py` 全部去掉。

### ❌ 删除 2：服务端 SessionContext + Redis 迁移

**原方案**：服务端保存会话状态，开发用 DB、生产用 Redis，30 分钟 TTL。

**修正方案**：保持前端驱动模式。`SelectionContext` 由前端在每次 `ChatRequest` 中完整传入。

理由：

- 当前 `ConversationContext` 由前端传入，工作良好
- 服务端会话状态引入 session 生命周期、多 tab 冲突、Redis 部署等复杂性
- "刷新恢复"的收益远小于引入状态一致性的风险
- 如果确实需要恢复选择状态，前端 `localStorage` 即可

### ❌ 删除 3：ScenicPOI + WeatherProvider + TrafficProvider + TicketProvider

**原方案**：新增 POI 模型（厕所/餐饮/停车/医疗等 8 类）、实时天气/交通/票务 Provider。

**修正方案**：本轮不实现。赛题资料包无这四类数据，需要外部采集。

替代：

- 盲区问题（厕所、停车场）通过 `KnowledgeBlindSpot` 表追踪，管理员可录入为 FAQ 条目
- 在架构文档中声明 provider 接口预留——已有 Weather/Traffic/Ticket Provider 的 `base.py` 抽象接口
- 不新增 `models/scenic_poi.py`

### ❌ 删除 4：Selection revision 乐观锁

`PUT /api/sessions/{session_id}/selection` + `expected_revision` → 去掉。

理由：游客端单用户单页面操作，不存在两个客户端同时修改选择状态的场景。即使有，last-write-wins 完全可接受。

### ❌ 删除 5：Phase 0 阻塞策略

**原方案**：在 Reranker 性能方案确定前，不进入真实 LLM，不修改任何选择相关代码。

**修正方案**：Reranker 优化和主动选择开发**并行推进**。它们是正交维度。

| 工作项 | 依赖 Reranker 决策？ | 可立即启动？ |
|--------|:--:|:--:|
| SelectionContext + ChatRequest 扩展 | ❌ | ✅ |
| QuickTopic/Spot 表 + API | ❌ | ✅ |
| 前端选择组件 | ❌ | ✅ |
| Pipeline 注入 guided_selector | ❌ | ✅ |
| 条件式 Reranker | ✅ | ❌ 等待决策 |
| Reranker 参数调优 | ✅ | ❌ 等待决策 |
| LLM System Prompt + AnswerValidator | ❌ | ✅ |

---

## 四、缺失项（需补充）

### ➕ 补充 1：LLM 方言/口语改写层

Codex 的 ASR 方案只提到了降噪、VAD、热词增强、置信度闸门。缺少**方言→普通话的 LLM 改写**。

灵山胜境位于无锡（吴语区），ASR 即使置信度 0.6-0.8，识别文本可能含吴语同音错字（"零三"→"灵山"）。

在 `backend/app/services/asr/dialect_rewriter.py` 中实现（参考 `08 文档` §三）。

### ➕ 补充 2：FAQ L3 语义匹配补完

当前 FAQ 语义匹配（L3）是 `return None` 的 stub。补完 L3 可将命中率从 ~60% 提升到 75%+。

在 `backend/app/services/qa/faq_matcher.py` 中补完 `match_semantic` 方法（参考 `08 文档` §六.2.1）。

### ➕ 补充 3：知识盲区管理端闭环

Codex 提到了 `UnansweredQuestion` 模型，但缺少：
- 管理端按频次排序查看盲区
- 管理员补充答案后自动进入 FAQ 索引

在 `backend/app/api/admin.py` 中新增 `GET /blind-spots` + `POST /blind-spots/{id}/fill`。

---

## 五、修正后的文件改动清单

```
新增 (7):
├── backend/app/schemas/selection.py                    # SelectionContext Pydantic
├── backend/app/models/quick_select.py                  # QuickTopic + QuickSpot ORM
├── backend/app/repositories/quick_select.py            # 仓储
├── backend/app/services/qa/guided_selector.py          # 引导选择器
├── backend/app/api/quick_select.py                     # GET /bootstrap, /topics, /spots
├── frontend/src/components/interaction/GoalSelector.vue
├── frontend/src/stores/interaction.js

修改 (10):
├── backend/app/schemas/chat.py                         # ChatRequest + selection
├── backend/app/services/qa/pipeline.py                 # 注入 guided_selector + 快捷追问
├── backend/app/services/qa/faq_matcher.py              # L3 语义匹配补完
├── backend/app/api/chat.py                             # pipeline 构造传参
├── backend/app/api/router.py                           # 注册 quick_select 路由
├── backend/app/api/admin.py                            # 盲区管理 API
├── backend/app/db/bootstrap.py                         # 默认 QuickTopic/Spot 数据
├── backend/app/db/base.py                              # 注册新模型
├── backend/app/core/config.py                          # 新增 quick_select 相关配置
├── frontend/src/views/tourist/ChatView.vue             # 组合选择组件 + 面包屑

明确不做 (以下文件/功能本轮不创建):
├── backend/app/services/interaction/orchestrator.py    ❌
├── backend/app/services/interaction/domain_router.py   ❌
├── backend/app/services/interaction/evidence_gate.py   ❌
├── backend/app/services/interaction/answer_policy.py   ❌
├── backend/app/services/interaction/answer_verifier.py ❌ → 合并到 pipeline.py
├── backend/app/models/scenic_poi.py                    ❌
├── backend/app/models/session_context.py               ❌
├── backend/app/models/selection_event.py               ❌
├── backend/app/services/providers/weather.py           ❌
├── backend/app/services/providers/traffic.py           ❌
├── backend/app/services/providers/ticket.py            ❌
├── Redis / SingleFlight / 分布式缓存                    ❌
└── Selection revision 乐观锁                            ❌
```

---

## 六、修正后的执行顺序

```
并行轨道 A：Reranker 性能优化
├── 条件式 Reranker 阈值确定
├── candidate_k + max_length 调参
└── 验收：P50 < 800ms（A+B 优化后）

并行轨道 B：主动选择最小闭环
├── Step 1：SelectionContext 模型 + ChatRequest 扩展
├── Step 2：QuickTopic + QuickSpot 表 + API + bootstrap
├── Step 3：GoalSelector + AttractionPicker + TopicSelector 前端组件
├── Step 4：Pipeline 注入 guided_selector
│           ├── 检索增强：selection → search_boost 拼入检索 query
│           ├── 回答引导：selection → prompt_hint 注入 LLM
│           ├── 快捷追问：回答后返回 2-4 个下一步选项
│           ├── 冲突处理：文字实体优先于选择
│           └── 面包屑：前端展示当前选择层级
├── Step 5：FAQ L3 语义匹配补完
└── Step 6：知识盲区追踪表 + 管理端 API

后续阶段（本轮不做框架层新抽象）：
├── Phase C：LLM 真实化 + 证据链 Prompt + AnswerValidator
├── Phase D：会话上下文 + 指代消解 + SnowNLP 情感 + 人格化话术
└── Phase E：ASR + 方言改写（外部 API 账号到位后）
```

---

## 七、验收标准（修正版）

| 指标 | 门槛 | 说明 |
|------|------|------|
| 游客 3 次点击内可进入指定景点话题 | 100% | 前端交互 |
| 选择后检索目标景点 Recall@5 | ≥ 95% | 30 题评测 |
| 选择与文字冲突解析正确率 | ≥ 95% | 手动 10 条测试 |
| 选择状态更新 P95 | < 200ms | 无额外 API 调用，纯前端 |
| 5 轮连续追问实体保持正确率 | ≥ 90% | 指代消解后 |
| 切换景点后旧实体污染率 | < 5% | 冲突处理 |
| 事实回答有来源比例 | 100% | LLM 接入后 |
| 无证据主动坦承比例 | 100% | LLM 接入后 |
| FAQ / 主动选择快速通道 P95 | < 100ms | 不经过 Reranker 和 LLM |
| 现有 20 个后端测试 | 全部通过 | 不退化 |

---

## 八、关键约束

1. **不新增抽象层文件**。Orchestrator / DomainRouter / EvidenceGate / AnswerPolicy / AnswerVerifier 全部作为 `pipeline.py` 的私有方法。
2. **保持前端驱动**。选择状态由前端在每次 `ChatRequest.selection` 中完整传入，不引入服务端 session 存储。
3. **POI / Weather / Traffic 只做接口预留**。在 `providers/` 目录下写 `base.py` 声明抽象类即可，不做实现。
4. **不做 Selection revision**。
5. **不阻塞 Reranker 优化**。主动选择代码与 Reranker 性能调参可并行。
6. **每完成一个 Step 运行 `pytest` 确认 20 个测试不退化**。

---

## 九、数据预设（直接使用）

```python
# backend/app/db/bootstrap.py — 新增

DEFAULT_QUICK_TOPICS = [
    {"key": "attractions",    "label": "景点介绍", "icon": "🏯", "category": "explore",
     "search_hint": "knowledge_entries",   "prompt_hint": "请详细说明选中景点的特色与历史"},
    {"key": "history",        "label": "历史文化", "icon": "📜", "category": "explore",
     "search_hint": "历史|文化|朝代|渊源|典故", "prompt_hint": "请从历史渊源和文化内涵角度介绍"},
    {"key": "routes",         "label": "路线推荐", "icon": "🗺️", "category": "recommend",
     "search_hint": None,                   "prompt_hint": None},
    {"key": "practical",      "label": "实用信息", "icon": "🎫", "category": "faq",
     "search_hint": "faq",                  "prompt_hint": None},
    {"key": "blessing",       "label": "祈福体验", "icon": "🙏", "category": "explore",
     "search_hint": "祈福|摸佛脚|抱佛脚|天下第一掌|许愿|百子戏弥勒",
     "prompt_hint": "请从祈福文化和互动体验的角度介绍"},
    {"key": "architecture",   "label": "建筑艺术", "icon": "🏛️", "category": "explore",
     "search_hint": "建筑|梵宫|坛城|塔|雕刻|青铜|琉璃|壁画|穹顶",
     "prompt_hint": "请从建筑风格、工艺技法和艺术价值角度介绍"},
    {"key": "family",         "label": "亲子游玩", "icon": "👨‍👩‍👧", "category": "recommend",
     "search_hint": "亲子|家庭|孩子|互动|体验|适合",
     "prompt_hint": "请面向带孩子的家庭给出友好建议"},
    {"key": "dining",         "label": "餐饮服务", "icon": "🍽️", "category": "faq",
     "search_hint": "餐饮|吃饭|素食|素斋|素面|餐厅",
     "prompt_hint": None},
]

DEFAULT_QUICK_SPOTS = [
    {"key": "lingshan_big_buddha", "label": "灵山大佛",
     "search_hint": "灵山大佛", "prompt_hint": "请详细介绍灵山大佛"},
    {"key": "nine_dragons_bath",   "label": "九龙灌浴",
     "search_hint": "九龙灌浴|太子佛像", "prompt_hint": "请详细介绍九龙灌浴"},
    {"key": "brahma_palace",       "label": "梵宫",
     "search_hint": "梵宫|灵山梵宫", "prompt_hint": "请详细介绍梵宫"},
    {"key": "five_seals_mandala",  "label": "五印坛城",
     "search_hint": "五印坛城|坛城", "prompt_hint": "请详细介绍五印坛城"},
    {"key": "xiangfu_temple",      "label": "祥符禅寺",
     "search_hint": "祥符禅寺", "prompt_hint": "请详细介绍祥符禅寺"},
    {"key": "first_palm",          "label": "天下第一掌",
     "search_hint": "天下第一掌|佛手|摸天下第一掌", "prompt_hint": "请详细介绍天下第一掌"},
    {"key": "bodhi_avenue",        "label": "菩提大道",
     "search_hint": "菩提大道", "prompt_hint": "请详细介绍菩提大道"},
    {"key": "ashoka_pillar",       "label": "阿育王柱",
     "search_hint": "阿育王柱", "prompt_hint": "请详细介绍阿育王柱"},
]
```

---

## 十、结论

**批准执行 Phase 1 主动选择最小闭环，但不批准原方案的 5 层抽象和 7 个新数据模型。**

| # | 修正项 | 严重度 | 说明 |
|---|--------|:--:|------|
| 1 | 删除 Orchestrator/DomainRouter/EvidenceGate → 合并到 pipeline | 🔴 | 防止过度抽象 |
| 2 | 删除服务端 SessionContext + Redis → 保持前端驱动 | 🔴 | 防止不必要的复杂性 |
| 3 | 删除 ScenicPOI/Weather/Traffic/Ticket Provider → 接口预留 | 🔴 | 资金数据不在资料包内 |
| 4 | 删除 Selection revision 乐观锁 → 直接覆盖 | 🟡 | 解决不存在的并发问题 |
| 5 | 取消 Phase 0 阻塞 → Reranker 与主动选择并行 | 🟡 | 正交维度不应串行 |
| 6 | 补充方言改写 + FAQ L3 + 盲区闭环 | 🟡 | 08 文档已有设计 |
| 7 | 采纳 SelectionContext 结构化模型 | ✅ | Codex 方案优于扁平字段 |
| 8 | 采纳上下文冲突优先级 + 快捷追问 + 面包屑 | ✅ | 正确且必要 |

**修正后，本轮新增文件从 ~25 个减少到 7 个，修改文件从 ~15 个减少到 10 个。架构保持扁平，所有路由逻辑在 `pipeline.py` 内闭环。可立即启动，不阻塞于 Reranker 性能决策。**
