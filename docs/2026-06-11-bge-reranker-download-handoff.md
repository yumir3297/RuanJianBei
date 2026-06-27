# bge-reranker-base 下载与离线验证全盘交接

- 交接日期：2026-06-11
- 项目根目录：`D:\桌面\软件杯`
- 当前负责范围：只补齐并验证 `BAAI/bge-reranker-base` 模型
- 当前主线阶段：Reranker Step 3（模型下载与离线验证）
- 后续接回方：Codex

## 1. 交接目标

请接手 AI 只完成以下任务：

1. 从 Hugging Face 官方源续传或补齐同一个模型：`BAAI/bge-reranker-base`。
2. 所有模型文件与缓存必须留在 D 盘项目目录。
3. 在完全离线模式下完成一次真实 CrossEncoder 加载和推理。
4. 验证项目主链路能够构建真实 `CrossEncoderReranker`，而不是 BM25 fallback。
5. 将实际执行命令、结果、耗时和最终缓存状态回填到本文档末尾。

本交接不要求、也不允许继续编写 Reranker 评测脚本或进入 LLM 阶段。

## 2. 项目总体进度

### 2.1 已完成的数据与检索能力

1. FastAPI 后端与 Vue 前端骨架已可运行。
2. 官方景区资料已完成结构化并接入数据库。
3. 当前数据规模：
   - Knowledge：38
   - Knowledge Chunk：66
   - FAQ：88
   - Route：3
   - Visitor Behavior Summary：1
4. FAQ 已实现 `DB -> 内存索引`。
5. FAQ 未命中后已进入真实 Chroma 向量检索。
6. Embedding 模型 `BAAI/bge-small-zh-v1.5` 已位于 D 盘缓存。
7. Chroma collection：`scenic_knowledge_chunks`，记录数 66。
8. Chroma 或 embedding 异常时会显式退回数据库检索。

### 2.2 无 Reranker 的 30 题基线

报告文件：

```text
D:\桌面\软件杯\eval\reports\retrieval_v0.json
```

基线指标：

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

不要修改此测试题、期望标题或知识数据来提高分数。

## 3. Reranker 代码当前状态

Reranker 代码已经完成，不需要接手 AI 修改。

### 3.1 已实现模块

```text
D:\桌面\软件杯\backend\app\services\rag\reranker.py
D:\桌面\软件杯\backend\app\services\rag\cross_encoder_reranker.py
D:\桌面\软件杯\backend\app\services\rag\bm25_reranker.py
D:\桌面\软件杯\backend\app\services\rag\resilient_reranker.py
```

运行降级顺序：

```text
CrossEncoder
  -> BM25 fallback
  -> 保留 Chroma 原始向量顺序
```

明确模式名：

```text
cross_encoder
bm25_fallback
stable_order_fallback
```

### 3.2 主链路已接入

关键文件：

```text
D:\桌面\软件杯\backend\app\api\chat.py
D:\桌面\软件杯\backend\app\services\rag\chroma_retriever.py
D:\桌面\软件杯\backend\app\core\config.py
```

当前行为：

1. `get_cached_reranker()` 使用 `lru_cache`，同一配置只加载一次模型。
2. 主链路加载模型时固定使用 `local_files_only=True`，不会在聊天请求期间联网下载。
3. 模型不完整时，`primary=None`，明确使用 `BM25Reranker`。
4. `VectorBackedRAGService` 已记录：
   - `last_rerank_ms`
   - `last_reranker_mode`
5. Reranker 推理异常不会丢弃已经成功返回的 Chroma 候选。

### 3.3 已通过测试

```text
Reranker 新增单元测试：9 passed
后端全部测试：20 passed
评测指标测试：3 passed
compileall：passed
```

后端测试必须从 `backend` 目录执行：

```powershell
Set-Location 'D:\桌面\软件杯\backend'
.\.venv\Scripts\python.exe -m pytest .\app\tests -q
```

接手 AI 不需要重新设计、重写或格式化这些代码。

## 4. Python 与依赖环境

必须使用项目虚拟环境：

```text
D:\桌面\软件杯\backend\.venv\Scripts\python.exe
```

已安装版本：

```text
huggingface_hub = 1.18.0
hf-xet = 1.5.1
sentence-transformers = 5.5.1
transformers = 5.11.0
torch = 2.12.0+cpu
rank-bm25 = 0.2.2
```

