# 2026-06-04 RAG 索引构建阶段执行总结

## 本轮开发目标

在遵守既有开发边界的前提下，推进下一阶段 Phase 1 的前半部分：

1. 先完成知识切块入库。
2. 再完成 RAG 向量索引构建入口。
3. 每完成一段即进行审查和验证。
4. 不在未确认前安装新依赖、下载模型或切换主问答链路。

## 已完成内容

### 1. 知识切块入库

新增 `KnowledgeChunk` 数据模型、仓储和切块器，并接入 `POST /api/admin/sync-processed-data`。

当前同步真实处理结果：

1. `knowledge_imported = 38`
2. `chunk_imported = 66`
3. `faq_imported = 88`
4. `route_imported = 3`
5. `behavior_imported = 1`
6. `faq_index_count = 88`

审查结论：

1. 切块来自数据库中的 `knowledge_entries`，没有运行时回退读取 JSON。
2. chunk metadata 保留了 source entry、title、category、source 等信息。
3. 未改变 FAQ 优先路径和路线推荐路径。
4. 测试已覆盖同步后 chunk 数量和 metadata。

### 2. RAG 索引构建入口

新增真实索引构建基础设施：

1. `BaseEmbedder` 接口。
2. `SentenceTransformerEmbedder` 真实 embedding 适配层，默认模型配置为 `BAAI/bge-small-zh-v1.5`。
3. `BaseVectorStore` 接口。
4. `ChromaVectorStore` 真实 ChromaDB 适配层。
5. `RAGIndexBuilder`，负责从 `KnowledgeChunkRepository` 读取切块、批量 embedding、写入向量库。
6. 后台接口 `POST /api/admin/build-rag-index`。

新增配置项：

1. `chroma_persist_dir = ../kb/chroma_db`
2. `rag_collection_name = scenic_knowledge_chunks`
3. `embedding_model_name = BAAI/bge-small-zh-v1.5`
4. `reranker_model_name = BAAI/bge-reranker-base`
5. `rag_index_batch_size = 32`
6. `rag_candidate_k = 20`
7. `rag_top_k = 5`

审查结论：

1. 生产路径指向真实 `sentence-transformers + ChromaDB`。
2. 测试路径只使用内存 fake，不会伪装成正式 RAG。
3. 缺少依赖时接口返回 `503` 和 `rag_dependency_missing`，不会静默降级。
4. 当前没有切换主问答链路，避免影响已跑通的最小闭环。

## 验证结果

已执行：

```powershell
.\.venv\Scripts\python.exe -m compileall .\app .\main.py
```

结果：通过。

已执行：

```powershell
.\.venv\Scripts\python.exe -m pytest .\app\tests -q
```

结果：`6 passed in 2.06s`。

已验证缺依赖接口行为：

```text
POST /api/admin/build-rag-index -> 503
error = rag_dependency_missing
message = sentence-transformers is not installed. Install it before building the RAG index.
```

## 当前依赖状态

当前虚拟环境中以下依赖未安装：

1. `chromadb`
2. `sentence_transformers`
3. `torch`
4. `rank_bm25`

因此真实向量索引构建入口已经完成，但还不能实际生成 Chroma 索引。

## 下一步待确认

需要用户确认是否安装真实 RAG 依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install chromadb sentence-transformers rank-bm25
```

确认后下一步建议：

1. 安装依赖。
2. 执行 `POST /api/admin/sync-processed-data` 确保 chunk 最新。
3. 执行 `POST /api/admin/build-rag-index` 生成真实 Chroma 索引。
4. 接入 `VectorBackedRAGService`，逐步替换当前 SQL LIKE 占位检索。
5. 实现真实 `CrossEncoderReranker`，替换当前只截断 Top-K 的 stub。
