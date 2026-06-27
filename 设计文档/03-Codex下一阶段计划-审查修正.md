# Codex 下一阶段计划 — 审查修正确认

> 本文档是对 Codex `NEXT_PHASE_DEVELOPMENT_REPORT.md` 的审查结果。**方向正确，但 5 处关键缺失必须修正后才能动工。**

---

## 一、准入条件

| 检查项 | 结果 | 
|--------|:--:|
| 计划方向（RAG + LLM + 评测） | ✅ 正确 |
| 执行顺序（RAG → LLM → Eval → ASR/TTS → Avatar） | ✅ 正确 |
| 与设计文档一致 | ⚠️ 部分缺失 |
| 赛题硬指标覆盖 | ❌ 缺延迟预算分析 |
| 声称的"已完成"属实 | ✅ 已验证代码 |
| **整体** | **⚠️ 修正后可执行** |

---

## 二、当前代码状态（已验证）

对比 Codex 报告中 2.1 节的声明：

| 声明 | 验证结果 |
|------|:--:|
| metadata_json 列已加 | ✅ `models/knowledge.py` 第20行 |
| FAQ 改为 DB→内存加载 | ✅ `runtime.py` 已实现 `reload_runtime_faq_matcher` |
| 推荐引擎 DB 驱动 | ✅ `engine.py` 已按兴趣规则匹配3条路线 |
| 路线推荐返回真实路线 | ✅ 含 route_plan / guide_points / experiences |
| 数据同步接口可用 | ⚠️ 未验证（本轮不涉及，不影响） |

**当前真正的"占位"清单（与报告 2.2 节一致）**：

| 模块 | 当前实现 | 占位程度 |
|------|---------|---------|
| RAG 检索 | `RepositoryBackedRAGService`：SQL LIKE + 词频打分 | 🔴 完全占位 |
| Reranker | `Reranker.rerank()`：仅截断 Top-K，不做任何真实排序 | 🔴 完全占位 |
| LLM | `OpenAICompatibleLLMService`：返回硬编码占位文本 | 🔴 完全占位 |
| ASR | stub | 🔴 完全占位 |
| TTS | stub | 🔴 完全占位 |
| Avatar | stub | 🔴 完全占位 |

---

## 三、计划审查——5 处关键缺失

### 🔴 缺失 1：Reranker 是假货，计划却当"可连接"

**现状**：

```python
# backend/app/services/rag/reranker.py (当前代码)
class Reranker:
    def rerank(self, query, documents, top_k=5):
        del query          # ← query 被丢弃，完全没参与排序
        trimmed = documents[:top_k]   # ← 只截取前5个，不做任何重排
        return [RerankResult(document=doc, score=doc.score or 0.0) for doc in trimmed]
```

**Codex 计划说的是**：

> "接入现有 Reranker 模块接口，如果不引新依赖，则先实现轻量排序增强"

**问题**：这个 Reranker **本身就是一个假的**——它把 query 直接丢弃，不做任何交叉编码。ChromaDB 检索能力再强，经过这个"假 Reranker"就等于没做重排，Top-5 的精度不会有任何提升。设计文档明确要求 `bge-reranker-base`（Cross-Encoder），这是 90% 准确率的关键环节。

**修正**：真实 RAG 接入时**必须同时实现真实 Reranker**。方案：

```python
# 方案 A（推荐）：引入 sentence-transformers，加载 bge-reranker-base
from sentence_transformers import CrossEncoder

class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query, documents, top_k=5):
        pairs = [(query, doc.content) for doc in documents]
        scores = self.model.predict(pairs)
        # 按分数降序重排
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return [RerankResult(document=doc, score=float(score)) for doc, score in ranked[:top_k]]
```

```python
# 方案 B（备选，不引新依赖）：BM25 重排
from rank_bm25 import BM25Okapi

class BM25Reranker(Reranker):
    def rerank(self, query, documents, top_k=5):
        corpus = [doc.content for doc in documents]
        bm25 = BM25Okapi([self._tokenize(d) for d in corpus])
        scores = bm25.get_scores(self._tokenize(query))
        # ...
```

**方案 A 是唯一能达到 90% 准确率的路径。** B 方案不如 A，但好歹比当前"假 Reranker"强。

---

### 🔴 缺失 2：没有 Embedding 模型选型

**问题**：ChromaDB 需要 embedding 模型把文本转成向量。Codex 计划里提了 ChromaDB，但没提用哪个 embedding。这直接影响检索精度。