依赖均安装在 D 盘虚拟环境。不要调用系统 Python 安装依赖，不要向 C 盘创建新虚拟环境。

## 5. 固定路径与环境变量

### 5.1 固定缓存路径

```text
Hugging Face 根缓存：D:\桌面\软件杯\.cache\huggingface
Torch 缓存：D:\桌面\软件杯\.cache\torch
目标模型缓存：D:\桌面\软件杯\.cache\huggingface\models--BAAI--bge-reranker-base
Embedding 模型缓存：D:\桌面\软件杯\.cache\huggingface\models--BAAI--bge-small-zh-v1.5
Chroma 数据：D:\桌面\软件杯\kb\chroma_db
```

### 5.2 下载前必须设置

```powershell
$env:HF_HOME='D:\桌面\软件杯\.cache\huggingface'
$env:HUGGINGFACE_HUB_CACHE='D:\桌面\软件杯\.cache\huggingface\hub'
$env:TRANSFORMERS_CACHE='D:\桌面\软件杯\.cache\huggingface\transformers'
$env:TORCH_HOME='D:\桌面\软件杯\.cache\torch'
$env:PYTHONPATH='D:\桌面\软件杯\backend'
```

如果决定按当前建议绕过卡住的 Xet 传输，再额外设置：

```powershell
$env:HF_HUB_DISABLE_XET='1'
```

必须仍使用 Hugging Face 官方源，不要同时设置第三方 `HF_ENDPOINT`。

下载阶段应移除离线变量：

```powershell
Remove-Item Env:HF_HUB_OFFLINE -ErrorAction SilentlyContinue
Remove-Item Env:TRANSFORMERS_OFFLINE -ErrorAction SilentlyContinue
```

## 6. 上一次下载发生了什么

上一次执行的核心逻辑为：

```python
from sentence_transformers import CrossEncoder

CrossEncoder(
    "BAAI/bge-reranker-base",
    cache_folder="D:/桌面/软件杯/.cache/huggingface",
    max_length=512,
)
```

当时现象：

1. 下载进程运行约 6 分钟没有命令输出。
2. 初次检查时权重 `.incomplete` 文件为 0 字节。
3. Hugging Face Xet 日志已生成，因此判断传输卡在 Xet 路径。
4. 外层任务终止后发现下载 Python 子进程仍残留，随后已单独终止 PID `15600`。
5. 当前模型 lock 目录存在但为空，没有遗留 lock 文件。
6. 不要根据旧的“0 字节”结论直接删除目录，因为终止前缓存状态又发生了变化。

## 7. 当前缓存真实状态

截至交接文档生成时，目标目录已经存在，统计为：

```text
文件数：8
总字节数：1,112,206,979
```

关键文件：

```text
refs\main
  40 bytes

snapshots\2cfc18c9415c912f9d8155881c133215df768a70\config.json
  799 bytes

snapshots\2cfc18c9415c912f9d8155881c133215df768a70\model.safetensors
  1,112,206,140 bytes
```

当前没有 `.incomplete` 权重文件，且模型 lock 目录为空。

但是 snapshot 当前只看到 `config.json` 与 `model.safetensors`，没有看到 tokenizer 相关文件。因此：

1. 不能宣布模型已经完整下载。
2. 不要删除现有 1.11GB `model.safetensors`。
3. 优先让 Hugging Face 根据现有缓存补齐缺失文件。
4. 最终以离线真实加载和推理成功为唯一完成标准。

`.no_exist` 目录中的 0 字节标记是 Hugging Face 对仓库中不存在文件的缓存标记，不等同于模型权重损坏，不要手工删除或当作失败文件。

## 8. 接手 AI 推荐执行顺序

### Step A：不要先删除缓存

先确认：

1. `model.safetensors` 大小仍为 `1,112,206,140` 字节。
2. `.locks\models--BAAI--bge-reranker-base` 中没有 lock 文件。
3. 不存在本次旧下载进程 PID `15600`。

不要执行清空整个 `.cache\huggingface` 的命令。

### Step B：禁用 Xet 后用官方源补齐模型

推荐直接再次构造同一个 CrossEncoder，让依赖根据当前缓存补齐 tokenizer 等必要文件：

