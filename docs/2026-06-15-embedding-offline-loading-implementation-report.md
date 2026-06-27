# Embedding 离线加载修复实施记录

- 日期：2026-06-15
- 依据：`设计文档/11-Embedding离线加载修复方案.md`
- 状态：已完成并通过验收

## 本轮目标

修复聊天运行时在网络不可用时仍尝试访问 Hugging Face、继而退化为 SQL 检索的问题，使已缓存于 D 盘的 `BAAI/bge-small-zh-v1.5` 能被直接离线加载。

## 修改范围

1. 为 `SentenceTransformerEmbedder` 增加向后兼容的 `local_files_only` 关键字参数，并透传给 `SentenceTransformer`。
2. 聊天运行时固定使用 `local_files_only=True`。
3. 检索与重排评测脚本固定使用 `local_files_only=True`。
4. 增加参数传递测试，并执行离线模型、Chroma 检索、编译和后端回归验证。

## 明确不修改

1. 不更换或下载模型。
2. 不重建 Chroma 索引。
3. 不修改 Reranker、数据库 Schema、配置项、依赖和前端。
4. 管理端 `build-rag-index` 保持默认允许首次下载。

## 风险与停止条件

1. 若本地模型缺失或损坏，立即停止，不擅自下载或替换模型。
2. 若当前 `sentence-transformers` 版本不支持 `local_files_only`，停止并报告，不擅自升级依赖。
3. 若离线 Embedder 可加载但 Chroma 检索失败，保留现有 SQL 降级并单独定位，不扩大本轮范围。

## 验收标准

1. `local_files_only` 参数被正确透传，默认值仍为 `False`。
2. D 盘模型在离线条件下成功生成向量。
3. 聊天 Pipeline 在离线条件下构建为向量 RAG，而不是初始化阶段退化到 SQL。
4. Chroma 检索能够返回结果。
5. `compileall` 与后端完整测试通过。

## 实施结果

1. `SentenceTransformerEmbedder` 已新增 `local_files_only` 关键字参数，默认值保持 `False`。
2. 聊天运行时固定传入 `local_files_only=True`，管理端索引构建保持原行为。
3. 两个检索评测脚本已同步使用离线加载。
4. 新增两项单元测试，覆盖参数透传、默认行为和聊天运行时离线约束。
5. 强制 `HF_HUB_OFFLINE=1` 后，D 盘模型成功输出 `512` 维向量。
6. 现有 Chroma 集合共 `66` 条记录，离线向量查询成功返回结果。
7. 聊天 Pipeline 在离线环境中实际构建为 `VectorBackedRAGService`，检索模式为 `vector`，未退化到 SQL。
8. Embedder 专项测试 `2 passed`，后端完整回归 `32 passed`。
9. 后端应用与评测脚本 `compileall` 均通过。

## 审查结论

本轮修改符合最小范围要求，没有更换模型、重建索引、修改依赖、数据库或前端。Embedding 离线加载阻塞已解除，可以回到阶段 A1 的受控快捷追问主线。
