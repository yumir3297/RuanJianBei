# Embedding 模型离线加载修复方案

> 编写时间：2026-06-15。修复 SentenceTransformerEmbedder 在离线环境下加载失败导致退化到 SQL 检索的问题。

---

## 一、问题诊断

### 1.1 现象

服务启动或问答请求时，`SentenceTransformerEmbedder` 初始化失败 → `chat.py` 的 `try/except` 捕获异常 → 全链路退化到 SQL LIKE 检索（`RepositoryBackedRAGService`），Chroma 向量检索完全不可用。

### 1.2 根因

**不对称修复**：

| 组件 | `local_files_only` | 效果 |
|------|:--:|------|
| `CrossEncoderReranker` | ✅ `True` | 离线可用，直接读 D 盘 `model.safetensors` |
| `SentenceTransformerEmbedder` | ❌ 未设置 | 离线时初始化失败 |

`sentence_transformers` 库的 `SentenceTransformer` 和 `CrossEncoder` 默认都会先尝试连接 Hugging Face Hub 检查更新。`CrossEncoderReranker` 已经传了 `local_files_only=True`（在 `cross_encoder_reranker.py:48`），但 `SentenceTransformerEmbedder` 没有。

**调用链**：

```
embedder.py:48  →  SentenceTransformer(model_name, cache_folder=...)
                         没有 local_files_only=True
                         → 尝试联网检查 Hub
                         → 网络不通 → 抛异常
                         → chat.py:114 try/except 捕获
                         → rag_service = fallback_rag (SQL)
```

### 1.3 本地模型文件状态（已验证）

D 盘缓存目录 `D:\桌面\软件杯\.cache\huggingface` 下两份模型完整就绪：

```
BAAI/bge-small-zh-v1.5/  (Embedding)
  model.safetensors         ← 权重完整
  config.json / tokenizer.json / vocab.txt ...
  
BAAI/bge-reranker-base/   (Reranker)  
  model.safetensors         ← 权重完整
  config.json / tokenizer.json ...
```

文件齐全，无需重新下载。只需让 `SentenceTransformer` 信任本地缓存即可。

---

## 二、修复方案（最简可用，3 处改动）

### 2.1 改动 1：`embedder.py` — 增加 `local_files_only` 参数

**文件**：`backend/app/services/rag/embedder.py`

**现状**：
```python
class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, cache_dir: Path | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise AppError(...)
        self._model = SentenceTransformer(
            model_name,
            cache_folder=str(self.cache_dir) if self.cache_dir is not None else None,
        )
```

**修改后**：
```python
class SentenceTransformerEmbedder:
    def __init__(
        self,
        model_name: str,
        cache_dir: Path | None = None,
        *,
        local_files_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise AppError(
                "sentence-transformers is not installed. Install it before building the RAG index.",
                error_code="rag_dependency_missing",
                status_code=503,
            ) from exc

        self._model = SentenceTransformer(
            model_name,
            cache_folder=str(self.cache_dir) if self.cache_dir is not None else None,
            local_files_only=local_files_only,
        )
```

改动要点：
1. 新增关键字参数 `local_files_only: bool = False`（默认 `False` 保持向后兼容，让 `admin.py` 的首次索引构建仍可下载模型）
2. 把 `local_files_only` 传给 `SentenceTransformer()`
3. 代码风格与 `CrossEncoderReranker.__init__` 完全一致

### 2.2 改动 2：`chat.py` — 运行时传 `local_files_only=True`

**文件**：`backend/app/api/chat.py`

**现状**：
```python
@lru_cache(maxsize=2)
def get_cached_embedder(model_name: str, cache_dir: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(model_name, cache_dir=Path(cache_dir))
```

**修改后**：
```python
@lru_cache(maxsize=2)
def get_cached_embedder(model_name: str, cache_dir: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(model_name, cache_dir=Path(cache_dir), local_files_only=True)
```

仅加一个参数 `local_files_only=True`。与同一文件中 `get_cached_reranker` 在 L70 传递 `local_files_only=True` 的做法完全对称。

### 2.3 改动 3：`admin.py` — 索引构建保持允许下载（默认值 `False`）

**文件**：`backend/app/api/admin.py`

**不修改**。

理由：
- `admin.py:93` 的 `build-rag-index` 端点是**首次部署**时调用的，需要从 Hugging Face 下载模型
- `SentenceTransformerEmbedder` 的 `local_files_only` 默认值已经是 `False`，不需要改
- 模型下载成功后，后续服务重启时 `lru_cache` 的 embedder 实例已经是 `local_files_only=True`（来自 `chat.py`），互不干扰

---

## 三、为什么这是最简方案

### 与其他候选方案的对比