```powershell
Set-Location 'D:\桌面\软件杯'

$env:HF_HOME='D:\桌面\软件杯\.cache\huggingface'
$env:HUGGINGFACE_HUB_CACHE='D:\桌面\软件杯\.cache\huggingface\hub'
$env:TRANSFORMERS_CACHE='D:\桌面\软件杯\.cache\huggingface\transformers'
$env:TORCH_HOME='D:\桌面\软件杯\.cache\torch'
$env:PYTHONPATH='D:\桌面\软件杯\backend'
$env:HF_HUB_DISABLE_XET='1'

Remove-Item Env:HF_HUB_OFFLINE -ErrorAction SilentlyContinue
Remove-Item Env:TRANSFORMERS_OFFLINE -ErrorAction SilentlyContinue

& 'D:\桌面\软件杯\backend\.venv\Scripts\python.exe' -c "from sentence_transformers import CrossEncoder; model=CrossEncoder('BAAI/bge-reranker-base', cache_folder='D:/桌面/软件杯/.cache/huggingface', max_length=512); print('online_load_ok')"
```

如果该命令失败：

1. 记录完整错误信息。
2. 停止，不要换模型。
3. 不要切换第三方镜像。
4. 不要删除 1.11GB 权重后重新开始。
5. 将错误回填到本文档。

### Step C：完全离线加载并执行真实推理

下载命令成功后，必须新开一个进程执行：

```powershell
Set-Location 'D:\桌面\软件杯'

$env:HF_HOME='D:\桌面\软件杯\.cache\huggingface'
$env:HUGGINGFACE_HUB_CACHE='D:\桌面\软件杯\.cache\huggingface\hub'
$env:TRANSFORMERS_CACHE='D:\桌面\软件杯\.cache\huggingface\transformers'
$env:TORCH_HOME='D:\桌面\软件杯\.cache\torch'
$env:PYTHONPATH='D:\桌面\软件杯\backend'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'

& 'D:\桌面\软件杯\backend\.venv\Scripts\python.exe' -c "from pathlib import Path; from app.services.rag.base import RetrievedDocument; from app.services.rag.cross_encoder_reranker import CrossEncoderReranker; reranker=CrossEncoderReranker(model_name='BAAI/bge-reranker-base', cache_dir=Path('D:/桌面/软件杯/.cache/huggingface'), batch_size=8, max_length=512, local_files_only=True); docs=[RetrievedDocument(title='灵山大佛', content='灵山大佛是一尊高八十八米的露天青铜佛像。'), RetrievedDocument(title='餐饮', content='景区提供素斋、素面等餐饮服务。')]; results=reranker.rerank('灵山大佛有多高', docs, top_k=2); print('offline_inference_ok', [(item.document.title, item.score) for item in results])"
```

成功要求：

1. 输出包含 `offline_inference_ok`。
2. 输出两条真实浮点分数。
3. `灵山大佛` 排在 `餐饮` 前面。
4. 运行期间禁止网络也能成功。

### Step D：验证项目主链路选择真实 CrossEncoder

继续保持离线变量，然后执行：

```powershell
& 'D:\桌面\软件杯\backend\.venv\Scripts\python.exe' -c "from app.api.chat import get_cached_reranker; get_cached_reranker.cache_clear(); reranker=get_cached_reranker('BAAI/bge-reranker-base','D:/桌面/软件杯/.cache/huggingface',8,512); print(type(reranker).__name__, type(reranker.primary).__name__ if reranker.primary else None, type(reranker.fallback).__name__ if reranker.fallback else None)"
```

唯一合格的关键输出应包含：

```text
ResilientReranker CrossEncoderReranker BM25Reranker
```

如果 `primary` 输出为 `None`，则仍未完成交接目标。

### Step E：记录最终缓存状态

请记录：

1. snapshot commit 目录名。
2. snapshot 下所有必要文件名与大小。
3. 整个模型缓存总大小。
4. 在线补齐命令耗时。
5. 离线加载与推理耗时。
6. 是否使用了 `HF_HUB_DISABLE_XET=1`。

不需要运行 30 题评测，该部分由 Codex 接回后完成。

## 9. 严格禁止事项

接手 AI 不得执行：

1. 不得修改 `backend/app` 中任何代码。
2. 不得修改 `eval` 评测集或报告。
3. 不得删除完整 Hugging Face 根缓存。
4. 不得删除已有的 `bge-small-zh-v1.5`。
5. 不得重建 Chroma collection。
6. 不得修改数据库或景区资料。
7. 不得换成其他 Reranker 模型。
8. 不得切换第三方镜像或在线 API，除非用户另行明确批准。
9. 不得安装 CUDA 版 PyTorch。
10. 不得进入真实 LLM、ASR、TTS、Avatar 或前端开发。
11. 不得使用 `Stop-Process -Name python` 批量结束所有 Python；项目可能有前后端服务进程。

