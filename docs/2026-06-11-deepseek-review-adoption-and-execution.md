# 2026-06-11 DeepSeek 审查建议采纳与执行方案

## 1. 审查结论

DeepSeek 对上一版开发计划的总体评价是：方向正确、阶段拆分合理、数字人延后策略务实，可以批准执行。

但它指出了几个会直接影响最终准确率和可交付性的关键问题。经过对照当前代码后，以下建议应当采纳，并纳入正式开发顺序。

## 2. 必须采纳的修正

### 修正 1：`RetrievedDocument` 必须增加 `content` 字段

采纳等级：必须采纳。

原因：

1. 当前 `RetrievedDocument` 只有 `title`、`snippet`、`source`、`score`。
2. 后续 CrossEncoder Reranker 需要完整文本参与 `(query, document_text)` 打分。
3. 如果只用前 160 字 snippet 重排，会损失大量上下文，影响 Top-K 质量。
4. LLM prompt 后续也需要区分“完整证据文本”和“前端展示摘要”。

准备修改：

1. 修改 `backend/app/services/rag/base.py`。
2. 给 `RetrievedDocument` 增加 `content: str = ""`。
3. 保留 `snippet` 作为展示摘要。
4. 更新 `RepositoryBackedRAGService`，旧 SQL fallback 也补齐 `content`。
5. 后续 `VectorBackedRAGService` 从 Chroma 取回完整 chunk 文本后写入 `content`。
6. 后续 Reranker 默认使用 `doc.content or doc.snippet`。

### 修正 2：延迟预算必须嵌入 Phase C/D/E/F，不只做事后统计

采纳等级：必须采纳。

原因：

1. 比赛指标包含语音响应延迟 `< 5s`。
2. 如果只在最后统计，发现超时后再重构会很被动。
3. RAG、Reranker、LLM 首 token 必须从实现阶段就纳入预算。

准备加入的预算：

1. Chroma Top-20 检索：`< 300ms`。
2. CrossEncoder Reranker 20 -> 5：目标 `< 150ms`，若本机达不到则记录真实基线。
3. LLM 首 token：`< 2000ms`。
4. FAQ 命中全链路：`< 600ms`。
5. 当前无 TTS 的 RAG + LLM 全链路：优先控制在 `< 3000ms`，最大不超过 `< 5000ms`。

准备修改：

1. 在 RAG 检索、Reranker、LLM 调用处使用 `perf_counter` 记录耗时。
2. 后续评测脚本输出每段耗时。
3. 阶段审查时必须汇报实际耗时。

### 修正 3：明确 `rank-bm25` 用途

采纳等级：采纳，采用 DeepSeek 推荐的方案 B。

用途：

1. `rank-bm25` 不用于替代 Chroma。
2. 不优先改 FAQ L2。
3. 用作 `CrossEncoderReranker` 加载失败时的轻量 fallback。

原则：

1. BM25 fallback 比当前 `del query` 截断式 stub 更可靠。
2. fallback 必须显式标记，不能伪装成真实 CrossEncoder。
3. 最终交付状态仍以真实 CrossEncoder 为目标。

准备修改：

1. 后续新增 `BM25Reranker` 或 `BM25FallbackReranker`。
2. `CrossEncoderReranker` 不可用时，由配置或初始化逻辑切到 BM25。
3. 日志和测试中明确 fallback 状态。

### 修正 4：评测分两轮做

采纳等级：必须采纳。

原因：

1. 如果等 LLM 接入后才评测，就无法判断错误来自检索还是生成。
2. RAG 检索质量必须在接 LLM 前先独立验证。

调整后的评测计划：

1. 评测 v0：Phase C 完成后执行，先做 30 题检索质量评测。
2. v0 指标：Recall@5、MRR。
3. 评测 v1：Phase E 完成后执行，扩展到 100 题端到端问答。
4. v1 指标：must_contain 命中率、推荐命中率、首 token 延迟、全链路延迟。

准备修改：

1. Phase C 完成后建立 `eval` 数据和脚本的最小版本。
2. 先不等待 LLM，直接测 `query -> RAG -> Top-5 evidence`。
3. 后续再补齐 100 题端到端评测。

### 修正 5：优先安装 torch CPU 版

采纳等级：采纳。

原因：

1. 当前开发阶段不应默认下载 CUDA 版 torch。
2. CUDA 版体积大、安装慢，且本机是否有 GPU 不确定。
3. CPU 版足够完成开发期 bge-small 和 reranker 验证。

