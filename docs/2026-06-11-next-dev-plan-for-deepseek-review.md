# 2026-06-11 下一步开发计划（提交 DeepSeek 审查版）

## 1. 文档目的

本文用于在正式继续编码前，向 DeepSeek 或其他 AI 审查者说明：

1. 当前项目已经开发到哪里。
2. 下一步准备开发什么。
3. 每一步采用什么方法。
4. 哪些地方需要用户确认后才能继续。
5. 数字人相关能力在最终作品路线中的位置。

本文件只描述代码开发计划，不包含 PPT、演示稿、答辩稿、UI 美化文案等非代码任务。

## 2. 最终作品目标

最终作品是一个面向景区的智能导览问答系统。

核心能力包括：

1. 基于官方景区资料的知识问答。
2. FAQ 快速命中。
3. 景区路线推荐。
4. 真实 RAG 检索增强生成。
5. 真实 Reranker 精排。
6. 至少一个真实多模态大模型接入。
7. 后续接入 ASR、TTS 与数字人 Avatar，形成语音交互和数字人讲解体验。

阶段优先级判断：

1. 当前最重要的是先把问答主链路做真实、做稳定。
2. 语音和数字人如果过早接入，只会把占位答案包装得更好看，不能提升核心准确率。
3. 因此近期开发重点仍是 `真实 RAG -> 真实 Reranker -> 真实 LLM -> 评测闭环`。
4. 数字人相关能力需要明确保留在最终路线图中，但不抢占当前 RAG 主链路优先级。

## 3. 当前开发进度

### 3.1 已完成

1. 前后端基础骨架已建立。
2. 后端 FastAPI 基础接口可运行。
3. 前端已有连接后端的最小闭环。
4. 比赛提供的景区资料已整理进入项目数据目录。
5. 原始资料已提取为结构化 processed 数据。
6. 已形成并接入以下数据：
   - `knowledge_entries.json`
   - `guide_sections.json`
   - `faq_entries.json`
   - `route_recommendations.json`
   - `visitor_behavior_summary.json`
7. 后端已支持 `POST /api/admin/sync-processed-data` 同步真实处理数据。
8. FAQ 已改为 `DB -> 内存索引`。
9. 路线推荐已由 DB 驱动。
10. 行为摘要已接入后台概览。
11. 已新增 `KnowledgeChunk` 数据模型、仓储和切块器。
12. 数据同步时已经能生成知识切块。
13. 已新增 RAG 索引构建基础设施：
    - `BaseEmbedder`
    - `SentenceTransformerEmbedder`
    - `BaseVectorStore`
    - `ChromaVectorStore`
    - `RAGIndexBuilder`
14. 已新增后台接口 `POST /api/admin/build-rag-index`。
15. 当前后端测试已覆盖基础同步、FAQ、推荐、RAG index builder。

### 3.2 当前准确位置

项目当前停在：

**真实 RAG 依赖尚未安装，Chroma 向量索引尚未生成，主问答链路还没有从 SQL LIKE 占位检索切换到真实向量检索。**

当前依赖状态：

1. `chromadb` 未安装。
2. `sentence-transformers` 未安装。
3. `torch` 未安装。
4. `rank_bm25` 未安装。

当前 `POST /api/admin/build-rag-index` 的预期行为：

1. 如果依赖未安装，返回 `503`。
2. 错误码为 `rag_dependency_missing`。
3. 不会静默降级为假向量检索。

## 4. 下一步开发总路线

下一步建议拆成 6 个小阶段：

1. 安装并固定真实 RAG 依赖。
2. 构建真实 Chroma 向量索引。
3. 实现 `VectorBackedRAGService`，替换 SQL LIKE 占位检索。
4. 实现真实 `CrossEncoderReranker`，替换当前只截断 Top-K 的 stub。
5. 接入真实多模态 LLM，替换占位生成。
6. 建立 100 题评测闭环和延迟评测。

数字人相关能力放入后续阶段：

1. ASR 语音识别。
2. TTS 语音合成。
3. 数字人 Avatar 播报。
4. 前端语音交互与数字人展示。

## 5. 近期开发阶段拆分与方法

### Phase A：安装真实 RAG 依赖

目标：

1. 让当前 `SentenceTransformerEmbedder` 和 `ChromaVectorStore` 可以真实运行。
2. 为后续向量检索、重排、评测提供运行环境。

准备安装的依赖：

```text
chromadb
sentence-transformers
rank-bm25
```

说明：

1. `sentence-transformers` 会间接依赖 `torch`。
2. 如果安装速度慢或模型下载失败，应停止并向用户说明，不擅自切换方案。
3. 若本机资源不足，可先使用 `BAAI/bge-small-zh-v1.5`，不直接上 `bge-large`。

方法：

1. 更新 `backend/requirements.txt`。
2. 在虚拟环境中安装依赖。
3. 执行依赖可用性检查。
4. 不在依赖未确认前改主链路。

