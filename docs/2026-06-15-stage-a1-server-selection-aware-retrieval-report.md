# 阶段 A1 实施报告：服务端选择校验与选择感知检索

- 日期：2026-06-15
- 状态：本切片已完成并通过回归，等待用户确认下一步
- 对应主线：`设计文档/10-最终总体设计与开发主线.md` 主线阶段 A / 轨道 A1
- 前置能力：SelectionContext、bootstrap API、游客端主动选择与请求携带已完成

## 一、本切片目标

让前端传来的选择上下文第一次真正影响服务端问答链路，同时保持“选择只是检索线索，不是事实证据”的原则。

完成后：

1. 服务端逐轮回查景点、话题和路线ID。
2. 本轮文字中明确出现的景点优先于按钮选择。
3. 选择或文字实体生成结构化检索范围。
4. Chroma和SQL降级检索都遵守同一范围。
5. 缓存键区分不同景点、话题和路线。
6. SSE返回服务端确认后的上下文，前端据此更新选择。

## 二、明确不做

1. 不实现服务端长期SessionContext或Redis。
2. 不实现代词指代的LLM消解。
3. 不实现快捷追问。
4. 不实现FAQ L3或Reranker性能闸门。
5. 不修改数据库表结构，不新增依赖。
6. 不把话题按钮文本、ASR文本或选择内容当作回答证据。

## 三、最小架构

新增一个轻量 `GuidedSelectionResolver`，位于 `services/qa/`，职责仅限：

1. 校验SelectionContext中的数据库ID。
2. 从本轮文字中匹配官方知识条目的标题/别名。
3. 按优先级生成服务端可信的ResolvedSelection。
4. 生成类型安全的RetrievalScope。

`QAPipeline`仍只负责编排：调用resolver、生成缓存键、传递检索范围和发送SSE事件。实体匹配与数据库验证不直接堆入pipeline。

## 四、冲突优先级

本切片实现：

1. 本轮文字中明确出现并能在官方知识库验证的景点。
2. 本轮有效按钮选择。
3. `ConversationContext.last_subject`中能验证的景点。
4. 无范围的自由提问。

示例：按钮选择“灵山大佛”，文字输入“五印坛城有什么特色”，最终范围必须是五印坛城。

## 五、检索范围

新增 `RetrievalScope`：

```python
@dataclass(frozen=True, slots=True)
class RetrievalScope:
    source_entry_id: int | None = None
    category: str | None = None
```

范围生成规则：

1. 景点：使用对应KnowledgeEntry的 `source_entry_id` 精确过滤。
2. 路线：用RouteTemplate标题匹配官方“游览路线”知识条目，再按 `source_entry_id` 过滤。
3. 可安全映射的话题：按已有知识分类过滤。
4. `architecture`、`blessing`等跨分类话题不强制过滤，只保留上下文，避免误删正确证据。

话题到分类的安全映射：

```text
attractions -> 景点信息
history     -> 历史文化
routes      -> 游览路线
family      -> 游览路线
practical   -> 实用贴士
dining      -> 实用贴士
```

## 六、缓存键

不修改现有缓存表结构。新增稳定哈希键：

```text
sha256(normalized_query + mode + attraction_id + topic_key + route_id)
```

日志继续保存真实normalized query，不把哈希键写入游客可见记录。

知识同步当前已经全量清空QA缓存，因此本切片不额外增加knowledge_version字段。

## 七、上下文SSE事件

新增事件：

```text
event: context
data: {
  selection: {...服务端确认后的SelectionContext...},
  resolution_source: "query|selection|history|default",
  warnings: []
}
```

前端收到后更新interaction store并持久化，使文字实体覆盖结果能够反映到面包屑和下一轮请求。

## 八、预计文件改动

新增：

1. `backend/app/services/qa/guided_selector.py`
2. `backend/app/tests/test_guided_selector.py`

修改：

