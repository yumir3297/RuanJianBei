# Reranker 性能问题审查单（提交 DeepSeek）

- 编写日期：2026-06-12
- 项目根目录：`D:\桌面\软件杯`
- 当前阶段：真实 RAG + 真实 CrossEncoder Reranker
- 当前状态：准确率达标，CPU 延迟严重超标，已停止后续 LLM 开发
- 审查目标：确定 Reranker 性能优化的下一步方案与验收标准

## 1. 先给结论

当前不是“功能未实现”，而是一个明确的性能冲突：

```text
BAAI/bge-reranker-base 在 30 题上把检索 Top-1 和 MRR 提升到 100%，
但 CPU 对 Chroma Top-20 完整 chunk 做重排时，P50 约 4.73 秒、P95 约 6.08 秒。
```

因此：

1. Reranker 排序质量达到目标。
2. Reranker 性能完全不满足原设计 `<150ms`。
3. 单独 Reranker P95 已超过赛题最终语音链路 `<5s` 的总预算。
4. 当前不能直接继续接 LLM、TTS 和数字人，否则全链路延迟必然进一步恶化。

需要 DeepSeek 评估：下一步应如何在准确率、CPU 延迟、模型大小、候选数量和文本长度之间取舍。

## 2. 项目当前真实进度

### 2.1 已完成

1. 官方景区资料提取、清洗和结构化。
2. Knowledge 38 条，Knowledge Chunk 66 条。
3. FAQ 88 条，路线 3 条，行为摘要 1 条。
4. FAQ `DB -> 内存索引`。
5. QueryRewriter。
6. `BAAI/bge-small-zh-v1.5` embedding。
7. Chroma collection `scenic_knowledge_chunks`，66 个 chunk。
8. FAQ 未命中后进入真实 Chroma 检索。
9. Chroma 失败时显式 SQL fallback。
10. `BAAI/bge-reranker-base` 已下载到 D 盘并可完全离线推理。
11. CrossEncoder、BM25 fallback、原向量顺序三级保护。
12. 30 题无重排检索报告和真实重排对比报告。

### 2.2 尚未开始

1. 真实多模态 LLM。
2. 100 题端到端问答评测。
3. 真实 ASR。
4. 真实 TTS。
5. 数字人驱动。
6. Reranker 性能优化。

当前停止在 Reranker 性能决策点，没有进入 LLM。

## 3. 当前技术环境

### 3.1 运行环境

```text
操作系统：Windows
Python：项目 D 盘虚拟环境
推理设备：CPU
torch：2.12.0+cpu
sentence-transformers：5.5.1
transformers：5.11.0
huggingface_hub：1.18.0
```

当前没有启用 CUDA、ONNX Runtime 或 OpenVINO。

### 3.2 固定路径

```text
项目：D:\桌面\软件杯
虚拟环境：D:\桌面\软件杯\backend\.venv
模型缓存：D:\桌面\软件杯\.cache\huggingface
Chroma：D:\桌面\软件杯\kb\chroma_db
```

### 3.3 当前模型

```text
Embedding：BAAI/bge-small-zh-v1.5
Reranker：BAAI/bge-reranker-base
Reranker 缓存大小：约 1.134GB
```

## 4. 当前检索与重排流程

```text
用户问题
  -> FAQ 精确/模糊匹配
  -> FAQ 未命中
  -> QueryRewriter
  -> bge-small embedding
  -> Chroma Top-20
  -> bge-reranker-base CrossEncoder
  -> Top-5
  -> 后续 LLM（尚未接入）
```

Reranker 输入：

```text
(query, document.content)
```

其中 `document.content` 为完整 chunk，不是 160/200 字 snippet。

当前参数：

```text
candidate_k = 20
top_k = 5
batch_size = 8
max_length = 512
device = CPU
```

## 5. 准确率事实

测试集：30 个自然语言景区问题。

类别：

```text
景点事实与特色：10
历史文化：8
建筑艺术：6
游客服务与路线：6
```

### 5.1 无 Reranker 基线

```text
Recall@1 = 96.67%
Recall@5 = 100.00%
MRR = 98.33%
```

### 5.2 CrossEncoder 重排后

```text
Recall@1 = 100.00%
Recall@5 = 100.00%
MRR = 100.00%
```

变化：

```text
Recall@1：+3.33 个百分点
Recall@5：0
MRR：+1.67 个百分点
```

没有 Top-5 失败项，没有准确率退化题。

### 5.3 实际改善的题目

只有 1 题的目标排名发生变化：

```text
id：retrieval-016
问题：抱佛脚、摸天下第一掌等互动体现了景区的哪种特色体验？
目标：祈福文化的特色体验
原始排名：2
重排后排名：1
原始 Top-1：其他特色景点
重排 Top-1：祈福文化的特色体验
```

这说明当前 Chroma 原始排序已经很强，CrossEncoder 的边际收益是把 30 题中的 1 题从第 2 提升到第 1。

## 6. 延迟事实

以下均为完全离线、模型只加载一次并预热后的 30 题正式计时。

### 6.1 Embedding

