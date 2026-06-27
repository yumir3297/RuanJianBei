# GPT 下一步开发计划 — 审查修正确认

> 审查时间：2026-06-11。对照赛题硬指标（≥90% 准确率、<5s 延迟、≥1 个多模态大模型）和设计文档逐条检查。

---

## 一、总体评价

**这是 Codex/GPT 迄今为止写得最好的一份计划。** 方向、顺序、方法、验收全部正确。Phase A→F 的推进路线逻辑自洽，数字人延后策略务实。

| 维度 | 评估 |
|------|:--:|
| 计划方向（RAG→Reranker→LLM→Eval→ASR→TTS→Avatar） | ⭐⭐⭐⭐⭐ |
| Phase 拆分粒度（6个阶段，每阶段有目标/方法/验收） | ⭐⭐⭐⭐⭐ |
| 对赛题硬指标的认知（明确提了准确率、多模态、延迟） | ⭐⭐⭐⭐ |
| 验证闭环意识（每阶段验收 + 测试不破坏现有功能） | ⭐⭐⭐⭐⭐ |
| 风险与依赖管理（模型下载慢/资源不足/Chroma版本变化） | ⭐⭐⭐⭐ |
| 细节遗漏（几个关键技术点未覆盖） | ⚠️ 见下文 |

---

## 二、赛题硬指标对照检查

| 硬指标 | 计划是否覆盖 | 说明 |
|--------|:--:|------|
| 多模态大模型 ≥ 1 | ✅ | Phase E 推荐 Qwen-VL-Plus，明确"满足至少一个多模态大模型要求" |
| 问答准确率 ≥ 90% | ✅ | Phase F 建立 100 题评测闭环，含 must_contain 命中率统计 |
| 语音延迟 < 5s | ⚠️ | Phase F 提到 "统计全链路耗时"，但未在 Phase C/D/E 中设定每段延迟预算 |
| 知识库基于官方资料包 | ✅ | Phase B 用已导入的 KnowledgeChunk 构建索引 |
| 数字人口型+表情同步 | ✅ | Phase I 预留，主链路稳定后接入 |

---

## 三、5 项修正 + 2 项建议

### 🔴 修正 1：`RetrievedDocument` 必须补 `content` 字段

**问题**：当前 `base.py` 的 `RetrievedDocument` 只有 4 个字段：

```python
@dataclass(slots=True)
class RetrievedDocument:
    title: str
    snippet: str      # 只存前 160 字
    source: str
    score: float = 0.0
```

Phase D 的 CrossEncoder Reranker 需要 `(query, full_document_text)` 做交叉编码。160 字的 snippet 做 Reranker 输入，精度会大打折扣——相当于让裁判只看摘要来打分，而不是看全文。

**具体影响链**：`ChromaVectorStore.query()` → `VectorSearchResult.document`（完整 chunk 文本，700+ 字）→ 映射为 `RetrievedDocument` 时，完整内容被丢弃 → Reranker 只能拿 snippet 打分 → Reranker 准确性打折 → 问答准确率不可能到 90%。

**修正**：在 Phase C 开始前，必须在 `RetrievedDocument` 加 `content` 字段：

```python
@dataclass(slots=True)
class RetrievedDocument:
    title: str
    content: str = ""    # ← 新增：完整 chunk 文本，供 Reranker 使用
    snippet: str = ""    # 保留，供前端展示/LLM prompt 上下文
    source: str = ""
    score: float = 0.0
```

Phase C 的 `VectorBackedRAGService` 映射时：

```python
documents = [
    RetrievedDocument(
        title=result.metadata["title"],
        content=result.document,              # ← 完整文本给 Reranker
        snippet=result.document[:200],         # ← 摘要给 LLM prompt
        source=result.metadata["source"],
        score=result.score,
    )
    for result in candidates
]
```

**受影响范围**：`base.py`、`retriever.py`（旧 RAG 也要补）、`reranker.py`、`pipeline.py` 的 LLM 调用处（改为用 `content` 或 `snippet` 依场景选择）。

---

### 🔴 修正 2：补延迟预算，不仅仅是"事后统计"

