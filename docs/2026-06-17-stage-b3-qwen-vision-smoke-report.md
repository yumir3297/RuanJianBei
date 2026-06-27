# 2026-06-17 阶段 B3.3 Qwen 单图真实烟测报告

## 本轮目标

使用用户提供的 1 张本地图片执行 1 次真实 Qwen 图片识别调用，验证百炼视觉模型是否能完成图片识别并返回可用于 RAG 的检索线索。

## 测试图片

```text
D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png
```

图片内容为清晰的灵山大佛地标图，适合作为首次业务烟测样本。

## 执行命令

```powershell
backend\.venv\Scripts\python.exe eval\scripts\qwen_vision_smoke.py `
  --image "D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png" `
  --question "这张图片可能对应景区哪个位置？请提取可用于景区资料检索的线索。" `
  --allow-network
```

## 真实调用结果

本轮已执行 1 次真实百炼 Qwen 图片识别调用，但烟测未通过。

```text
ok = false
provider = qwen
model = qwen3.7-plus
confidence = 0.0
error_type = ReadTimeout
error_message = Qwen vision request timed out.
elapsed_ms = 22692.21
```

报告文件：

```text
eval/reports/qwen_vision_smoke.json
```

## 失败原因

Qwen Provider 在等待百炼响应时触发 `ReadTimeout`，后端按设计返回了低置信度降级结果：

```text
图片识别服务暂时不可用，当前图片只能作为低置信度检索线索。
```

这说明：

1. 脚本已真实发起百炼调用。
2. 当前请求未获得有效视觉识别内容。
3. 降级链路生效，没有把失败结果伪装成景区事实。
4. 原脚本曾把 fallback retrieval_query 误判为 `ok=true`，已修正为 `ok=false`。

## 已完成修复

1. `QwenVisionService` 降级结果现在会记录 `error_type` 和安全错误信息。
2. `qwen_vision_smoke.py` 只有在无 Provider 错误且有结构化视觉线索时才判定 `ok=true`。
3. 已修正 `eval/reports/qwen_vision_smoke.json`，避免误报成功。
4. 新增 Mock 测试覆盖 Provider 超时降级记录。

## 验证结果

```text
B3 专项测试: 7 passed
后端完整回归: 66 passed
compileall:   passed
```

## 下一步选项

在不擅自扩大真实调用次数的前提下，下一步需要用户确认二选一：

1. **保留 `qwen3.7-plus`，调大视觉请求超时后再重试 1 次。**
   适合判断这次是否只是冷启动或网络慢。

2. **改用百炼控制台中更明确的视觉理解模型名后再重试 1 次。**
   适合排查 `qwen3.7-plus` 是否不是当前账号/接口下最合适的图片理解模型。

建议先执行选项 1：将 `VISION_READ_TIMEOUT_SECONDS` 调到 `60`，`VISION_TOTAL_TIMEOUT_SECONDS` 调到 `90`，只重试同一张图片 1 次。如果仍失败，再回到百炼控制台核对模型名。
