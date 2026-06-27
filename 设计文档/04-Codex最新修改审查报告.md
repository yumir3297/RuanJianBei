# Codex 最新修改 — 审查报告

> 审查时间：2026-06-06。逐文件验证了本轮所有新增和修改，对照赛题硬指标（准确率 ≥ 90%、延迟 < 5s、多模态大模型）和设计文档要求。

---

## 一、审查摘要

| 维度 | 评估 | 说明 |
|------|:--:|------|
| 基础设施搭建 | ⭐⭐⭐⭐ | ChromaDB、Embedder、IndexBuilder、Chunker 质量不错 |
| 配置驱动化 | ⭐⭐⭐⭐⭐ | `.env`+`Settings` 全覆盖，Chroma 路径/模型名都可配置 |
| 核心链路连通 | 🔴 **0 分** | **最严重问题：所有新增能力都没有接到问答主链路** |
| 评测体系 | 🔴 **极弱** | 只有 3 道占位题 + 1 个未完成的函数 |
| 赛题硬指标 | 🔴 **未达标** | LLM 仍是占位、Reranker 仍是假货、问答链路仍是 SQL LIKE |

**:tada:一句话：Codex 把"厨房设备和食材"都备好了，但锅没开火，菜没下锅。**

---

## 二、逐模块审查

### 2.1 已正确完成的部分

| 文件 | 审查结论 |
|------|:--:|
| `services/rag/vector_store.py` | ✅ `ChromaVectorStore` 实现正确，`replace_all`/`query` 逻辑通顺 |
| `services/rag/embedder.py` | ✅ `SentenceTransformerEmbedder` 调用 `bge-small-zh-v1.5`，`SimpleEmbedder` 用于开发测试 |
| `services/rag/index_builder.py` | ✅ 批量 embedding + 写入 ChromaDB + 计时报告，流水线清晰 |
| `services/data_import/chunker.py` | ✅ 句级切分 + 50字 overlap + metadata 继承，策略合理 |
| `models/knowledge_chunk.py` | ✅ 结构完整，`chunk_id` 主键 + 外键关联 `knowledge_entries` |
| `repositories/knowledge_chunk.py` | ✅ `replace_all` 事务式替换 |
| `tests/test_faq_perf.py` | ✅ FAQ 加载 < 1000ms + 精确匹配 < 5ms 验证完整 |
| `core/config.py` | ✅ `chroma_persist_dir`、`embedding_model_name`、`reranker_model_name`、`rag_candidate_k` 等全部可配置 |
| `models/__init__.py` | ✅ 所有新模型已注册 |
| `admin.py` 数据同步 + RAG索引构建 | ✅ `POST /sync-processed-data` 和 `POST /build-rag-index` 两个接口实现正确 |

---

### 2.2 🔴 严重问题

#### 问题 1：RAG 检索 — ChromaDB 建了但没用（最致命）

**现状**：

```
chat.py (QA主链路)
  └── RepositoryBackedRAGService    ← SQL LIKE + 词频打分，旧占位
        └── Reranker()              ← del query + 截断，假货
```

**同时存在但未连接的新组件**：
- `ChromaVectorStore` — 向量检索（存在，未使用）
- `SentenceTransformerEmbedder` — bge-small 向量化（存在，未使用）
- `RAGIndexBuilder` — 索引构建（存在，仅在 admin API 手动调用，不参与问答）
- `settings.embedding_model_name = "BAAI/bge-small-zh-v1.5"` — 配置了，`chat.py` 从不读取
- `settings.reranker_model_name = "BAAI/bge-reranker-base"` — 配置了，`chat.py` 从不读取

**缺失的组件**：需要一个 `ChromaBackedRAGService` 类，实现 `BaseRAGService.retrieve()` 接口，内部调用 `ChromaVectorStore.query()` + `SentenceTransformerEmbedder.embed()`。当前不存在这个类。

**修正**：