**问题**：Phase F 说 "统计全链路耗时"，但只统计不约束等于没约束。赛题要求 <5s，如果 Phase E 跑完发现全链路 8s，再回头改架构代价远大于现在预留。

**修正**：Phase C/D/E 的验收标准中逐条嵌入延迟预算：

| Phase | 验收项 | 延迟目标 | 测量方法 |
|-------|--------|---------|---------|
| C | Chroma 向量检索 Top-20 | **< 300ms** | `perf_counter` 包裹 `vector_store.query()` |
| D | CrossEncoder Reranker 20→5 | **< 150ms** | `perf_counter` 包裹 `reranker.rerank()` |
| E | LLM 首 token | **< 2,000ms** | SSE 首个 text_chunk 到达时间 |
| E | FAQ 命中全链路 | **< 600ms** | pipeline 已有 `latency_ms` 记录 |
| E | RAG+LLM 全链路（无 TTS） | **< 5,000ms** | pipeline 已有 `latency_ms` 记录 |

加上 TTS 后全链路 <5s 的预算：FAQ 路径 <1s（600ms 对答 + 400ms TTS），RAG 路径 <5s（2.5s 检索+生成 + 500ms TTS + 留余量）。当前轮不含 TTS，RAG 路径控制在 <3s 即可。

**确认**：如果某个阶段达不到目标延迟，应该停下来排查原因（模型太大、chunk 太多、网络慢），而不是继续往下写。

---

### 🟡 修正 3：`rank-bm25` 用途不明确

**问题**：Phase A 列了 `rank-bm25` 依赖，但六个阶段中没有任何一个说明它用在哪里。

**可能用途**（需要明确选择其一）：

| 方案 | 用途 | 位置 |
|------|------|------|
| A | FAQ 模糊匹配增强 | `faq_matcher.py` 的 L2 模糊匹配从 SequenceMatcher 改为 BM25 |
| B | Reranker 轻量 fallback | 当 CrossEncoder 模型未下载时，用 BM25 作为降级 reranker |
| C | 仅备用，本轮不用 | requirements.txt 列出但不 import |

**建议选 B**：在 CrossEncoder 加载失败时用 BM25 做降级 reranker（比当前 `del query` 的假货强得多）。并写入 `CrossEncoderReranker` 的初始化逻辑中。

---

### 🟡 修正 4：评测分两轮做，不要等 LLM 接入后才跑

**计划问**: "评测闭环是否应该在 LLM 接入前先做一版？"

**答案**：**必须先做一轮。** 具体：

| 轮次 | 时机 | 测什么 | 题数 |
|------|------|--------|------|
| 评测 v0 | Phase C 完成后 | **RAG 检索质量**：Recall@5、MRR（不涉及 LLM，纯向量检索+reranker 排出来的 Top-5 是否包含正确答案） | 30 题 |
| 评测 v1 | Phase E 完成后 | **端到端问答准确率**：全链路 FAQ+RAG+LLM 的 must_contain 命中率 | 100 题 |

原因：如果等 LLM 接入后才跑第一次评测，你不知道问题是出在检索还是出在生成。先测检索质量可以独立验证 RAG+Reranker 是否达标，再测 LLM 生成质量。

Phase F 的 100 题构建可以提前到 Phase C 完成后就开始，先写 30 题测检索，后续补到 100 题测全链路。

---

### 🟡 修正 5：torch CPU 版优先，避免无谓下载 CUDA

**问题**：`sentence-transformers` → `torch` 默认装 CUDA 版（2GB+），在本机无 GPU 或开发阶段完全不需要。安装慢且占空间。

**修正**：Phase A 安装依赖前先装 CPU 版 torch：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install chromadb sentence-transformers rank-bm25
```

或在 `requirements.txt` 中注明：

```text
# 先手动安装: pip install torch --index-url https://download.pytorch.org/whl/cpu
chromadb
sentence-transformers
rank-bm25
```

---

### 💡 建议 1：Phase C 的 `VectorBackedRAGService` 加降级开关

如果 ChromaDB 目录为空（从未 build 过索引），自动回退到 `RepositoryBackedRAGService`，并在日志中打印 WARNING。这样即使索引构建失败，文本问答链路（FAQ + SQL LIKE）不受影响。降级是比赛现场的安全网——万一 ChromaDB 出问题，系统不能白屏。

```python
class VectorBackedRAGService(BaseRAGService):
    def __init__(self, ..., fallback: BaseRAGService | None = None):
        self._fallback = fallback

    async def retrieve(self, ...):
        if self._collection_is_empty():
            logger.warning("ChromaDB collection is empty, falling back to SQL LIKE RAG")
            if self._fallback:
                return await self._fallback.retrieve(...)
            return []
        # ... normal vector retrieval