**修正**：必须明确——

| 选项 | 模型 | 维度 | 大小 | 推荐场景 |
|------|------|------|------|---------|
| 轻量 | `BAAI/bge-small-zh-v1.5` | 512 | ~95MB | 开发调试、低配机器 |
| 标准（推荐） | `BAAI/bge-large-zh-v1.5` | 1024 | ~1.3GB | 正式运行、追求精度 |

建议首版用 small（开发快），评测阶段切 large（冲 90%）。两版共享同一个 `BaseEmbedder` 接口，切换一行配置。

---

### 🔴 缺失 3：完全没有延迟预算

**问题**：计划里搭建 RAG + LLM，但**从未量化每一步的延迟**。赛题要求 < 5 秒全链路，你必须在设计阶段就把时间分好。

**当前代码已有延迟记录**（`pipeline.py` 第 126 行记录 `latency_ms`），但只记录不约束。

**修正**：Phase 1 启动前必须先定延迟预算：

| 阶段 | 预算 | 说明 |
|------|------|------|
| Query 改写 | < 10ms | 纯字符串 + 别名映射 |
| FAQ 精确匹配 | < 5ms | hash 查表，已验证 |
| FAQ 模糊匹配 | < 20ms | SequenceMatcher |
| **RAG 检索（新）** | **< 300ms** | embedding + ChromaDB 查询 |
| **Reranker（新）** | **< 150ms** | Cross-Encoder 单次推理 |
| **LLM 首 token（新）** | **< 2,000ms** | 流式生成，首字即开始返回 |
| TTS（将来） | < 500ms/句 | 句级流式合成 |
| **总计（当前轮）** | **< 2.5s** | FAQ 路径 < 30ms；RAG 路径 < 2.5s |
| **总计（全链路）** | **< 5s** | FAQ 路径 < 600ms；RAG 路径 < 5s |

**关键**：`LLM 首 token < 2000ms` 这个预算决定了不能用太大的模型。7B 模型首 token 约 500-800ms，13B 模型约 1-1.5s。超过 2s 的首 token 延迟就意味着 < 5s 全链路很危险。

---

### 🔴 缺失 4：多模态大模型要求未兑现

**赛题原文**："需明确使用至少1个多模态大模型作为核心AI能力支撑"

**Codex 计划**："接入真实模型配置" — 没指定具体模型，没提多模态。

**修正**：可选的真实多模态模型（含视觉理解能力）：

| 模型 | 提供商 | 多模态能力 | 首 token 延迟 | 推荐度 |
|------|--------|-----------|--------------|:--:|
| **Qwen-VL-Plus / Max** | 阿里通义千问 | 图文理解 | ~800ms | ⭐⭐⭐ |
| **DeepSeek-VL2** | DeepSeek | 图文理解 | ~800ms | ⭐⭐⭐ |
| **Step-1V** | 阶跃星辰 | 图文理解 | ~800ms | ⭐⭐ |
| GLM-4V | 智谱 | 图文理解 | ~1s | ⭐⭐ |

**建议首版选 Qwen-VL-Plus**：国产、API 稳定、OpenAI 兼容接口（当前适配层无需改动）、延迟可控、正经多模态。

> 注意：多模态能力在实际场景中可用于"游客拍照问这是什么景点"，但第一版只保证模型本身是多模态标签即可，不强制要求前端传图片。

---

### 🟡 缺失 5：评测集合规模与判定标准未定

**问题**：计划说"首版评测集"但没有具体指标。

**修正**：对标设计文档的 eval 规范——

| 维度 | 要求 |
|------|------|
| FAQ 类 | 40 题（门票、时间、位置、基础信息） |
| 知识类 | 40 题（历史、文化、建筑参数、佛教知识） |
| 推荐类 | 20 题（路线推荐、个性化建议） |
| **合计** | **100 题** |
| 判定方式 | `must_contain` 关键词匹配（主） + LLM-as-Judge（辅） |
| 格式 | JSON，含 `id/category/query/expected_answer/must_contain/source_doc` |
| 来源 | 优先从 `faq_entries.json` 和 `knowledge_entries.json` 中提取 |

---

## 四、计划中正确的部分（确认保留）

