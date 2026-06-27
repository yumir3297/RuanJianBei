# Reranker 阶段实施方案（待审查）

- 编写日期：2026-06-11
- 当前状态：方案已编写，尚未下载模型，尚未修改业务代码
- 审查对象：用户 / DeepSeek
- 对应阶段：真实 CrossEncoder Reranker + BM25 fallback

## 1. 编写目的

在已经跑通真实 Chroma 检索和 30 题检索评测的基础上，接入真实重排序层，将流程完善为：

```text
FAQ 未命中
  -> QueryRewriter
  -> BGE embedding
  -> Chroma Top-20
  -> CrossEncoder Reranker 20 -> 5
  -> 返回证据
```

本阶段只处理重排序，不接真实 LLM、ASR、TTS、Avatar，也不修改前端。

## 2. 当前基线

### 2.1 已完成能力

1. `BAAI/bge-small-zh-v1.5` 已缓存到 D 盘。
2. Chroma collection `scenic_knowledge_chunks` 已包含 66 个 chunk。
3. `VectorBackedRAGService` 已接入主问答链路。
4. FAQ 未命中后会进入真实 Chroma 检索。
5. Chroma 异常时会显式退回 `RepositoryBackedRAGService`。
6. `RetrievedDocument.content` 已保留完整 chunk 文本。
7. 当前候选数量由 `rag_candidate_k=20` 控制，最终返回数量为 Top-5。
8. `sentence-transformers`、`rank-bm25` 和 CPU 版 PyTorch 已安装在 D 盘虚拟环境。

### 2.2 30 题检索基线

```text
Recall@1 = 96.67%
Recall@5 = 100.00%
MRR = 98.33%
Chroma query P95 = 12.44ms
总检索 P95 = 78.15ms
```

唯一 Top-1 偏位题：

```text
问题：抱佛脚、摸天下第一掌等互动体现了景区的哪种特色体验？
Top-1：其他特色景点
Top-2：祈福文化的特色体验（期望）
```

### 2.3 当前缺口

1. `Reranker` 仍只保持原顺序并截断，不会按 query 重新评分。
2. `BAAI/bge-reranker-base` 当前尚未下载到 D 盘缓存。
3. 主链路没有单独记录 Reranker 耗时和实际运行模式。
4. 现有检索评测脚本只评测 Chroma 原始 Top-5，没有进行重排前后对比。

## 3. 设计约束

本方案遵守以下既有要求：

1. 使用 `query + document.content` 做交叉编码，不使用截断后的 `snippet` 代替完整证据。
2. 模型、依赖和缓存全部位于 `D:\桌面\软件杯` 下。
3. CrossEncoder 模型只初始化一次，不在每次请求中重复加载。
4. CrossEncoder 不可用时必须显式标记 fallback，不能伪装为真实重排。
5. Reranker 失败不能让已成功的 Chroma 检索结果整体丢失。
6. 不改变 FAQ 优先、SSE 输出和 SQL fallback 的既有行为。
7. 不为提高评测分数修改测试问题、期望标题或原始知识数据。
8. 单阶段完成后停止，等待审查，不自动进入 LLM 阶段。

## 4. 拟采用的模块结构

### 4.1 保留稳定接口

继续使用：

```python
@dataclass(slots=True)
class RerankResult:
    document: RetrievedDocument
    score: float


class Reranker:
    def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 5,
    ) -> list[RerankResult]:
        ...
```

`VectorBackedRAGService`、旧仓储 RAG 和测试中的依赖注入方式保持不变。

### 4.2 新增 `CrossEncoderReranker`

拟新增：

```text
backend/app/services/rag/cross_encoder_reranker.py
```

职责：

1. 从 D 盘 HuggingFace 缓存加载 `BAAI/bge-reranker-base`。
2. 组成 `(query, document.content or document.snippet)` 输入对。
3. 批量执行 `CrossEncoder.predict()`。
4. 按模型分数降序排列并返回 Top-K。
5. 将模型名、批大小、最大长度作为构造参数，不在实现中写死运行参数。
6. 支持注入假模型，保证单元测试不依赖真实模型下载。

### 4.3 新增 `BM25Reranker`

拟新增：

```text
backend/app/services/rag/bm25_reranker.py
```

职责：

1. 在 CrossEncoder 初始化或推理失败时提供轻量排序。
2. 使用已经安装的 `rank-bm25`。
3. 不新增 `jieba` 依赖。
4. 中文文本建议使用“连续中文字符 + 字符二元组”，英文和数字使用普通词元。
5. 空 query、空 documents 和 `top_k <= 0` 均返回稳定结果，不抛无意义异常。

选择字符/二元组而不是 `jieba` 的原因：

1. 当前环境没有安装 `jieba`。
2. 可以避免未经确认增加新依赖。
3. 景区实体名较短，字符二元组能覆盖“灵山大佛”“五印坛城”等专名。
4. BM25 只是显式 fallback，不替代最终 CrossEncoder 方案。