验收：

1. `import chromadb` 成功。
2. `import sentence_transformers` 成功。
3. `import rank_bm25` 成功。
4. 后端原有测试仍通过。

需要用户确认：

1. 是否允许安装上述依赖。
2. 是否允许首次运行时下载 embedding / reranker 模型。

### Phase B：构建真实 Chroma 向量索引

目标：

1. 用已生成的 `KnowledgeChunk` 构建真实向量库。
2. 确认 Chroma 持久化目录可用。

方法：

1. 先调用 `POST /api/admin/sync-processed-data`，确保数据库切块最新。
2. 再调用 `POST /api/admin/build-rag-index`。
3. 使用 `BAAI/bge-small-zh-v1.5` 生成 chunk embedding。
4. 将向量、chunk 文本、metadata 写入 Chroma collection。
5. Chroma 默认持久化目录使用配置项 `chroma_persist_dir`。

验收：

1. 后台接口返回 `indexed_chunks = 66` 或与当前 chunk 总数一致。
2. Chroma collection 名称为 `scenic_knowledge_chunks`。
3. 每条向量记录包含：
   - `chunk_id`
   - `title`
   - `category`
   - `source`
   - `source_entry_id`
   - `chunk_index`
4. 重复构建索引不会产生重复脏数据，而是替换 collection。

风险：

1. 首次下载模型可能较慢。
2. Chroma 版本变化可能影响 API 行为。
3. Windows 环境下部分依赖可能安装较慢。

### Phase C：实现 VectorBackedRAGService

目标：

将当前 `RepositoryBackedRAGService` 的 SQL LIKE 占位检索替换为真实向量检索。

当前问题：

1. 现有 RAG 检索只是在数据库里做关键字搜索。
2. 当前 `Reranker` 只截断结果，并不真正重排。
3. FAQ 未命中后仍无法进入真正 RAG 链路。

方法：

1. 新增 `VectorBackedRAGService`。
2. 复用现有 `QueryRewriter` 做查询规范化。
3. 使用 `SentenceTransformerEmbedder` 对 query 做 embedding。
4. 使用 `ChromaVectorStore.query` 检索候选 chunk。
5. 将候选 chunk 转换为 `RetrievedDocument`。
6. 暂时保留现有 `Reranker` 接口，后续 Phase D 替换其实现。
7. 通过配置或依赖注入切换 RAG service，避免硬编码。

建议检索参数：

1. Chroma candidate top-k：`20`
2. 最终返回 top-k：`5`
3. chunk 文本摘要长度：先保留 `content` 前 200 到 300 字，后续根据 prompt 调整。

验收：

1. FAQ 未命中后进入 `VectorBackedRAGService`。
2. 返回结果来自 Chroma，而不是 SQL LIKE。
3. 返回结果包含证据 metadata。
4. 后端测试新增向量检索服务测试。
5. 原 FAQ 精确匹配速度不受影响。

### Phase D：实现真实 CrossEncoderReranker

目标：

替换当前只做截断的 Reranker stub，使排序真实受 query 影响。

方法：

1. 保留当前 `Reranker` 对外接口。
2. 新增或替换为 `CrossEncoderReranker`。
3. 默认模型使用 `BAAI/bge-reranker-base`。
4. 输入为 `(query, document_text)` pairs。
5. 输出为按 reranker score 排序后的 `RerankResult`。
6. 若模型依赖缺失，应抛出明确错误，不静默 fallback。

短期 fallback：

1. 可保留当前 stub 作为 dev fallback。
2. fallback 必须在日志或接口状态中明确标记。
3. fallback 不能作为最终交付状态。

验收：

1. 同一批候选文档，对不同 query 的排序不同。
2. Reranker 输出包含真实 score。
3. Reranker 延迟单次目标 `< 150ms`，若本机达不到，记录基线。
4. 测试覆盖排序受 query 影响。

### Phase E：接入真实多模态 LLM

目标：

替换当前占位生成，让问答接口能基于检索证据输出真实模型回答，并满足“至少一个多模态大模型”的要求。

候选方案：

1. 推荐：`Qwen-VL-Plus`
2. 备选：`DeepSeek-VL2`

方法：

1. 保留现有 OpenAI-compatible 适配层思路。
2. 增加模型 provider 配置。
3. Prompt 强制要求只基于检索证据回答。
4. 证据不足时明确说明资料不足。
5. 保持 SSE 流式输出接口不变。
6. 暂不做图片上传和图像问答 UI，先确保模型本身是多模态能力模型。

验收：

1. FAQ 未命中后，系统能经过 RAG 证据生成真实回答。
2. 回答内容能引用或贴合检索证据。
3. 证据不足时不编造。
4. SSE 输出仍可被前端消费。
5. 模型配置项不写死在代码中。

需要用户确认：