```text
平均：17.00ms
P50：16.31ms
P95：25.86ms
最大：27.44ms
```

### 6.2 Chroma Top-20

```text
平均：9.05ms
P50：7.87ms
P95：12.35ms
最大：32.31ms
```

### 6.3 CrossEncoder Top-20 -> Top-5

```text
平均：5006.45ms
P50：4731.09ms
P95：6079.41ms
最小：3797.26ms
最大：6108.44ms
```

### 6.4 当前检索总耗时

```text
平均：5032.50ms
P50：4751.77ms
P95：6117.22ms
最大：6139.27ms
```

### 6.5 初始化与预热

```text
Embedding 模型加载：11125.01ms
Reranker 模型加载：2597.24ms
Reranker Top-20 预热：938.77ms
```

初始化已通过进程内缓存避免每请求重复发生。当前瓶颈不是模型重复加载，而是每次 CrossEncoder 推理本身。

## 7. 已经排除的问题

### 7.1 不是模型没有生效

完全离线 smoke test：

```text
query：灵山大佛有多高
灵山大佛 score：0.999656
餐饮 score：0.000049
```

主链路：

```text
wrapper = ResilientReranker
primary = CrossEncoderReranker
fallback = BM25Reranker
```

### 7.2 不是 Chroma 慢

Chroma Top-20 P95 只有 `12.35ms`。

### 7.3 不是 embedding 慢

Embedding P95 只有 `25.86ms`。

### 7.4 不是每次重新加载模型

`chat.py` 使用 `lru_cache` 缓存 Reranker 实例。

### 7.5 不是网络延迟