准备执行的安装顺序：

```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install chromadb sentence-transformers rank-bm25
```

说明：

1. 该步骤需要网络。
2. 该步骤需要用户确认。
3. 如果下载失败或速度异常，应停止并反馈，不自行换源或换模型。

## 3. 采纳的补充建议

### 建议 1：`VectorBackedRAGService` 增加显式降级开关

采纳方式：采纳，但必须显式标记。

做法：

1. 如果 Chroma collection 为空或未构建，运行时可以回退到 `RepositoryBackedRAGService`。
2. 回退时必须记录 warning。
3. 返回或日志中应能看出当前走的是 fallback，而不是正式向量检索。
4. 管理端 `build-rag-index` 仍然保持缺依赖返回 `503`，不静默降级。

原因：

1. 比赛现场需要安全网，Chroma 出问题时系统不能完全不可用。
2. 但安全网不能掩盖真实 RAG 未运行的问题。

### 建议 2：LLM `stream_generate` 增加可配置 system prompt

采纳方式：采纳。

做法：

1. 在 `Settings` 中增加 `llm_system_prompt`。
2. Prompt 内容不写死在调用逻辑里。
3. 真实 LLM 接入时，构造 `system + user + evidence context`。
4. evidence context 优先使用 `RetrievedDocument.content`。
5. 证据不足时要求模型明确说明资料不足，不允许编造。

原因：

1. 后续冲准确率需要持续调 prompt。
2. Prompt 配置化便于对比实验。
3. 符合 retrieval-first 原则。

## 4. 修正后的正式执行顺序

### Step 1：先做结构修正

内容：

1. `RetrievedDocument` 增加 `content`。
2. 更新旧仓储检索映射，保证 fallback 也有完整内容。
3. 调整现有测试，确保不破坏当前 pipeline。

审查：

1. 编译通过。
2. 后端测试通过。
3. FAQ 与旧 RAG fallback 不受影响。

### Step 2：确认并安装真实 RAG 依赖

内容：

1. 用户确认允许安装依赖。
2. 先装 CPU 版 torch。
3. 再装 `chromadb`、`sentence-transformers`、`rank-bm25`。
4. 更新 `backend/requirements.txt`，并注明 torch CPU 安装方式。

审查：

1. import 检查通过。
2. 原测试通过。
3. 若依赖安装失败，停止并反馈。

### Step 3：构建真实 Chroma 索引

内容：

1. 同步 processed data。
2. 调用 `POST /api/admin/build-rag-index`。
3. 使用 `BAAI/bge-small-zh-v1.5` 向量化 `KnowledgeChunk`。
4. 写入 Chroma collection。

审查：

1. indexed chunk 数量等于 DB chunk 数量。
2. metadata 完整。
3. 重复构建不会产生脏数据。

### Step 4：实现 `VectorBackedRAGService`

内容：

1. query rewrite。
2. query embedding。
3. Chroma Top-20 检索。
4. 转为 `RetrievedDocument(content + snippet + metadata)`。
5. 空 collection 时显式 fallback 到 SQL RAG。
6. 记录 Chroma 检索耗时。

审查：

1. FAQ 未命中后能走向量检索。
2. Chroma 检索目标 `< 300ms`。
3. fallback 有明确 warning。
4. 测试覆盖正常检索和 fallback。

### Step 5：评测 v0

内容：

1. 建立 30 题检索评测集。
2. 统计 Recall@5。
3. 统计 MRR。
4. 统计检索耗时。

审查：

1. 能一键运行。
2. 能输出 Markdown 或 JSON 报告。
3. 能定位问题是检索召回不足还是排序不足。

### Step 6：实现真实 Reranker

内容：

1. 新增 `CrossEncoderReranker`。
2. 默认模型 `BAAI/bge-reranker-base`。
3. 输入 `query + doc.content`。
4. 输出真实 score。
5. CrossEncoder 不可用时允许显式 BM25 fallback。
6. 记录 rerank 耗时。

审查：

1. 排序真实受 query 影响。
2. 输出包含真实 score。
3. 延迟目标 `< 150ms`，若不达标则记录真实基线并分析。
4. 测试覆盖 CrossEncoder 逻辑边界或 BM25 fallback。

### Step 7：接入真实多模态 LLM

内容：

1. 配置化 `llm_system_prompt`。
2. 选择并配置多模态模型供应商。
3. 构造 evidence-based messages。
4. 保持 SSE 输出结构。
5. 记录首 token 延迟。

