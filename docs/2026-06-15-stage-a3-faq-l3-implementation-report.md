# 阶段 A3.1 FAQ L3 实施报告

- 日期：2026-06-15
- 状态：已完成并通过评测
- 主线依据：`设计文档/10-最终总体设计与开发主线.md`
- 本轮边界：只完成 FAQ L3，不修改数据库 Schema、公共 API、依赖或模型供应商

## 实现内容

1. 新增批量内存 `FAQSemanticIndex`，启动或首次聊天时一次性编码 88 条 FAQ 的 202 个别名，请求内只编码一次 query。
2. 新增 `FAQSemanticGate`，先识别可信景点实体和受控意图，再只在同实体、同意图候选内执行余弦匹配。
3. 保持主链路顺序 `L1 exact -> L2 fuzzy -> L3 semantic -> cache/RAG`。
4. FAQ 与向量 RAG 共享同一个缓存 `SentenceTransformerEmbedder`，不重复加载模型。
5. FAQ 数据刷新时同步重建门控映射和已有语义索引。
6. 本地模型或语义索引初始化失败时，显式降级到原有 L1/L2 + RAG，不阻塞聊天。
7. 新增配置 `FAQ_SEMANTIC_THRESHOLD=0.60`，阈值不写死在匹配模块中。

## 评测过程

第一版全库纯向量 Top-1 未通过：同一景点的介绍、位置、参数和开放信息容易互相误判。该失败结果保留在：

- `eval/reports/faq_semantic_v1.json`

经用户批准后改为“实体 + 意图双门控 + 语义排序”。评测集最终包含 21 条有证据正例和 13 条知识盲区负例。原“鹿鸣谷什么时候可以进去游览”被核对为负例，因为资料中的 `faq_spot_086` 实际只提供景点参数，不包含开放时间。

最终报告：

- `eval/reports/faq_semantic_v2.json`

最终指标：

```text
threshold = 0.60
正例 FAQ ID 准确率 = 21/21 = 100%
正例错误命中 = 0
负例拒绝率 = 13/13 = 100%
索引条目数 = 88
索引别名数 = 202
索引构建耗时 = 274.87ms（本次评测）
查询 P50 = 10.92ms
查询 P95 = 13.51ms
```

阈值 0.60 只在实体和意图均通过门控后生效，不是面对全库的裸低阈值。最低正例分数为 0.6072，对应“灵山大照壁 + 参数”唯一候选；所有盲区负例均在语义检索前被拒绝。

## 运行时验证

真实 `build_pipeline` 初始化结果：

```text
pipeline = QAPipeline
rag_service = VectorBackedRAGService
FAQ entry_count = 88
FAQ exact_index_count = 202
FAQ semantic_alias_count = 202
FAQ semantic_threshold = 0.60
FAQ semantic_build_ms = 261.82ms
```

## 自动化检查

1. FAQ 门控、语义索引、刷新和原行为专项测试：`8 passed`。
2. 后端完整回归：`46 passed`。
3. 评测工具测试：`3 passed`。
4. 真实 D 盘本地 Embedding、Reranker 和向量 RAG 初始化成功。

## 分段审查结论

1. 模块性：实体/意图门控、向量索引、FAQ 编排和 Pipeline 构建职责分离。
2. 可添加性：新增分类可扩展门控映射；阈值可通过环境变量调整。
3. 可阅读性：未将向量计算或门控规则堆入 `pipeline.py`。
4. 准确性：单阈值失败结果未上线，只有通过双门控评测的方案接入主链路。
5. 降级性：模型不可用时保留 L1/L2 和数据库 RAG fallback。
6. 范围控制：未实现知识盲区表、管理 API 或前端页面。

## 当前停止点

A3.1 已完成。下一步 A3.2 需要新增 `knowledge_blind_spots` 表和管理 API，必须先由用户单独确认 `docs/2026-06-15-stage-a3-faq-l3-and-blind-spot-plan.md` 中的 Schema/API 后再编码。