### 4.4 新增可降级包装器

拟新增：

```text
backend/app/services/rag/resilient_reranker.py
```

运行优先级：

```text
CrossEncoder
  -> 失败时 BM25
  -> BM25 也失败时保留 Chroma 原顺序
```

包装器需要暴露：

```text
last_mode = cross_encoder | bm25_fallback | stable_order_fallback
```

每次降级均输出 warning，并保留原始异常日志。这样不会因为重排器异常而丢失可用的向量检索结果。

## 5. 主链路接入方案

### 5.1 缓存模型实例

在 `backend/app/api/chat.py` 增加缓存构建函数：

```text
get_cached_reranker(model_name, cache_dir, batch_size, max_length)
```

使用 `lru_cache`，保证：

1. 同一配置只加载一次 CrossEncoder。
2. 多次聊天请求复用模型。
3. 不把数据库 Session 放入缓存对象。
4. 初始化失败时构建 BM25 fallback，并记录当前模式。

### 5.2 修改注入点

`build_pipeline()` 中：

1. `VectorBackedRAGService` 注入真实可降级 Reranker。
2. `RepositoryBackedRAGService` 可继续使用轻量 Reranker，避免 SQL fallback 触发大型模型推理。
3. 不改变 `QAPipeline` 构造接口。
4. 不改变 `/api/chat/stream` 的请求和响应格式。

### 5.3 增加运行指标

在 `VectorBackedRAGService` 增加：

```text
last_rerank_ms
last_reranker_mode
```

日志需要包含：

```text
candidate_count
returned_count
reranker_mode
rerank_duration_ms
```

`RetrievedDocument.score` 继续代表当前最终排序分数，不在本阶段扩展前端响应结构。

## 6. 配置方案

拟在 `Settings` 和 `.env.example` 增加：

```text
RERANKER_BATCH_SIZE=8
RERANKER_MAX_LENGTH=512
```

继续使用现有配置：

```text
RERANKER_MODEL_NAME=BAAI/bge-reranker-base
RAG_CANDIDATE_K=20
RAG_TOP_K=5
MODEL_CACHE_DIR=../.cache/huggingface
```

所有路径通过 `Settings.model_cache_root` 解析，不直接写死绝对路径。

## 7. 模型下载与磁盘策略

当前检查结果：`bge-reranker-base` 尚未存在于 D 盘 HuggingFace 缓存。

审查确认后才执行首次下载，环境变量固定为：

```text
HF_HOME=D:\桌面\软件杯\.cache\huggingface
HUGGINGFACE_HUB_CACHE=D:\桌面\软件杯\.cache\huggingface\hub
TRANSFORMERS_CACHE=D:\桌面\软件杯\.cache\huggingface\transformers
TORCH_HOME=D:\桌面\软件杯\.cache\torch
```

下载失败、磁盘空间不足或模型加载异常时：

1. 立即停止该步骤并反馈。
2. 不擅自换模型。
3. 不擅自换镜像。
4. 不擅自改为在线 API。

## 8. 测试方案

### 8.1 单元测试

新增测试至少覆盖：

1. CrossEncoder 按假模型分数正确重排。
2. CrossEncoder 使用完整 `document.content`。
3. `content` 为空时才使用 `snippet`。
4. 空候选和非法 Top-K 的边界。
5. BM25 排序会随 query 改变。
6. CrossEncoder 推理异常时切换到 BM25。
7. BM25 异常时保留 Chroma 原始顺序。
8. `VectorBackedRAGService` 记录重排耗时和运行模式。
9. 原有 SQL fallback 测试继续通过。

真实模型不参与普通单元测试，避免测试依赖网络和大型模型。

### 8.2 真实模型 smoke test

使用现有 66 个 chunk 和真实模型验证：

1. 模型从 D 盘缓存加载。
2. 同一组候选在不同 query 下排序发生合理变化。
3. 返回结果包含真实 reranker score。
4. 连续两次构建 pipeline 时模型实例被复用。
5. `/api/chat/stream` 仍能返回 5 条真实来源。

### 8.3 回归测试

运行：

```text
backend/app/tests
eval/tests
compileall
```

不得破坏当前后端 `10 passed` 和评测指标测试 `3 passed` 的基线。

## 9. 评测方案

### 9.1 保留原始基线

不覆盖：

```text
eval/reports/retrieval_v0.json
```

它继续代表“无 Reranker 的 Chroma 原始排序”。

### 9.2 新增重排对比脚本

拟新增：

```text
eval/scripts/reranker_regression.py
eval/reports/reranker_v0.json
```

对同一批 30 题同时记录：