审查：

1. 首 token 目标 `< 2000ms`。
2. 回答只基于证据。
3. 证据不足不编造。
4. 模型配置不写死。

### Step 8：评测 v1

内容：

1. 扩展到 100 题。
2. FAQ 40 题。
3. 知识问答 40 题。
4. 推荐 20 题。
5. 输出准确率和延迟 P50/P95。

审查：

1. 能得到端到端准确率基线。
2. 能看到每段耗时。
3. 能指导后续优化。

## 5. 数字人阶段保留但不前置

数字人相关能力仍属于最终作品目标，但不应早于真实问答主链路。

后续顺序：

1. ASR：语音转文本。
2. TTS：文本转语音。
3. Avatar：数字人播报与口型/表情同步。
4. 前端：语音交互和数字人展示区域。

原则：

1. 数字人播报内容必须来自真实 QA 链路。
2. 数字人服务失败时必须能回退到文本问答。
3. 数字人阶段继续受 `< 5s` 总延迟目标约束。

## 6. 当前准备开始做的第一步

在用户确认后，正式开发第一步应为：

**Step 1：结构修正，给 `RetrievedDocument` 增加 `content` 字段，并补齐旧 RAG fallback 的完整内容映射。**

原因：

1. 这一步不需要安装依赖。
2. 它是后续 Vector RAG、Reranker、LLM prompt 的共同基础。
3. 先修它可以降低后续改动冲突。

完成后再进入：

1. 安装真实 RAG 依赖。
2. 构建 Chroma 索引。
3. 实现 `VectorBackedRAGService`。

## 7. 需要用户确认的事项

开始正式开发前需要确认：

1. 是否同意先做 `RetrievedDocument.content` 结构修正。
2. 结构修正通过后，是否允许安装 CPU 版 torch 与真实 RAG 依赖。
3. 首次模型下载失败时，是否暂停等待用户决定，而不是自行换模型或换源。

## 8. 结论

DeepSeek 的审查建议大部分是高价值修正，应纳入正式执行计划。

调整后的近期开发路线为：

**先修 `RetrievedDocument.content` 基础结构，再安装 CPU torch 和 RAG 依赖，然后构建 Chroma 索引，接入 VectorBackedRAGService，立刻做 30 题检索评测，再实现 CrossEncoderReranker 与 BM25 fallback，最后接真实多模态 LLM 和 100 题端到端评测。**

## 9. Step 1 完成记录

完成时间：2026-06-11。

已完成内容：

1. `RetrievedDocument` 已新增 `content` 字段。
2. `snippet` 保留为展示摘要字段。
3. `RepositoryBackedRAGService` 已补齐完整正文映射。
4. 当前 stub `Reranker` 的说明已更新，明确未来真实 Reranker 应使用 `document.content`。
5. 新增测试验证旧 RAG fallback 不会丢失完整正文。

本步未做内容：

1. 未安装任何新依赖。
2. 未下载 embedding 或 reranker 模型。
3. 未切换主问答链路。
4. 未修改前端。
5. 未接入 Chroma 查询路径。

验证结果：

```powershell
.\.venv\Scripts\python.exe -m compileall .\app .\main.py
.\.venv\Scripts\python.exe -m pytest .\app\tests -q
```

结果：

```text
7 passed in 1.41s
```

本步审查结论：

1. 符合 DeepSeek 的修正 1。
2. 不影响 FAQ 优先路径。
3. 不影响旧 SQL fallback。
4. 为后续 `VectorBackedRAGService`、`CrossEncoderReranker` 和真实 LLM prompt 提供了完整证据文本基础。

下一步待确认：

1. 是否允许安装 CPU 版 torch。
2. 是否允许安装 `chromadb`、`sentence-transformers`、`rank-bm25`。
3. 是否允许首次构建索引时下载 `BAAI/bge-small-zh-v1.5`。

## 10. Step 2 完成记录

完成时间：2026-06-11。

用户要求：

1. 允许安装真实 RAG 依赖。
2. 所有东西尽量安装到 D 盘。

已完成内容：

1. 确认 Python 虚拟环境位于 `D:\桌面\软件杯\backend\.venv`。
2. 确认依赖安装目录位于 `D:\桌面\软件杯\backend\.venv\Lib\site-packages`。
3. 创建 D 盘缓存目录：
   - `D:\桌面\软件杯\.cache\pip`
   - `D:\桌面\软件杯\.cache\huggingface`
   - `D:\桌面\软件杯\.cache\torch`
   - `D:\桌面\软件杯\.cache\tmp`