| 候选 | 做法 | 问题 |
|------|------|------|
| ~~环境变量 `HF_HUB_OFFLINE=1`~~ | 在 `.env` 或启动脚本中设置 | 会**同时影响** admin 的首次下载和 Reranker，粒度太粗 |
| ~~新增配置项 `embedding_local_files_only`~~ | 在 `config.py` 加一个字段 | 当前 Reranker 也没走配置项（直接写死在 `chat.py:70`），新增配置项属于过度设计 |
| ✅ **本方案**：参数传递 | `chat.py` 传 `True`，`admin.py` 用默认 `False` | 改动最小、语义最清晰，与 Reranker 已建立的模式一致 |

### 边界情况

| 场景 | 行为 |
|------|------|
| 启动时模型已在 D 盘 | `SentenceTransformer` 直接加载 `.safetensors`，不联网 |
| 启动时模型不在 D 盘 | `SentenceTransformer` 抛 `LocalEntryNotFoundError` → `chat.py:114` 捕获 → fallback 到 SQL |
| 首次部署（admin build-rag-index） | `local_files_only=False`（默认），允许下载 → 下载到 D 盘 → 后续启动可离线 |
| 网络恢复后重新 build-rag-index | 仍可从 Hugging Face 拉取最新版本 |

---

## 四、不影响的部分

| 组件 | 影响 |
|------|:--:|
| `CrossEncoderReranker` | ❌ 已有 `local_files_only=True`，不变 |
| FAQ 匹配 | ❌ 不经过 Embedder |
| SQL fallback（`RepositoryBackedRAGService`） | ❌ 不经过 Embedder |
| 评测脚本（`eval/` 下的 `retrieval_regression.py` 等） | ⚠️ 需同步改为 `local_files_only=True`（如果需要离线评测） |
| 前端 | ❌ 无影响 |

### 评测脚本同步修复

**文件**：`eval/scripts/retrieval_regression.py` 和 `eval/scripts/reranker_regression.py`

这两个脚本在构造 `SentenceTransformerEmbedder` 时也需要同步改为 `local_files_only=True`：

```python
# 现状
embedder = SentenceTransformerEmbedder(model_name, cache_dir=cache_dir)

# 修改后
embedder = SentenceTransformerEmbedder(model_name, cache_dir=cache_dir, local_files_only=True)
```

---

## 五、改动清单

```
修改文件 (3):
├── backend/app/services/rag/embedder.py       # 增加 local_files_only 参数
├── backend/app/api/chat.py                    # 传 local_files_only=True
└── eval/scripts/retrieval_regression.py       # 同步离线模式（如果涉及）

不修改 (确认)：
├── backend/app/api/admin.py                   # 首次构建仍需允许下载
├── backend/app/core/config.py                 # 不需要新增配置项
├── backend/.env                               # 不需要设置环境变量
└── backend/requirements.txt                   # 不需要新增依赖
```

---

## 六、验证步骤

```powershell
# 1. 确认模型文件在 D 盘
dir "D:\桌面\软件杯\.cache\huggingface\models--BAAI--bge-small-zh-v1.5\snapshots\*\model.safetensors"

# 2. 离线 smoke test
Set-Location "d:\桌面\软件杯\backend"
$env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe -c "
from app.services.rag.embedder import SentenceTransformerEmbedder
from pathlib import Path
e = SentenceTransformerEmbedder('BAAI/bge-small-zh-v1.5', cache_dir=Path('../.cache/huggingface'), local_files_only=True)
v = e.embed('灵山大佛')
print(f'OK: {len(v)} dims')
"

# 3. 编译检查
.\.venv\Scripts\python.exe -m compileall .\app .\main.py -q

# 4. 后端回归测试
.\.venv\Scripts\python.exe -m pytest .\app\tests -q --tb=short --ignore=app/tests/test_data_import.py --ignore=app/tests/test_faq_perf.py --ignore=app/tests/test_quick_select.py

# 5. 恢复环境变量
$env:HF_HUB_OFFLINE = ""
```

验收标准：
1. `compileall` 通过
2. 后端测试全部通过（26+ passed，不退化）
3. 离线 smoke test 输出 `OK: 512 dims`（或实际维度）
4. 离线条件下 Chroma 检索正常工作（不降级到 SQL）

---

## 七、执行约束

1. **不改模型**（BAAI/bge-small-zh-v1.5 保持不变）
2. **不改 Chroma 索引**（不重建）
3. **不改 Reranker**（已有 offline 保护）
4. **不新增配置项**（参数传递，与 Reranker 模式一致）
5. **不动数据库**（无 Schema 变更）
6. **如果验证失败**（模型文件缺失或损坏），立即停止并向用户报告，不擅自下载或换模型