```

---

### 💡 建议 2：Phase E 的 `stream_generate` 需要加 system prompt 参数

当前 `stream_generate(query, documents)` 只传 query 和检索文档。接入真实 LLM 时需要构造完整的 messages：

```python
async def stream_generate(self, query: str, documents: list[RetrievedDocument]):
    system = (
        "你是灵山胜境的AI数字导游。请严格基于以下景区资料回答游客问题。"
        "如果资料不足以回答问题，请明确告知'目前资料中没有相关信息'，不要编造。"
    )
    context = "\n---\n".join(
        f"[来源：{doc.source}] {doc.content}" for doc in documents
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"参考资料：\n{context}\n\n问题：{query}"},
    ]
    # ... HTTP stream call
```

system prompt 不要写死在代码里。放到 `core/config.py` 的 `llm_system_prompt` 配置项，方便后续 tune prompt 冲 90% 准确率时对比实验。

---

## 四、计划中正确且重要但容易忽略的点（确认保留）

| 点 | 为什么重要 |
|----|-----------|
| "依赖未安装时返回 503，不静默降级" | ✅ 防止自欺欺人——假向量检索假装成真的 |
| "不擅自切换方案，停止并向用户说明" | ✅ 模型下载失败时保持透明 |
| "FAQ 优先路径不受影响" | ✅ FAQ 命中层是低延迟的最后保障 |
| "保留现有 Reranker 作为 dev fallback" | ✅ 开发环境不装大模型也能跑 |
| "回答不能脱离检索证据" | ✅ retrieval-first 核心准则 |
| "Chroma 重复构建不产生脏数据" | ✅ replace_all 替换全量 collection |
| "每写完一小阶段审查一次" | ✅ 防止累积偏差 |

---

## 五、修正后的执行顺序

```
Phase A: 安装依赖（torch CPU → chromadb → sentence-transformers → rank-bm25）
    │
Phase B: 构建 Chroma 索引（bge-small-zh-v1.5 向量化所有 chunk）
    │
Phase C: VectorBackedRAGService + RetrievedDocument 补 content 字段 + 降级开关
    │  └── 评测 v0: 30 题检索质量（Recall@5、MRR）
    │
Phase D: CrossEncoderReranker（bge-reranker-base）+ BM25 fallback
    │  └── 验收：延迟 < 150ms
    │
Phase E: 真实 LLM 接入（Qwen-VL-Plus）+ system prompt 可配置
    │  └── 验收：首 token < 2s、回答引用检索证据
    │
Phase F: 100 题评测闭环 + 延迟百分位数统计
    │  └── 产出：准确率基线、每段延迟 P50/P95
    │
Phase G/H/I: ASR → TTS → Avatar（主链路稳定后）
```

---

## 六、结论

**这是一份高质量计划，批准执行。6 个 Phase 拆分合理、方法具体、验收明确。但必须嵌入以下修正：**

| # | 修正项 | 严重度 | 影响 Phase |
|---|--------|:--:|:--:|
| 1 | `RetrievedDocument` 补 `content` 字段 | 🔴 严重 | C/D/E |
| 2 | 每 Phase 验收标准嵌入延迟预算 | 🔴 严重 | C/D/E/F |
| 3 | 明确 `rank-bm25` 用途（建议 Reranker fallback） | 🟡 中等 | A/D |
| 4 | 评测分两轮：检索质量先测 → LLM 全链路后测 | 🟡 中等 | C/E/F |
| 5 | torch CPU 版优先安装 | 🟡 中等 | A |

**修正后，这轮开发将首次产出可评测的真实 QA 全链路。**