4. 使用 CPU wheel index 安装 `torch`。
5. 安装真实 RAG 依赖：
   - `chromadb`
   - `sentence-transformers`
   - `rank-bm25`
6. 更新 `backend/requirements.txt`，记录直接依赖版本。
7. 新增 `model_cache_dir` 配置项，后续模型缓存固定到 `D:\桌面\软件杯\.cache\huggingface`。
8. `SentenceTransformerEmbedder` 已支持传入 D 盘 cache folder。
9. `POST /api/admin/build-rag-index` 后续加载 embedding 模型时会使用 D 盘模型缓存目录。

已安装核心版本：

```text
torch==2.12.0+cpu
chromadb==1.5.9
sentence-transformers==5.5.1
rank-bm25==0.2.2
```

路径确认：

```text
Chroma 持久化目录：D:\桌面\软件杯\kb\chroma_db
模型缓存目录：D:\桌面\软件杯\.cache\huggingface
pip 缓存目录：D:\桌面\软件杯\.cache\pip
```

本步未做内容：

1. 未下载 `BAAI/bge-small-zh-v1.5` 模型文件。
2. 未构建 Chroma 向量索引。
3. 未切换主问答链路。
4. 未实现 `VectorBackedRAGService`。
5. 未实现真实 `CrossEncoderReranker`。