1. 最终使用哪个模型供应商。
2. API key 和 base URL 如何配置。
3. 是否允许在本轮只使用文本输入能力，但选用多模态模型。

### Phase F：建立 100 题评测闭环

目标：

让后续优化有客观基线，而不是凭感觉判断效果。

方法：

1. 新建评测数据文件。
2. 先构建 100 题：
   - FAQ 40 题
   - 知识问答 40 题
   - 路线推荐 20 题
3. 每题包含：
   - `id`
   - `category`
   - `query`
   - `expected_answer`
   - `must_contain`
   - `source_doc`
4. 新增准确率评测脚本。
5. 新增延迟评测脚本。
6. 输出评测报告 JSON 或 Markdown。

验收：

1. 能一键跑完整评测。
2. 能统计 FAQ 命中率。
3. 能统计知识问答 must_contain 命中率。
4. 能统计推荐结果是否命中目标路线。
5. 能输出 FAQ、RAG、Reranker、LLM 首 token、全链路耗时。

## 6. 后续数字人阶段规划

数字人相关能力不应消失在任务列表中，但建议排在主问答链路稳定之后。

### Phase G：ASR 语音识别

目标：

让用户可以语音提问。

方法：

1. 前端录音。
2. 后端接收音频。
3. 调用 ASR 服务转文本。
4. 文本进入现有问答链路。

验收：

1. 语音能转成文本。
2. 文本能进入 FAQ / RAG / LLM 主链路。
3. ASR 错误时前端有明确提示。

### Phase H：TTS 语音合成

目标：

让系统回答可以被语音播报。

方法：

1. 后端将最终文本回答传入 TTS。
2. 返回音频 URL 或音频流。
3. 前端播放音频。
4. 保留文本显示。

验收：

1. 文本回答可以生成语音。
2. 音频能在前端播放。
3. 总响应延迟尽量控制在比赛要求范围内。

### Phase I：数字人 Avatar

目标：

让导览回答由数字人形象进行讲解，形成最终展示效果。

方法：

1. 选择数字人渲染方案。
2. 将 TTS 音频或文本驱动 Avatar。
3. 前端展示数字人区域。
4. 保持问答、路线、证据等信息同步展示。

验收：

1. 数字人能播报回答。
2. 播报内容来自真实问答链路。
3. 不影响基础文本问答使用。
4. 网络或数字人服务不可用时，可以回退到文本和音频。

## 7. 开发审查规则

后续每写完一个小阶段，都要进行一次审查。

审查内容包括：

1. 是否符合最初文档要求。
2. 是否只做了代码创作范围内的任务。
3. 是否有未确认的依赖、模型下载或 API 配置。
4. 是否没有把数据写死在代码里。
5. 是否没有破坏现有 FAQ 优先路径。
6. 是否保留了模块性、可添加性、可阅读性。
7. 是否有测试或可复现实验结果。
8. 是否更新阶段总结文档，方便继续交叉审查。

## 8. 近期最小可执行顺序

如果 DeepSeek 审查通过，建议下一步按以下顺序执行：

1. 用户确认是否允许安装真实 RAG 依赖。
2. 更新 `backend/requirements.txt`。
3. 安装 `chromadb`、`sentence-transformers`、`rank-bm25`。
4. 运行后端测试，确认原功能未破坏。
5. 调用数据同步接口，确保 chunk 最新。
6. 调用索引构建接口，生成真实 Chroma 索引。
7. 写 `VectorBackedRAGService`。
8. 写对应测试并审查。
9. 写 `CrossEncoderReranker`。
10. 写对应测试并审查。

## 9. 给 DeepSeek 的重点审查问题

请重点检查以下问题：

1. 当前是否应该先安装真实 RAG 依赖，而不是先写 LLM 或数字人。
2. `BAAI/bge-small-zh-v1.5` 作为开发期 embedding 模型是否合适。
3. `BAAI/bge-reranker-base` 作为首版 reranker 是否合适。
4. Chroma 索引构建后再切换主问答链路的顺序是否稳妥。
5. 数字人阶段排在真实问答链路之后是否符合比赛目标。
6. 是否需要在当前阶段提前预留数字人接口字段。
7. 评测闭环是否应该在 LLM 接入前先做一版，还是等真实 LLM 接入后再做。
8. 当前计划是否存在范围过大、依赖过重或验收标准不清的问题。

## 10. 结论

下一步开发不应直接跳到数字人，也不应直接写前端展示。

更稳妥的路线是：

**先把真实 RAG 索引跑起来，再把问答链路切到向量检索，然后接真实 Reranker，再接真实多模态 LLM，最后进入评测闭环；数字人作为最终作品展示能力，在主问答链路稳定后接入。**

这条路线能同时满足：

1. 比赛对智能问答准确率的要求。
2. 比赛对多模态模型能力的要求。
3. 后续数字人展示的基础输入质量要求。
4. 当前项目已有架构的可维护性要求。