1. `backend/app/services/rag/base.py`
2. `backend/app/services/rag/vector_store.py`
3. `backend/app/services/rag/chroma_retriever.py`
4. `backend/app/services/rag/retriever.py`
5. `backend/app/repositories/knowledge.py`
6. `backend/app/repositories/quick_topic.py`
7. `backend/app/repositories/route.py`
8. `backend/app/services/qa/pipeline.py`
9. `backend/app/api/chat.py`
10. 相关后端测试fake接口
11. `frontend/src/stores/interaction.js`
12. `frontend/src/stores/chat.js`
13. `frontend/src/views/tourist/ChatView.vue`

## 九、风险与控制

### 风险1：过滤过严导致无结果

控制：只对精确景点/路线和可证明的一对一分类应用过滤；跨分类话题不强制过滤。

### 风险2：向量检索失败后SQL降级越过范围

控制：RetrievalScope同时传给Chroma和RepositoryBackedRAGService。

### 风险3：失效或伪造ID污染检索

控制：所有ID必须从数据库回查；无效字段被清理并返回warning。

### 风险4：同一句出现多个景点

控制：首版按最长标题/别名匹配；若同长度则使用文本中最先出现的实体。多实体比较问答后续单独扩展。

### 风险5：缓存串景点

控制：缓存键包含服务端解析后的完整选择身份。

## 十、验收标准

1. 有效选择可生成正确服务端上下文。
2. 无效景点、话题或路线ID不会进入检索范围。
3. “选择灵山大佛 + 提问五印坛城”解析为五印坛城。
4. Chroma query收到正确metadata where条件。
5. SQL fallback遵守同一source/category范围。
6. 相同问题在不同景点下生成不同缓存键。
7. SSE返回context事件。
8. 前端接收context并更新本地选择。
9. 新增专项测试通过，完整后端测试无退化。
10. 前端生产构建与compileall通过。

## 十一、分步审查

1. Resolver完成后运行实体冲突和无效ID专项测试。
2. RetrievalScope完成后运行Chroma/SQL筛选测试。
3. Pipeline和前端context完成后运行Pipeline测试与前端构建。
4. 最后运行完整后端回归和范围审查。

## 十二、实际完成结果

已完成：

1. 新增轻量 `GuidedSelectionResolver`。
2. 实现景点、启用话题和路线的数据库逐轮校验。
3. 实现“本轮文字实体 > 按钮选择 > 历史主体 > 默认”的优先级。
4. 新增类型安全的 `RetrievalScope`。
5. Chroma支持 `source_entry_id`/`category` metadata筛选。
6. SQL fallback遵守相同检索范围。
7. 路线选择优先绑定对应官方路线知识条目。
8. 新增选择感知的SHA-256缓存键，未修改缓存表结构。
9. Pipeline发送 `context` SSE事件并使用解析后的范围检索。
10. 前端接收服务端上下文，更新面包屑和localStorage。

未进入：

1. 未修改数据库Schema或依赖。
2. 未实现快捷追问、长期SessionContext和LLM指代消解。
3. 未修改Reranker模型、参数或执行策略。
4. 未实现FAQ L3。

## 十三、验证证据

```text
Resolver专项测试：5 passed
Chroma/SQL范围专项测试：7 passed
Pipeline组合专项测试：13 passed
完整后端回归：30 passed
前端生产构建：通过（1688 modules transformed）
compileall：通过
真实SSE冲突冒烟：灵山大佛按钮 + 五印坛城文字 -> attraction_id 16
真实Chroma筛选：source_entry_id 16 返回3个分块，全部属于16
```

## 十四、发现的既有风险

真实应用冒烟时，`SentenceTransformerEmbedder` 会先尝试访问 Hugging Face；当前网络受限后，系统按既有降级逻辑切换到SQL检索。该问题不是本切片引入，也未阻止context冲突解析；真实Chroma metadata过滤已通过直接读取现有D盘向量库验证。

若要确保离线启动时始终使用D盘Embedding模型，下一步需要单独审查并确认是否给Embedder增加 `local_files_only` 配置。按照项目规则，本轮不擅自改变模型加载策略。

## 十五、结论

游客主动选择现在已从“前端展示”升级为“服务端可信校验 + 冲突纠正 + 选择感知检索 + 缓存隔离”的真实闭环。本切片满足验收标准，可以停止等待下一步确认。