验证结果：

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall .\app .\main.py
.\.venv\Scripts\python.exe -m pytest .\app\tests -q
```

结果：

```text
No broken requirements found.
7 passed in 1.65s
```

本步审查结论：

1. 依赖安装成功，且核心包均可正常 import。
2. 依赖安装位置在 D 盘项目虚拟环境。
3. pip 下载缓存已指定到 D 盘。
4. 后续模型缓存和 Chroma 持久化目录已固定到 D 盘。
5. 原有后端测试未被破坏。

下一步：

1. 调用数据同步接口，确保 `KnowledgeChunk` 最新。
2. 调用 `POST /api/admin/build-rag-index`。
3. 首次调用时会下载 `BAAI/bge-small-zh-v1.5` 到 D 盘模型缓存目录。
4. 构建完成后验证 indexed chunk 数量与 DB chunk 数量一致。

## 11. 评测工具短改记录

完成时间：2026-06-11。

背景：

1. 用户要求暂时不要继续主线。
2. DeepSeek 的 `07-本轮修改指令.md` 中包含多个 Phase，其中主线索引构建、RAG 切换、Reranker、真实 LLM、情感分析等暂不执行。
3. 本轮只采纳其中“评测闭环提前补强”的低风险部分。

已完成内容：

1. `eval/metrics/accuracy.py` 已从单一关键词函数扩展为可复用评测模块。
2. 新增 `AccuracyReport` 与 `AccuracyFailure` 结构。
3. 新增 `evaluate_cases()`，支持 `must_contain`、`must_not_contain`，并兼容 `key_points`。
4. 新增 `evaluate()`，可直接读取测试集文件并返回 dict。
5. `eval/scripts/regression.py` 已改为结构化 JSON 输出。
6. regression 当前为 `offline_smoke` 模式，使用 `expected_answer` 作为临时 answer function。
7. 修正 `eval/testset/recommend_test.json` 的样例答案，使其与 `must_contain` 自洽。

本步未做内容：

1. 未构建 Chroma 索引。
2. 未接入 `VectorBackedRAGService`。
3. 未修改 `backend/app/api/chat.py`。
4. 未接真实 Reranker。
5. 未接真实 LLM。
6. 未新增情感分析依赖或数据库字段。

验证结果：

```powershell
.\backend\.venv\Scripts\python.exe .\eval\scripts\regression.py
.\backend\.venv\Scripts\python.exe -c "from pathlib import Path; from eval.metrics.accuracy import evaluate; result=evaluate(Path('eval/testset/faq_test.json'), lambda q: '灵山大佛通高88米'); print(result['accuracy'], result['passed'], result['total'])"
cd backend
.\.venv\Scripts\python.exe -m pytest .\app\tests -q
```

结果：

```text
offline_smoke: total_cases=3, total_passed=3, overall_accuracy=1.0
accuracy.evaluate smoke: 1.0 1 1
7 passed in 4.97s
```

本步审查结论：

1. 评测工具已经具备后续接真实 pipeline/API 的基本结构。
2. 本轮没有继续主线，没有引入新依赖。
3. 后端现有测试未受影响。

## 12. Step 3 完成记录：真实 Chroma 索引构建

完成时间：2026-06-11。

已完成内容：

1. 检查 RAG 依赖可用：
   - `torch==2.12.0+cpu`
   - `chromadb==1.5.9`
   - `sentence-transformers==5.5.1`
   - `rank-bm25==0.2.2`
2. 确认路径仍固定在 D 盘：
   - Chroma 持久化目录：`D:\桌面\软件杯\kb\chroma_db`
   - 模型缓存目录：`D:\桌面\软件杯\.cache\huggingface`
   - Torch 缓存目录：`D:\桌面\软件杯\.cache\torch`
3. 调用 `POST /api/admin/sync-processed-data`，同步结果：
   - `knowledge_imported = 38`
   - `chunk_imported = 66`
   - `faq_imported = 88`
   - `route_imported = 3`
   - `behavior_imported = 1`
4. 调用 `POST /api/admin/build-rag-index`，首次下载并加载 `BAAI/bge-small-zh-v1.5`。
5. 成功构建 Chroma collection：`scenic_knowledge_chunks`。
6. Chroma 实际 collection count 验证为 `66`。
7. 真实检索 smoke test：
   - query：`灵山大佛有多高`
   - Top-1：`灵山大佛`
   - Top-1 chunk：`ke_13_001`
8. 离线缓存模式下再次构建索引成功，说明模型已可从 D 盘缓存加载。

构建结果：

```text
message = RAG index built successfully.
total_chunks = 66
indexed_chunks = 66
collection_name = scenic_knowledge_chunks
embedding_model_name = BAAI/bge-small-zh-v1.5
first_build_duration_ms = 8078
offline_rebuild_duration_ms = 8700
```

生成文件：

```text
D:\桌面\软件杯\kb\chroma_db\chroma.sqlite3
D:\桌面\软件杯\kb\chroma_db\cfe396a6-0aa2-4b94-8d17-954de36ccba3\
D:\桌面\软件杯\.cache\huggingface\models--BAAI--bge-small-zh-v1.5\
```

注意事项：

1. HuggingFace 首次下载时提示 Windows 当前环境不支持 symlink，缓存仍可正常工作，但可能占用更多磁盘空间。
2. 当前只是构建索引，主问答链路尚未切换到 Chroma。
3. 当前 `POST /api/chat/stream` 仍然走旧的 SQL fallback RAG。

验证结果：

```powershell
.\.venv\Scripts\python.exe -m compileall .\app .\main.py
.\.venv\Scripts\python.exe -m pytest .\app\tests -q
```

结果：

```text
7 passed in 2.15s
```

本步审查结论：

1. Phase 1 真实 Chroma 索引构建完成。
2. 索引数量与 DB chunk 数量一致。
3. 模型缓存和向量库均位于 D 盘项目目录。
4. 后端现有测试未受影响。

下一步：

1. 暂停，不直接继续主线。
2. 待用户确认后进入 `VectorBackedRAGService`。
3. 下一阶段目标是让 FAQ 未命中后走 Chroma 向量检索，并保留旧 SQL fallback 作为显式降级。

## 13. Step 4 完成记录：VectorBackedRAGService

完成时间：2026-06-11。

背景：

1. 开始本阶段时发现工作区已由其他进程或 AI 新增 `chroma_retriever.py`，并提前修改 `chat.py`。
2. 用户确认由 Codex 接管现有修改并修正缺口。
3. 原实现没有真正 SQL fallback，且使用 16 维零向量探测 512 维 Chroma collection，会产生错误警告。

已完成内容：

1. 保留并完善 `VectorBackedRAGService`。
2. 删除错误的 16 维零向量初始化探测。
3. 给 `BaseVectorStore` 新增 `count()` 接口。
4. `ChromaVectorStore.count()` 在 collection 不存在时返回 `0`。
5. `ChromaVectorStore.query()` 增加以下保护：
   - collection 不存在时返回空结果
   - collection 为空时返回空结果
   - `top_k <= 0` 时返回空结果
   - `n_results` 不超过实际记录数
6. `VectorBackedRAGService` 增加真正的 `BaseRAGService` fallback。
7. 以下情况会显式 warning 并回退到 `RepositoryBackedRAGService`：
   - Chroma collection 为空
   - embedding 或 Chroma query 抛异常
   - Chroma 返回零候选
8. 新增检索状态字段：
   - `last_mode`
   - `last_embedding_ms`
   - `last_vector_query_ms`
9. 向量候选数量使用配置项 `rag_candidate_k`。
10. reranker 返回的 score 会同步写回 `RetrievedDocument.score`。
11. `chat.py` 保持 `QAPipeline` 依赖注入结构不变，但增加：
    - cached `SentenceTransformerEmbedder`
    - cached `ChromaVectorStore`
    - `RepositoryBackedRAGService` fallback
    - 向量运行时初始化失败时的显式 SQL fallback
12. 避免每次聊天请求重新加载 embedding 模型。

新增测试：

1. 正常向量检索能映射完整 `content`、200 字 `snippet`、真实 source 和 score。
2. 空 collection 时不调用 embedder，直接使用 SQL fallback。
3. vector query 异常时使用 SQL fallback。

验证结果：

```text
compileall: passed
pytest: 10 passed in 1.88s
```

真实服务验证：

```text
service = VectorBackedRAGService
embedder_reused = True
mode = vector
embedding_ms = 154.23
vector_query_ms = 33.16
```

真实查询：

```text
query = 请介绍灵山梵宫的建筑特色与文化意义
Top-1 = 灵山梵宫
Top-2 = 灵山梵宫
```

SSE 接口验证：

```text
POST /api/chat/stream -> 200
source_count = 5
first_source.title = 五印坛城
first_source.source = 灵山胜境 景点结构化数据集.docx - 灵山胜境 / 五印坛城
```

本步未做内容：

1. 未接真实 CrossEncoder Reranker。
2. 未接 BM25 fallback reranker。
3. 未接真实 LLM。
4. 未修改前端页面。
5. 当前 LLM 回答仍然包含占位生成文本，但 sources 已来自真实 Chroma。

本步审查结论：

1. FAQ 优先路径保持不变。
2. FAQ 未命中后已进入真实 Chroma 向量检索。
3. Chroma query 延迟 `33.16ms`，低于 `<300ms` 目标。
4. SQL fallback 已真实可用并有明确 warning。
5. embedding 模型已缓存复用。
6. 后端现有测试未受影响。

下一步：

1. 暂停，不直接进入 Reranker。
2. 待用户审查并确认后，进入检索评测 v0 或真实 CrossEncoder Reranker 阶段。

## 14. 检索评测 v0 完成记录

完成时间：2026-06-11。

本轮范围：

1. 只评测 `QueryRewriter -> BGE embedding -> Chroma Top-5`。
2. 不包含 FAQ、CrossEncoder Reranker、BM25 和 LLM。
3. 不修改现有知识数据、Chroma 索引和主问答接口。

已完成内容：

1. 新增 `eval/testset/retrieval_test.json`，包含 30 个自然语言问题。
2. 题目分类如下：
   - 景点事实与特色：10 题
   - 历史文化：8 题
   - 建筑艺术：6 题
   - 游客服务与路线：6 题
3. 每题记录 `id`、`category`、`query`、`expected_titles` 和 `source_doc`。
4. 扩展检索指标：
   - `Recall@1`
   - `Recall@5`
   - `MRR`
5. 扩展延迟统计：
   - 平均值
   - P50
   - P95
   - 最小值
   - 最大值
6. 新增 `eval/scripts/retrieval_regression.py`，使用 D 盘离线模型缓存和真实 Chroma 索引执行评测。
7. 新增评测指标单元测试 `eval/tests/test_retrieval_metrics.py`。
8. 生成机器可读报告 `eval/reports/retrieval_v0.json`。

真实评测结果：

```text
case_count = 30
Recall@1 = 96.67%
Recall@5 = 100.00%
MRR = 98.33%
embedding P50 = 29.08ms
embedding P95 = 63.51ms
Chroma query P50 = 9.63ms
Chroma query P95 = 12.44ms
total P50 = 39.50ms
total P95 = 78.15ms
```

分类结果：

```text
景点事实与特色：Recall@1 100%，Recall@5 100%，MRR 100%
历史文化：Recall@1 87.5%，Recall@5 100%，MRR 93.75%
建筑艺术：Recall@1 100%，Recall@5 100%，MRR 100%
游客服务与路线：Recall@1 100%，Recall@5 100%，MRR 100%
```

唯一 Top-1 偏位：

1. 问题：`抱佛脚、摸天下第一掌等互动体现了景区的哪种特色体验？`
2. 目标知识：`祈福文化的特色体验`，实际排名第 2。
3. 排名第 1：`其他特色景点`。
4. 两段知识都包含相关互动景点内容，属于内容重叠，不是 Top-5 漏召回。
5. 本轮不为了提高分数修改测试预期或知识数据，后续可由 Reranker 处理排序区分。

门槛检查：

```text
Recall@5 >= 90%: passed
MRR >= 0.75: passed
Chroma query P95 < 300ms: passed
```

本步未做内容：

1. 未安装或接入 CrossEncoder Reranker。
2. 未接入 BM25 混合检索。
3. 未接入真实 LLM。
4. 未调整前端页面。

验证结果：

```text
eval/tests: 3 passed
backend/app/tests: 10 passed
compileall: passed
```

说明：后端测试必须在 `backend` 目录运行；从项目根目录直接运行时，现有项目结构不会自动把 `backend` 加入 `PYTHONPATH`。

本步审查结论：

1. 30 题均能在 Top-5 召回目标知识。
2. 评测题使用自然语言事实描述，不以直接复制标题作为统一问法。
3. 指标计算、延迟分位数和空输入边界已有单元测试。
4. 本阶段完成后停止，不自动进入 Reranker 阶段。

## 15. Reranker 阶段执行记录（模型下载阻塞）

执行时间：2026-06-11。

已完成内容：

1. 新增 `CrossEncoderReranker`：
   - 使用 `(query, document.content)` 批量评分。
   - `content` 为空时才使用 `snippet`。
   - 支持 `cache_dir`、`batch_size`、`max_length` 和 `local_files_only`。
   - 支持注入假模型，单元测试不依赖网络。
2. 新增 `BM25Reranker`：
   - 使用已安装的 `rank-bm25`。
   - 中文使用单字与字符二元组词元。
   - 未新增 `jieba` 或其他依赖。
3. 新增 `ResilientReranker`，降级顺序为：
   - `cross_encoder`
   - `bm25_fallback`
   - `stable_order_fallback`
4. 主链路接入：
   - `chat.py` 使用 `lru_cache` 缓存 Reranker。
   - 运行时使用 `local_files_only=True`，服务启动不会擅自下载模型。
   - `VectorBackedRAGService` 新增 `last_rerank_ms`。
   - `VectorBackedRAGService` 新增 `last_reranker_mode`。
   - 未包装的 Reranker 异常也会保留 Chroma 原始顺序。
5. 新增配置：
   - `reranker_batch_size=8`
   - `reranker_max_length=512`
6. `.env.example` 补充 RAG 与 Reranker 配置示例。

测试结果：

```text
Reranker 新增单元测试：9 passed
后端全部测试：20 passed
评测指标测试：3 passed
compileall：passed（独立模块阶段）
```

离线缺模验证：

```text
ResilientReranker
primary = None
fallback = BM25Reranker
```

说明：模型未缓存时，主链路会明确使用 BM25 fallback，不会联网、不伪装为 CrossEncoder，也不会中断问答。

模型下载阻塞：

1. 按确认方案尝试从 Hugging Face 下载 `BAAI/bge-reranker-base`。
2. 所有缓存环境变量均指向 `D:\桌面\软件杯\.cache\huggingface`。
3. 下载进程约运行 6 分钟，Python 进程仍响应，但权重 `.incomplete` 文件始终为 `0` 字节。
4. Hugging Face Xet 日志已生成，说明阻塞发生在 Xet 权重传输阶段。
5. 已终止外层下载任务及其残留 Python 子进程，确认不再占用缓存锁。

当前停止点：

1. 未禁用 Xet 重试。
2. 未切换 Hugging Face 镜像。
3. 未更换模型。
4. 未继续真实模型 smoke test。
5. 未编写或运行 30 题 Reranker 对比评测。
6. 等待用户确认下载问题的处理方式。

交接补充：

1. 已生成独立下载交接文件 `docs/2026-06-11-bge-reranker-download-handoff.md`。
2. 交接前再次复核发现缓存中已存在 `1,112,206,140` 字节的 `model.safetensors`，且当前无 `.incomplete` 权重与残留 lock。
3. snapshot 暂只确认 `config.json` 与 `model.safetensors`，tokenizer 文件未确认齐全，不能视为下载完成。
4. 接手 AI 的任务限定为从官方源补齐同一模型并完成离线真实推理，不允许修改代码、换模型、换镜像或继续评测。

## 16. Reranker 模型验收与 30 题对比评测

完成时间：2026-06-12。

### 16.1 模型离线验收

缓存状态：

```text
模型：BAAI/bge-reranker-base
缓存目录：D:\桌面\软件杯\.cache\huggingface
缓存文件数：14
缓存总大小：1,134,374,859 bytes
.incomplete 文件数：0
snapshot：2cfc18c9415c912f9d8155881c133215df768a70
```

离线真实推理：

```text
local_files_only=True：成功
模型加载：16180.62ms
首次两文档推理：763.83ms
灵山大佛 score：0.999656
餐饮 score：0.000049
排序：灵山大佛 > 餐饮
```

主链路验收：

```text
wrapper = ResilientReranker
primary = CrossEncoderReranker
fallback = BM25Reranker
```

### 16.2 新增评测能力

新增：

```text
eval/scripts/reranker_regression.py
eval/reports/reranker_v0.json
```

评测范围：

```text
QueryRewriter
  -> BGE embedding
  -> Chroma Top-20
  -> bge-reranker-base Top-5