| 点 | 判断 |
|----|:--:|
| 优先做 RAG + LLM + Eval，不堆前端页面 | ✅ 完全正确 |
| 保持 OpenAI 兼容适配层 | ✅ 当前已是，无需改动 |
| 保持 SSE 流式输出不变 | ✅ pipeline 已实现句级 TTS 分发 |
| 保留 QueryRewriter | ✅ 已验证可用 |
| LLM prompt 设计为"优先依据检索证据回答" | ✅ 这是 retrieval-first 核心 |
| 证据不足时明确说明不足 | ✅ 防幻觉，pipeline 已有此分支 |
| 后续顺序：ASR → TTS → Avatar → 后台增强 | ✅ 先保正确，再加语音 |
| 不碰前端视觉、不做大屏、不动上传工作流 | ✅ 范围控制正确 |
| 行为数据不入问答事实源 | ✅ 正确 |

---

## 五、修正后的实施计划

### Phase 1：真实 RAG + Reranker（合并，不分拆）

| 序号 | 任务 | 产出 |
|------|------|------|
| 1.1 | 在 `models/` 新增 `KnowledgeChunk` 表（chunk_id, source_entry_id, chunk_index, content, metadata_json） | 数据模型 |
| 1.2 | 实现 `services/data_import/chunker.py`：按景点+主题切块，保留 metadata | 切块脚本 |
| 1.3 | 选型并实现 `services/rag/embedder.py`（`bge-small-zh-v1.5`） | Embedding 服务 |
| 1.4 | 实现 `services/rag/chroma_retriever.py`，替换 `RepositoryBackedRAGService` | ChromaDB 检索 |
| 1.5 | 实现 `services/rag/cross_encoder_reranker.py`，替换 stub Reranker | 真实重排 |
| 1.6 | 修改 `api/chat.py`：`build_pipeline` 注入新版 RAG + Reranker | 对接 |
| 1.7 | 验证检索 Top-5 含正确答案（Recall@5 > 90%） | 检索质量 |

### Phase 2：真实 LLM 接入

| 序号 | 任务 | 产出 |
|------|------|------|
| 2.1 | 确认模型选择（推荐 Qwen-VL-Plus，确认多模态） | 决策 |
| 2.2 | 在 `.env` 配置 API key / base URL / model name | 配置 |
| 2.3 | 设计首版 Prompt（system + 检索证据模板） | Prompt |
| 2.4 | 改造 `openai_compatible.py` 接入真实 HTTP 流式调用 | 代码 |
| 2.5 | 验证流式输出 + 首 token 延迟 < 2s | 延迟 |

### Phase 3：评测闭环

| 序号 | 任务 | 产出 |
|------|------|------|
| 3.1 | 从资料包提取 100 题评测集（40 FAQ + 40 知识 + 20 推荐） | 评测集 |
| 3.2 | 实现 `eval/metrics/accuracy.py`（keyword + LLM-as-Judge） | 准确率脚本 |
| 3.3 | 实现 `eval/metrics/latency.py`（P50/P95/P99） | 延迟脚本 |
| 3.4 | 实现 `eval/scripts/regression.py` | 回归入口 |
| 3.5 | 跑首轮评测，输出基线准确率 | 基线数据 |

---

## 六、延迟预算校验清单（Phase 1+2 完成后必须逐条验证）

| 检查项 | 目标 | 测量方式 |
|--------|------|---------|
| FAQ 精确匹配 | < 5ms | `perf_counter` |
| ChromaDB 检索（Top-20） | < 300ms | `perf_counter` |
| Cross-Encoder Reranker | < 150ms | `perf_counter` |
| LLM 首 token | < 2,000ms | SSE 首个 chunk 到达时间 |
| FAQ 命中全链路 | < 600ms | pipeline 计时（已有） |
| RAG+LLM 全链路 | < 5,000ms | pipeline 计时（已有） |

---

## 七、本轮明确不做

与 Codex 原计划一致：

- ❌ 不碰前端视觉和大屏
- ❌ 不接真实 ASR/TTS/Avatar
- ❌ 不做上传管理
- ❌ 不把行为数据混入问答

---

## 八、结论

**计划方向正确，批准执行。但有 5 项修正必须先落地：**

1. Reranker 不能继续用假的——必须同时实现 Cross-Encoder 重排
2. 必须明确 embedding 模型（bge-small-zh-v1.5）
3. 启动前先定延迟预算表，每步有上限
4. LLM 选型必须确认多模态（Qwen-VL-Plus 推荐）
5. 评测集至少 100 题，含判定标准
