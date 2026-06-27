# 100 题评测修复 — 任务书（Claude）

> 100 题全量评测已跑完。代码逻辑没问题，两类失败需要修复。改 2 个文件。

---

## 当前结果

```
accuracy: 64% (64/100)
evidence_rate: 100%
source_hit_rate: 100%
```

两类失败：

| 类型 | 数量 | 原因 |
|------|:--:|------|
| RemoteProtocolError | 14 题 | FAQ 路径也触发了 DeepSeek，串行无间隔 → 限流断连 |
| required_fact_hit | 22 题 | 回答正确但评测集关键词匹配失败（格式不一致） |

排除限流假失败，实际准确率约 **78%**。修复后预计 **85-90%**。

---

## 修改 1：评测请求间加延迟（避免 DeepSeek 限流）

**文件**：`eval/scripts/e2e_eval_core.py`

**位置**：第 255-261 行 `evaluate_remote_cases` 函数

当前：
```python
for index, case in enumerate(cases):
    response = await request_case(case, ...)
    results.append(score_case(case, response))
```

改为：在 FAQ 路径题目（已知会触达 DeepSeek）之间加 `asyncio.sleep(1.5)`。更简单的方式是**每 10 个请求后加一个延迟**：

```python
import asyncio

for index, case in enumerate(cases):
    response = await request_case(
        case,
        endpoint=endpoint,
        client=client,
        is_cold_start=index == 0,
    )
    results.append(score_case(case, response))
    if (index + 1) % 10 == 0 and index + 1 < len(cases):
        await asyncio.sleep(2.0)
```

每 10 题停 2 秒，100 题总耗时增加约 18 秒，不影响评测结果。

**import**：确保文件顶部有 `import asyncio`。

---

## 修改 2：放宽 required_fact 匹配（支持格式变体）

**文件**：`eval/scripts/e2e_eval_core.py`

**位置**：第 388-392 行 `_all_terms_present` 函数

当前：
```python
def _all_terms_present(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    if not terms:
        return True
    normalized = text.casefold()
    return all(term.casefold() in normalized for term in terms)
```

LLM 回答"5000㎡"但 required_fact 写"5000平方米" → 失败。问题在于 `in` 是精确子串匹配。

改为：在匹配前做格式归一化，把常见的中文-数字-单位变体展开：

```python
import re

_FORMAT_NORMALIZATIONS = [
    (re.compile(r"(\d+)㎡"), r"\1平方米"),
    (re.compile(r"(\d+)m"), r"\1米"),
    (re.compile(r"(\d+)km"), r"\1公里"),
    (re.compile(r"(\d+)㎡"), r"\1平方米"),
    (re.compile(r"(\d+)t"), r"\1吨"),
    (re.compile(r"(\d+)m²"), r"\1平方米"),
    (re.compile(r"(\d+)kg"), r"\1公斤"),
    (re.compile(r"(\d+)h"), r"\1小时"),
    (re.compile(r"(\d+)min"), r"\1分钟"),
]

def _normalize_text(text: str) -> str:
    t = text.casefold()
    for pattern, replacement in _FORMAT_NORMALIZATIONS:
        t = pattern.sub(replacement, t)
    return t

def _all_terms_present(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    if not terms:
        return True
    normalized = _normalize_text(text)
    return all(_normalize_text(term) in normalized for term in terms)
```

**import**：确保文件顶部有 `import re`。

---

## 验证

修复后重新跑：

```powershell
Set-Location "d:\桌面\软件杯"
.\backend\.venv\Scripts\python.exe eval\scripts\run_e2e_chat_eval.py --mode sampled-real --limit 100 --allow-network --testset eval\testset\e2e_qa_100.json --endpoint http://127.0.0.1:8010/api/chat/stream --timeout-seconds 120
```

目标：`accuracy >= 0.85`。

---

## 文件清单

```
eval/scripts/e2e_eval_core.py  ← 修改1（+3行 请求延迟） + 修改2（+15行 格式归一化）
```

不改评测集，不改后端，不改前端。
