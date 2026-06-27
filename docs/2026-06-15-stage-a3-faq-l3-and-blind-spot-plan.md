# 阶段 A3：FAQ L3 与知识盲区闭环实施方案

- 日期：2026-06-15
- 状态：A3.1 FAQ L3 与 A3.2 知识盲区后端闭环均已完成
- 主线依据：`设计文档/10-最终总体设计与开发主线.md`

## 阶段拆分

### A3.1 FAQ L3 语义匹配

本子阶段不修改数据库 Schema，可以直接实施：

1. 复用 D 盘 `BAAI/bge-small-zh-v1.5`，不下载或更换模型。
2. 启动或首次聊天时，对当前 88 条 FAQ 的 202 个别名一次性批量生成归一化向量。
3. 请求时只生成一次 query embedding，并与内存中的别名向量计算余弦相似度。
4. 继续保持 `L1 exact -> L2 fuzzy -> L3 semantic -> cache/RAG` 顺序。
5. FAQ 数据刷新后使语义索引失效；若运行时已有 Embedder，则同步重建，否则在下一次聊天时重建。
6. 模型或语义索引不可用时显式降级到现有 L1/L2 + RAG，不阻塞聊天。

### A3.2 知识盲区闭环

该子阶段需要新增数据库表，暂不执行，先提交明确方案：

1. 新增 `knowledge_blind_spots` 表。
2. RAG 无证据时按规范化问题聚合次数，并保留有限原始样本。
3. 管理端按频次、状态、最近时间查看盲区。
4. 管理员填写答案后创建或更新 FAQ，并刷新 L1/L2/L3 内存索引。
5. 已解决记录保留，不物理删除。

## FAQ L3 模块设计

新增独立 `FAQSemanticIndex`，职责仅包括：

1. 批量构建别名向量。
2. 对 query 返回最高分 FAQ、相似度和命中别名。
3. 维护模型名、条目数、别名数、构建耗时等可观测状态。

`FAQMatcher` 继续负责 L1/L2/L3 顺序，不把 Embedding 实现细节写入 Pipeline。

## 阈值评测

新增独立测试集，至少包含：

1. 不与现有别名完全相同的景点介绍、位置、参数和开放信息正例。
2. 游览时间、概况等综合 FAQ 正例。
3. 厕所、停车、实时天气、票价、交通等当前资料未覆盖的负例。
4. 普通闲聊和与景区无关问题负例。

阈值从候选区间扫描，验收优先级：

1. 负例误命中率为 0。
2. 正例 FAQ ID 准确率不低于 80%。
3. L1/L2 现有测试不退化。
4. 单次 L3 查询 P95 记录真实值，不宣称未实测性能。

## A3.1 预计修改

1. 新增 `backend/app/services/qa/faq_semantic_index.py`。
2. 修改 `faq_matcher.py` 和 `runtime.py`。
3. 修改聊天 Pipeline 构建，使 FAQ 与 RAG 复用同一缓存 Embedder。
4. 新增语义评测测试集、阈值扫描脚本与报告。
5. 增加索引构建、命中、负例拒绝、刷新和降级测试。

## A3.1 明确不改

1. 不新增依赖、模型或数据库字段。
2. 不在请求中逐条计算 202 个 alias embedding。
3. 不把语义相似描述成绝对正确；低于阈值继续进入 RAG。
4. 不开发 LLM 并发、Chroma 预热、多模态或语音功能。

## A3.2 拟议 Schema

```text
knowledge_blind_spots
- id: integer primary key
- normalized_query: varchar(500), unique, indexed
- raw_query_samples_json: text, default []
- hit_count: integer, default 1
- status: varchar(20), default open
- category: varchar(50), default unknown
- resolution_type: varchar(20), nullable
- resolved_faq_id: varchar(120), nullable
- resolved_knowledge_id: integer, nullable
- first_seen_at: datetime
- last_seen_at: datetime
- resolved_at: datetime, nullable
```

相比早期文档的 `filled + suggested_answer`，本方案改为状态和解决关联，避免在盲区表中复制最终 FAQ 事实文本。

## A3.2 拟议 API

1. `GET /api/admin/blind-spots?status=open&limit=50`
2. `POST /api/admin/blind-spots/{id}/resolve-with-faq`
3. `POST /api/admin/blind-spots/{id}/link-knowledge`

第一版只建议实现 `resolve-with-faq`；长知识补充和 Chroma 重建继续使用已有知识管理/索引端点，不在一个请求中隐式重建大型索引。

## 停止边界

完成 A3.1 后停止。A3.2 涉及新增表、ORM、API 和管理端数据结构，必须由用户确认上述 Schema 与 API 后才能开始编码。

## 首轮实施结果（历史失败记录）

### 已完成

