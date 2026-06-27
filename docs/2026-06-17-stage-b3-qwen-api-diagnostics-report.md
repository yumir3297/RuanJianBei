# 2026-06-17 阶段 B3.4 Qwen API 可用性诊断报告

## 本轮目标

在 B3.3 图片烟测 `ReadTimeout` 且用户反馈工作台似乎没有 token 消耗后，先不继续发送图片，而是诊断百炼 Qwen API 的基础可用性。

## 执行内容

使用脚本：

```text
eval/scripts/qwen_api_diagnostics.py
```

执行命令：

```powershell
backend\.venv\Scripts\python.exe eval\scripts\qwen_api_diagnostics.py --allow-network
```

本轮只做两项低成本检查：

1. `GET /models`
2. `POST /chat/completions`，文本请求，`max_tokens=1`

没有发送图片，没有重试图片识别。

## 诊断结果

```text
ok = true
provider = qwen
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
model = qwen3.7-plus
```

`GET /models`：

```text
status_code = 200
model_count = 219
configured_model_listed = true
```

`POST /chat/completions`：

```text
status_code = 200
content_preview = OK
prompt_tokens = 13
completion_tokens = 34
total_tokens = 47
```

报告文件：

```text
eval/reports/qwen_api_diagnostics.json
```

## 结论

百炼 OpenAI-compatible Base URL、API Key 和 `qwen3.7-plus` 模型名均可用。B3.3 的图片烟测失败不应继续归因于基础配置错误。

更可能的问题集中在：

1. 图片请求耗时超过当前读超时。
2. 图片输入格式与当前模型的视觉路径兼容性需要进一步验证。
3. `qwen3.7-plus` 虽能完成文本请求，但图片处理可能需要更长超时或更明确的视觉模型/参数。

## 下一步建议

下一步不建议再做普通文本诊断，应进入 B3.5：图片请求最小化诊断。

建议顺序：

1. 将视觉请求超时调大到 `VISION_READ_TIMEOUT_SECONDS=60`、`VISION_TOTAL_TIMEOUT_SECONDS=90`。
2. 仍使用同一张灵山大佛图片，只重试 1 次图片识别。
3. 如果仍失败，再将请求格式调整为更贴近百炼视觉示例，或回到控制台确认是否有专门的视觉模型名。

所有重试仍需用户确认后再执行。