1. Chroma 原始 Top-5。
2. Chroma Top-20 经 CrossEncoder 后的 Top-5。
3. 重排前后 Recall@1、Recall@5、MRR。
4. 每题期望知识的原始排名和重排后排名。
5. embedding、Chroma、Reranker 和总耗时的平均值、P50、P95。
6. 当前实际模式是 CrossEncoder 还是 fallback。

### 9.3 验收门槛

硬门槛：

```text
重排后 Recall@5 >= 90%
重排后 Recall@5 不低于原始基线
MRR 不低于原始基线
不得出现未标记的 fallback
```

目标门槛：

```text
Recall@1 >= 96.67%
MRR >= 98.33%
Reranker 20 -> 5 的 P95 < 150ms
```

说明：当前基线已经很高，真实 Reranker 不保证一定把唯一偏位题提升到第一名。若 MRR 或延迟不达标，应保留真实结果并停止排查，不修改测试答案刷分，也不自行更换模型。

## 10. 预计修改文件

拟新增：

```text
backend/app/services/rag/cross_encoder_reranker.py
backend/app/services/rag/bm25_reranker.py
backend/app/services/rag/resilient_reranker.py
backend/app/tests/test_cross_encoder_reranker.py
backend/app/tests/test_bm25_reranker.py
backend/app/tests/test_resilient_reranker.py
eval/scripts/reranker_regression.py
eval/reports/reranker_v0.json
```

拟修改：

```text
backend/app/services/rag/reranker.py
backend/app/services/rag/chroma_retriever.py
backend/app/api/chat.py
backend/app/core/config.py
backend/.env.example
backend/app/tests/test_chroma_retriever.py
docs/2026-06-11-deepseek-review-adoption-and-execution.md
```

不修改：

```text
原始景区资料
data/processed 下的结构化数据
Chroma collection 内容
数据库模型与数据库数据
前端页面
LLM / ASR / TTS / Avatar 实现
```

## 11. 分步执行与逐步审查

审查通过后按以下顺序执行，每一步结束都先检查再进入下一步：

### Step 1：实现可测试的 Reranker 模块

1. CrossEncoder 实现。
2. BM25 fallback。
3. 可降级包装器。
4. 单元测试。

审查点：接口兼容、完整文本输入、异常降级、无新依赖。

### Step 2：接入主链路

1. 模型缓存构建。
2. `VectorBackedRAGService` 注入。
3. 耗时和模式记录。
4. 原有测试回归。

审查点：模型不重复加载、FAQ/SSE/SQL fallback 不受影响。

### Step 3：下载并验证真实模型

1. 下载到 D 盘缓存。
2. 离线重新加载验证。
3. 真实 20→5 smoke test。

审查点：路径、模型复用、真实 score、CPU 延迟。

### Step 4：30 题对比评测

1. 生成重排报告。
2. 对比原始基线。
3. 分析退化题与延迟。
4. 更新执行记录。

审查点：不覆盖基线、不刷测试集、不隐藏 fallback。

### Step 5：停止

本阶段完成后停止，等待用户审查；不自动开始真实 LLM。

## 12. 风险与处理原则

### 风险 1：CPU 延迟超过 150ms

处理：记录真实 P50/P95，检查批大小、最大长度和候选数量；不自行换模型。若仍超标，停止并由用户决定是否接受基线或调整方案。

### 风险 2：模型下载体积或网络异常

处理：停止并反馈实际错误，不改下载源、不换模型。

### 风险 3：高基线导致指标没有提升

处理：重点检查是否出现退化、排序是否真实受 query 影响，以及唯一偏位题是否合理；不以“必须提分”为理由修改测试集。

### 风险 4：内容重叠导致 CrossEncoder 仍无法区分

处理：保留证据和排名分析，后续可讨论 chunk 标题拼接、metadata 提示或知识去重，但这些不在本阶段擅自实施。

### 风险 5：Fallback 掩盖真实模型故障

处理：报告、日志和服务状态必须显示 `cross_encoder`、`bm25_fallback` 或 `stable_order_fallback`，验收时只有真实 CrossEncoder 模式可视为主目标完成。

## 13. 请求审查的重点

请重点确认：

1. 是否同意拆分为 CrossEncoder、BM25、Resilient 三个模块。
2. 是否同意 BM25 使用字符/二元组切分，不新增 `jieba`。
3. 是否同意运行时采用 CrossEncoder -> BM25 -> 原向量顺序的三级保护。
4. 是否同意保持 `RetrievedDocument.score` 为最终分数，不在本阶段扩展 API 字段。
5. 是否同意使用同一 30 题同时输出重排前后对比报告。
6. 当 CPU P95 超过 150ms 时，是否应停止并报告，而不是自动更换模型或减少候选数。

## 14. 当前停止点

截至本文档完成：

1. 没有修改后端业务代码。
2. 没有下载 `BAAI/bge-reranker-base`。
3. 没有修改 Chroma 索引和景区数据。
4. 等待用户或 DeepSeek 审查本文档后再正式编码。