## 10. 完成交接的判定标准

必须同时满足：

```text
[ ] 模型仍为 BAAI/bge-reranker-base
[ ] 缓存全部位于 D:\桌面\软件杯\.cache\huggingface
[ ] 没有第三方镜像或替代模型
[ ] local_files_only=True 能加载
[ ] 离线真实 CrossEncoder 推理成功
[ ] 灵山大佛测试样例排序合理
[ ] get_cached_reranker().primary 是 CrossEncoderReranker
[ ] fallback 仍为 BM25Reranker
[ ] 没有修改项目业务代码、评测集和知识数据
[ ] 已回填本文档的执行结果
```

仅看到 `model.safetensors` 或缓存目录超过 1GB，不算完成。

## 11. 完成后 Codex 的精准续接点

其他 AI 完成下载和离线验证后，Codex 从以下位置继续：

### 当前计划状态

```text
Step 1：CrossEncoder、BM25、Resilient 模块 - 已完成
Step 2：主 RAG 链路接入与耗时记录 - 已完成
Step 3：真实模型下载与离线验证 - 等待其他 AI 完成
Step 4：30 题重排前后对比评测 - 尚未开始
Step 5：完整回归与执行记录 - 尚未完成
```

### Codex 接回后的第一件事

1. 阅读本文档“执行结果回填”。
2. 自己再运行一次离线加载和两文档 smoke test。
3. 不重复下载模型。
4. 新增：
   - `eval/scripts/reranker_regression.py`
   - `eval/reports/reranker_v0.json`
5. 用现有 `eval/testset/retrieval_test.json` 的 30 题对比：
   - Chroma 原始 Top-5
   - Chroma Top-20 经 CrossEncoder 后的 Top-5
   - Recall@1
   - Recall@5
   - MRR
   - embedding / Chroma / reranker / total 的 P50 与 P95
6. 目标 Reranker P95 `<150ms`。若超过，记录真实结果并停止，不自动换模型或减少候选数。
7. 完成后运行后端全部测试、评测测试与 compileall。
8. 更新 `docs/2026-06-11-deepseek-review-adoption-and-execution.md`。
9. 阶段结束后停止，不进入真实 LLM。

## 12. 相关文档

```text
D:\桌面\软件杯\docs\2026-06-11-reranker-implementation-plan-for-review.md
D:\桌面\软件杯\docs\2026-06-11-deepseek-review-adoption-and-execution.md
D:\桌面\软件杯\docs\CURRENT_TASK_SUMMARY.md
D:\桌面\软件杯\eval\reports\retrieval_v0.json
```

## 13. 执行结果回填（由接手 AI 填写）

### Codex 独立验收补充（2026-06-12）

接手 AI 未填写下方模板，但 Codex 已按本文档标准独立验收：

```text
模型缓存文件数：14
模型缓存总大小：1,134,374,859 bytes
.incomplete 文件：0
local_files_only=True：成功
离线真实推理：成功
测试排序：灵山大佛 > 餐饮
主链路 primary：CrossEncoderReranker
主链路 fallback：BM25Reranker
```

该下载与离线验证任务已经完成，Codex 已继续并完成 Step 4 的 30 题对比评测。

### 执行者与时间

```text
执行者：
开始时间：
结束时间：
```

### 实际执行命令

```powershell
# 在此粘贴实际执行命令
```

### 下载结果

```text
是否设置 HF_HUB_DISABLE_XET=1：
是否仍使用 Hugging Face 官方源：
在线补齐是否成功：
在线补齐耗时：
最终 snapshot commit：
最终模型缓存总大小：
最终文件清单：
```

### 离线验证结果

```text
local_files_only=True 是否成功：
offline_inference_ok 输出：
离线推理耗时：
主链路 primary 类型：
主链路 fallback 类型：
```

### 异常与说明

```text
# 如果失败，粘贴完整错误及停止位置；不要自行换模型或镜像。
```

### 最终结论

```text
[ ] 下载与离线验证完成，可以交回 Codex
[ ] 未完成，需用户决定下一步
```