```python
# 新文件：backend/app/services/rag/chroma_retriever.py
class ChromaBackedRAGService(BaseRAGService):
    def __init__(self, vector_store, embedder, query_rewriter, reranker):
        self.vector_store = vector_store
        self.embedder = embedder
        self.query_rewriter = query_rewriter
        self.reranker = reranker

    async def retrieve(self, query, normalized_query=None, top_k=5):
        normalized = normalized_query or self.query_rewriter.rewrite(query)
        query_vec = self.embedder.embed(normalized)
        candidates = self.vector_store.query(query_vec, top_k=20)
        documents = [RetrievedDocument(title=m["title"], snippet=m["document"][:160], 
                      source=m.get("source",""), score=m.score) for m in candidates]
        ranked = self.reranker.rerank(query, documents, top_k=top_k)
        return [item.document for item in ranked]
```

```python
# 修改：backend/app/api/chat.py 的 build_pipeline()
from app.services.rag.chroma_retriever import ChromaBackedRAGService
from app.services.rag.embedder import SentenceTransformerEmbedder
from app.services.rag.vector_store import ChromaVectorStore

def build_pipeline(session, settings):
    ...
    return QAPipeline(
        ...
        rag_service=ChromaBackedRAGService(
            vector_store=ChromaVectorStore(settings.chroma_persist_root, settings.rag_collection_name),
            embedder=SentenceTransformerEmbedder(settings.embedding_model_name),
            query_rewriter=query_rewriter,
            reranker=?????,   # ← 问题2
        ),
        ...
    )
```

---

#### 🔴 问题 2：Reranker 仍然是假货

**现状**：`reranker.py` 第 15-24 行：

```python
class Reranker:
    def rerank(self, query, documents, top_k=5):
        del query          # 丢弃 query，不做任何交叉编码
        trimmed = documents[:top_k]
        return [RerankResult(document=doc, score=doc.score or 0.0) for doc in trimmed]
```

**赛题要求**：问答准确率 ≥ 90%。没有 Cross-Encoder Reranker，ChromaDB 的 Recall@5 最多 70-80%，不可能达到 90%。

**上一次审查已明确指出这是假货，本次仍未修正。**

**修正**：

```python
# 新文件：backend/app/services/rag/cross_encoder_reranker.py
from sentence_transformers import CrossEncoder
from app.services.rag.reranker import Reranker, RerankResult

class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self._model = CrossEncoder(model_name)

    def rerank(self, query, documents, top_k=5):
        if not documents:
            return []
        pairs = [(query, doc.content if hasattr(doc,'content') else doc.snippet) for doc in documents]
        scores = self._model.predict(pairs, show_progress_bar=False)
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return [RerankResult(document=doc, score=float(score)) for doc, score in ranked[:top_k]]
```

然后在 `chat.py` 注入 `CrossEncoderReranker(settings.reranker_model_name)`。

---

#### 🔴 问题 3：LLM 仍然是占位

**现状**：`openai_compatible.py` 第 14-25 行返回硬编码文本，不做任何真实 API 调用。

```python
async def stream_generate(self, query, documents):
    answer = f"根据当前检索到的景区资料，和"{query}"最相关的内容来自..."  # 硬编码
    for token in answer:
        await asyncio.sleep(0)
        yield token
```

**赛题要求**："需明确使用至少 1 个多模态大模型"。"至少"意味着必须有真实模型接入。

**修正**：必须实现真实的 OpenAI 兼容 HTTP 流式调用：

```python
import httpx

async def stream_generate(self, query, documents):
    system_prompt = "你是灵山胜境的AI导游..."  # phase 3 细调
    context = "\n".join(f"[来源{doc.source}] {doc.snippet}" for doc in documents)
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream(
            "POST", f"{self.settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
            json={"model": self.settings.llm_model, "messages": [...], "stream": True}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: ") and not line.endswith("[DONE]"):
                    delta = json.loads(line[6:])["choices"][0]["delta"].get("content","")
                    if delta:
                        yield delta
```

---

#### 🔴 问题 4：评测集只有 3 道占位题