所有评测均在：

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
local_files_only=True
```

条件下运行。

### 7.6 不是单次冷启动假象

正式计时前已完成 Top-20 Reranker 预热，30 次正式推理仍为 3.8 至 6.1 秒。

## 8. 当前实现关键点

关键文件：

```text
backend/app/services/rag/cross_encoder_reranker.py
backend/app/services/rag/bm25_reranker.py
backend/app/services/rag/resilient_reranker.py
backend/app/services/rag/chroma_retriever.py
backend/app/api/chat.py
eval/scripts/reranker_regression.py
eval/reports/reranker_v0.json
```

核心推理逻辑：

```python
pairs = [(query, document.content or document.snippet) for document in documents]
scores = model.predict(
    pairs,
    batch_size=8,
    show_progress_bar=False,
    convert_to_numpy=True,
)
```

模型构造：

```python
CrossEncoder(
    "BAAI/bge-reranker-base",
    cache_folder="D:/桌面/软件杯/.cache/huggingface",
    local_files_only=True,
    max_length=512,
)
```

## 9. 为什么这是阻塞问题

题目最终要求包括：

1. 文本与语音交互。
2. TTS。
3. 数字人口型与表情驱动。
4. 最终语音交互响应延迟 `<5s`。

当前仅 Reranker：

```text
P50 = 4.73s
P95 = 6.08s
```

尚未加入：

```text
LLM 首 token
LLM 全文生成
TTS
数字人驱动
网络或 API 延迟
```

因此按当前配置继续开发，即便后续组件全部优化，也几乎不可能满足 `<5s`。

## 10. 当前不能擅自做的事情

Codex 已按用户要求停止，没有自行执行：

1. 不更换 Reranker 模型。
2. 不把 candidate_k 从 20 改为 5/10。
3. 不把 max_length 从 512 改短。
4. 不把完整 chunk 改为 snippet。
5. 不安装 ONNX Runtime 或 OpenVINO。
6. 不启用量化。
7. 不修改 chunk 策略。
8. 不跳过 Reranker。
9. 不仅对低置信问题启用 Reranker。
10. 不使用 GPU/CUDA。
11. 不直接进入 LLM 阶段。

以上都属于有明显精度或工程后果的决策，需要先审查确认。

## 11. 请求 DeepSeek 评估的候选方向

请不要只回答“换小模型”或“使用 GPU”，需要对以下每个方向给出：预期延迟、准确率风险、改动范围、是否满足赛题、建议优先级和验证方法。

### 方向 A：减少候选数量

示例：

```text
Top-20 -> Top-10 -> Top-5
```

需要评估：

1. 现有 30 题中目标知识在原始 Top-10 的覆盖率是多少。
2. 候选减半的理论和实测延迟收益。
3. 对扩展到 100 题后的 Recall 风险。
4. 是否应采用动态 candidate_k。

### 方向 B：缩短 CrossEncoder 输入

示例：

```text
max_length 512 -> 256 / 192 / 128
```

需要评估：

1. 当前 chunk 实际 token 长度分布。
2. 截断发生比例。
3. 标题 + 关键句 + snippet 是否比完整 chunk 更合理。
4. 如何避免破坏设计文档强调的“不能只看 160 字摘要”。

### 方向 C：换更小的 Reranker

需要明确推荐具体模型，而不是泛称“小模型”。

需要评估：

1. 中文景区知识检索效果。
2. Windows CPU 支持。
3. 模型体积和内存占用。
4. 是否能在 30 题维持 100% 或至少不低于原始 96.67% Top-1。
5. 是否有商业或比赛使用限制。

### 方向 D：ONNX / OpenVINO / INT8

需要评估：

1. 当前 `sentence-transformers 5.5.1` 是否可直接使用 `backend="onnx"` 或 `backend="openvino"`。
2. Windows CPU 的实际支持和安装成本。
3. 是否需要模型导出。
4. INT8 对排序分数和准确率的影响。
5. 预期能否从 5 秒降低到可接受范围，而不只是 10%-20% 改善。

### 方向 E：条件式 Reranker

示例：

```text
Chroma Top-1 分数或 Top-1/Top-2 差距足够大 -> 直接返回
低置信或歧义问题 -> CrossEncoder
```

需要评估：

1. 30 题中实际上只有 1 题受益于 Reranker，是否适合条件触发。
2. 如何定义可解释的置信阈值。
3. 如何防止高置信错误。
4. 评测应同时报告平均、P95 和 Reranker 触发率。
5. 这种方案是否符合赛题“准确率 ≥90%”和稳定性要求。

### 方向 F：缓存 Reranker 结果

需要评估：

1. FAQ/常见问法是否适合 query 规范化后缓存。
2. 首次请求仍然很慢，缓存是否只能改善重复请求。
3. 缓存 key、TTL 和知识更新失效策略。
4. 是否只是辅助方案，不能作为主性能解决方案。

### 方向 G：异步/流式掩盖延迟

需要评估：

1. Reranker 完成前无法确定最终证据，是否真的能提前启动 LLM。
2. 先使用 Chroma Top-1 回答、后续纠正是否会造成事实不一致。
3. 此方向能否真实降低首 token，而非仅改变界面观感。

### 方向 H：GPU 或独立推理服务

需要评估：

1. 比赛部署环境是否可以依赖 GPU。
2. 如果开发机无 GPU，是否应把 Reranker 部署成远程推理服务。
3. 网络延迟与稳定性风险。
4. 是否符合当前“本地可演示、所有依赖位于 D 盘”的约束。

## 12. 希望 DeepSeek 回答的关键问题

请逐项明确回答：

1. `<150ms` 的原 Reranker 预算在 Windows CPU + `bge-reranker-base` + Top-20 + 512 tokens 条件下是否现实？
2. 当前实测 3.8-6.1 秒是否属于合理 CPU 基线，还是存在明显实现/线程配置错误？
3. 首选优化路线是什么？请给出具体执行顺序，而不是并列十种可能。
4. 哪些优化可以同时保留当前 100% 的 30 题结果？
5. 哪些优化必须重新跑 30 题，哪些必须先扩展到 100 题才能判断？
6. 是否建议保留 `bge-reranker-base`，还是更换具体轻量模型？
7. 如果换模型，推荐的准确模型名、下载体积、CPU 推理预期和许可证是什么？
8. 是否建议先测 Top-10 与 max_length 256 的组合？如果是，请给出停止/通过门槛。
9. 是否建议实现条件式 Reranker？置信阈值应如何由现有报告数据推导？
10. 是否值得引入 ONNX/OpenVINO/INT8？推荐哪一个作为 Windows CPU 首选？
11. 最终语音全链路 `<5s` 的预算应该如何重新分配给：FAQ、embedding、Chroma、Reranker、LLM、TTS、Avatar？
12. 在性能方案确定前，是否应该继续 LLM 开发，还是保持当前停止状态？

## 13. 期望 DeepSeek 给出的输出格式

希望审查结果按以下格式返回：

```text
一、对当前问题定位的判断
二、当前实现是否存在代码层性能错误
三、推荐的唯一主方案
四、可接受的备选方案
五、明确不建议的方案及原因
六、下一轮具体修改文件与步骤
七、每一步准确率和延迟验收门槛
八、失败时应停止并询问用户的条件
九、是否允许进入 LLM 阶段
```

## 14. 当前测试与报告位置

```text
无重排报告：D:\桌面\软件杯\eval\reports\retrieval_v0.json
重排报告：D:\桌面\软件杯\eval\reports\reranker_v0.json
30 题测试集：D:\桌面\软件杯\eval\testset\retrieval_test.json
评测脚本：D:\桌面\软件杯\eval\scripts\reranker_regression.py
Reranker 实现：D:\桌面\软件杯\backend\app\services\rag\cross_encoder_reranker.py
主 RAG 服务：D:\桌面\软件杯\backend\app\services\rag\chroma_retriever.py
依赖构建：D:\桌面\软件杯\backend\app\api\chat.py
```

## 15. 当前验证状态

```text
backend/app/tests：20 passed
eval/tests：3 passed
compileall：passed
accuracy_passed：true
performance_passed：false
```

## 16. 当前停止边界

在 DeepSeek 审查和用户确认前：

1. 不修改 Reranker 参数。
2. 不换模型。
3. 不增加推理后端依赖。
4. 不改变 chunk 或候选策略。
5. 不进入真实 LLM。
6. 不继续 ASR、TTS、Avatar 或前端开发。

下一步仅在收到审查结果并由用户确认后执行。