```

同一 30 题同时记录：

1. Chroma 原始 Top-5。
2. Chroma Top-20 中期望知识的原始排名。
3. CrossEncoder 重排后的 Top-5。
4. 重排前后 Recall@1、Recall@5、MRR。
5. embedding、Chroma、Reranker、total 的平均值、P50、P95、最小值和最大值。
6. 模型加载与 Top-20 预热耗时。

旧报告 `eval/reports/retrieval_v0.json` 保持不变，没有被覆盖。

### 16.3 准确率结果

```text
原始 Recall@1 = 96.67%
重排 Recall@1 = 100.00%
变化 = +3.33 个百分点

原始 Recall@5 = 100.00%
重排 Recall@5 = 100.00%
变化 = 0

原始 MRR = 98.33%
重排 MRR = 100.00%
变化 = +1.67 个百分点
```

分类结果：

```text
景点事实与特色：重排后 Recall@1 / Recall@5 / MRR 均为 100%
历史文化：Recall@1 从 87.5% 提升到 100%，MRR 从 93.75% 提升到 100%
建筑艺术：重排后 Recall@1 / Recall@5 / MRR 均为 100%
游客服务与路线：重排后 Recall@1 / Recall@5 / MRR 均为 100%
```

唯一发生目标排名变化的题目：

```text
id = retrieval-016
问题 = 抱佛脚、摸天下第一掌等互动体现了景区的哪种特色体验？
目标 = 祈福文化的特色体验
原始排名 = 2
重排后排名 = 1
原始 Top-1 = 其他特色景点
重排 Top-1 = 祈福文化的特色体验
```

没有 Top-5 失败项，没有准确率退化题。

### 16.4 延迟结果

初始化与预热：

```text
Embedding 模型加载 = 11125.01ms
Reranker 模型加载 = 2597.24ms
Reranker Top-20 预热 = 938.77ms
```

30 题正式计时：

```text
Embedding P50 = 16.31ms
Embedding P95 = 25.86ms