**设计文档要求**：100 题（40 FAQ + 40 知识 + 20 推荐）。

**现状**：

```
faq_test.json:       1 题   ← 只有"灵山大佛多高"
knowledge_test.json: 1 题   ← 只有"五印坛城是什么"
recommend_test.json:  1 题   ← 只有"适合两小时亲子游"
```

**accuracy.py 只有一个函数**，没有完整的评测循环、没有统计输出、没有错误样例收集。

**修正**：按照设计文档的格式，至少扩充到 20-30 题首版（最终目标 100 题）。`accuracy.py` 需要实现完整的评测循环。

---

### 2.3 🟡 中等问题

#### 问题 5：`RetrievedDocument` 缺少 `content` 字段

**现状**：`base.py` 的 `RetrievedDocument` 只有 `title/snippet/source/score`，没有 `content`。

**影响**：Reranker 需要完整的文档内容做交叉编码（不是 160 字 snippet），缺少 `content` 字段会导致 Cross-Encoder 效果差。

**修正**：

```python
@dataclass(slots=True)
class RetrievedDocument:
    title: str
    content: str = ""    # ← 新增：完整内容，供 Reranker 使用
    snippet: str = ""
    source: str = ""
    score: float = 0.0
```

---

#### 问题 6：没有降级策略

**现状**：如果 ChromaDB 路径不存在或 embedding 模型未下载，系统会直接报错，没有 fallback。

**修正**：在 `ChromaBackedRAGService` 初始化时检测 ChromaDB 是否有数据，如果没有则回退到 `RepositoryBackedRAGService`（SQL LIKE），且打印 warning 日志。

---

## 三、赛题硬指标对照

| 硬指标 | 要求 | 当前状态 | 差距 |
|--------|------|:--:|------|
| 多模态大模型 ≥ 1 个 | 必须 | 🔴 | LLM 仍是占位硬编码文本 |
| 问答准确率 ≥ 90% | 必须 | 🔴 | RAG 链路未接入、Reranker 是假货、无评测集 |
| 语音响应延迟 < 5s | 必须 | 🟡 | 延迟记录代码已就绪（pipeline 计时），但真实 RAG+LLM 路径不存在无法实测 |
| 知识库基于官方资料包 | 必须 | ✅ | 数据已入库、importer 完整、FAQ+知识+路线全覆盖 |
| 管理后台 | 功能需求 | ✅ | 概览+统计+数据同步+索引构建 API 完整 |
| 数字人口型+表情同步 | 功能需求 | 🟡 | stub 已就位、接口已定义，未接真实 |

---

## 四、修正优先级

| 优先级 | 问题 | 预计工作量 |
|:--:|------|:--:|
| P0 | 创建 `ChromaBackedRAGService` + 接入 `chat.py` | 1 个新文件 + 改 1 行 |
| P0 | 实现 `CrossEncoderReranker` + 接入 | 1 个新文件 + 改 1 行 |
| P0 | LLM 真实 HTTP 流式调用 | 改 1 个文件 |
| P1 | `RetrievedDocument` 补 `content` 字段 | 改 1 个 dataclass |
| P1 | 评测集扩充到 30 题 + 评测循环 | 写 JSON + 改脚本 |
| P2 | 降级策略 | 改 `ChromaBackedRAGService` |

---

## 五、结论

**Codex 本轮做对的事**：基础设施（ChromaDB、Embedder、IndexBuilder、Chunker、配置系统、FAQ 性能测试）全部正确实现，代码质量不错。

**Codex 本轮做错的事**：所有新组件都没有接到 QA 主链路。相当于把发动机、变速箱、轮胎都造好了但没装到车上。加上 Reranker 和 LLM 两个关键模块仍然是占位，问答核心系统实际上一毫米都没有前进。

**修正后效果预估**：P0 三项修完之后，可以首次验证真实 QA 全链路（FAQ 命中 < 30ms / RAG+LLM 期望 < 5s），开始跑评测 → 调参 → 冲 90%。