1. 新增批量内存 `FAQSemanticIndex`，支持一次构建别名向量、每次查询只编码一次。
2. `FAQMatcher` 已具备可选语义索引能力，但尚未接入聊天主链路。
3. 新增 22 条语义正例和 12 条知识盲区负例。
4. 新增 `eval/scripts/faq_semantic_regression.py`，扫描阈值 `0.60–0.95`。
5. 真实评测报告：`eval/reports/faq_semantic_v1.json`。
6. 202 个别名构建耗时 `381.63ms`；单次 query embedding + 内存匹配 P50 `26.90ms`、P95 `34.83ms`。
7. FAQ 专项测试通过，后端完整回归 `43 passed`，评测测试 `3 passed`，编译通过。

### 未通过原因

没有阈值同时满足“正例准确率不低于 80%”与“负例零误命中”：

1. `threshold=0.72`：负例拒绝率 100%，正例正确 `17/22 = 77.27%`，另有 4 条高分错误匹配。
2. `threshold=0.80`：负例拒绝率 100%，正例正确 `12/22 = 54.55%`，仍有 1 条错误匹配。
3. `threshold=0.85`：负例拒绝率 100%，正例正确仅 `6/22 = 27.27%`，仍有 1 条错误匹配。

主要错误不是跨景点，而是同一景点下“介绍、位置、参数、开放信息”别名高度相似，纯向量 Top-1 无法稳定区分意图。例如：

1. “晚上还能参观灵山大照壁吗”错误匹配到“大照壁有什么亮点”。
2. “五智门大概有多高多宽”错误匹配到“五智门位置”。
3. “祥符禅寺有哪些值得看的地方”错误匹配到“祥符禅寺在哪里”。
4. “鹿鸣谷什么时候可以进去游览”错误匹配到“鹿鸣谷在哪里”。

### 建议路线

建议将 L3 从“全库向量阈值”改为“实体 + 意图双闸门 + 语义排序”：

1. 先使用已验证的景点标题/别名提取实体。
2. 使用受控关键词识别 `介绍 / 位置 / 参数 / 开放信息` 意图。
3. 只在同实体、同意图候选内执行语义相似度。
4. 未识别实体或意图时保持保守阈值，低置信继续进入 RAG。
5. 重新运行同一 34 条评测，仍要求正例准确率至少 80%、负例零误命中。

该路线不新增依赖或数据库，但改变 FAQ L3 判定方法。按照协作规则，需要用户确认后再继续。

### 首轮停止点

1. FAQ 语义索引代码存在但未被聊天 Pipeline 启用，线上仍为 L1/L2 -> RAG。
2. 不采用未通过评测的 `0.72`、`0.80` 或 `0.85` 阈值。
3. 不开始知识盲区建表，继续等待 Schema/API 确认。

## 二次实施结果（最终）

用户批准“实体 + 意图双门控 + 语义排序”后，A3.1 已完成：

1. 新增独立 `FAQSemanticGate`，只允许可信景点实体和受控意图进入语义候选集。
2. 保留 `L1 exact -> L2 fuzzy -> L3 semantic -> cache/RAG` 顺序。
3. FAQ 与向量 RAG 共享缓存 Embedder，模型不可用时退回 L1/L2 + RAG。
4. 运行阈值由 v2 评测确定为 `0.60`，并通过配置项注入。
5. 最终测试集为 21 条有证据正例和 13 条盲区负例。
6. 正例 FAQ ID 准确率 100%，错误命中 0，负例拒绝率 100%。
7. 202 个别名构建耗时 `274.87ms`；查询 P50 `10.92ms`、P95 `13.51ms`。
8. 报告：`eval/reports/faq_semantic_v2.json`。
9. 后端完整回归 `46 passed`，评测测试 `3 passed`，真实 Pipeline 使用向量 RAG 且语义索引成功建立。

完整实施记录：`docs/2026-06-15-stage-a3-faq-l3-implementation-report.md`。

## A3.1 完成时停止点（历史）

A3.1 接入聊天主链路并通过评测后曾在此停止；当时 A3.2 尚未开始，等待用户确认 Schema/API。该确认现已完成，最终结果见下节。

## A3.2 最终实施结果

用户批准后，知识盲区后端最小闭环已完成：

1. RAG 无证据问题按规范化查询聚合，最多保存 5 个原始样本。
2. 新增 `GET /api/admin/blind-spots` 和 `POST /api/admin/blind-spots/{id}/resolve-with-faq`。
3. 管理员可创建或更新 FAQ，必须提交非空来源。
4. 解决后保留审计记录并刷新 FAQ L1/L2/L3 索引。
5. 官方资料同步会保护已解决盲区引用的人工 FAQ。
6. 后端完整回归 `52 passed`，评测测试 `3 passed`，真实数据库建表和接口验证通过。

完整实施记录：`docs/2026-06-15-stage-a3-blind-spot-implementation-report.md`。

管理前端页面留到阶段 C；`link-knowledge` 未实现，不在解决请求中隐式重建 Chroma。