Chroma P50 = 7.87ms
Chroma P95 = 12.35ms

Reranker P50 = 4731.09ms
Reranker P95 = 6079.41ms
Reranker min = 3797.26ms
Reranker max = 6108.44ms

Total P50 = 4751.77ms
Total P95 = 6117.22ms
```

门槛判定：

```text
重排 Recall@5 >= 90%：passed
重排 Recall@5 不低于原始：passed
重排 MRR 不低于原始：passed
Reranker P95 < 150ms：failed
```

总体结果：

```text
accuracy_passed = true
performance_passed = false
passed = false
```

### 16.5 回归结果

```text
backend/app/tests：20 passed
eval/tests：3 passed
compileall：passed
```

### 16.6 审查结论与停止点

1. `bge-reranker-base` 在当前 30 题上实现 100% Top-1、Top-5 与 MRR，排序质量达到目标。
2. CPU 对 20 个完整 chunk 做 CrossEncoder 推理约需 3.8 到 6.1 秒，远高于 `<150ms` 预算。
3. 性能瓶颈明确位于 Reranker，不在 embedding 或 Chroma。
4. 当前实现不满足后续语音全链路 `<5s` 的赛题预算，不能直接按现状进入 LLM。
5. 按既定约束，不擅自更换模型、减少候选数、截短文本或切换硬件方案。
6. 本阶段停止，等待用户或外部审查决定下一步性能方案。
