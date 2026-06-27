# 2026-06-17 阶段 B3.5 Qwen 图片识别超时重试计划

## 背景

B3.3 使用灵山大佛图片执行 1 次真实 Qwen 图片识别调用，结果 `ReadTimeout`。B3.4 已确认百炼 Base URL、API Key 和 `qwen3.7-plus` 模型名可用，最小文本请求成功并产生 usage。

因此，本轮只验证一个假设：B3.3 图片请求失败是否因为视觉请求读超时时间过短。

## 本轮目标

在不修改模型名、不修改图片输入格式、不批量调用的前提下，将视觉请求超时临时调大，对同一张图片只重试 1 次。

## 本轮做什么

1. 使用同一张图片：

```text
D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png
```

2. 使用同一模型：

```text
qwen3.7-plus
```

3. 临时覆盖超时配置：

```text
VISION_READ_TIMEOUT_SECONDS=60
VISION_TOTAL_TIMEOUT_SECONDS=90
```

4. 执行 1 次真实 Qwen 图片识别调用。
5. 输出仍写入：

```text
eval/reports/qwen_vision_smoke.json
```

## 本轮不做什么

1. 不修改 `backend/.env` 中的 API Key。
2. 不永久修改 `.env` 配置。
3. 不更换模型名。
4. 不改图片请求格式。
5. 不批量调用。
6. 不把视觉识别结果当作景区事实。

## 成功判定

1. `ok=true`。
2. `provider=qwen`。
3. `error_type=null`。
4. `retrieval_query` 非空。
5. 至少有一个结构化视觉信号：`scene_summary`、`detected_text`、`candidate_attractions`、`visual_tags` 或 `query_hints`。

## 失败后的判断

如果本轮仍失败，则不再继续盲目重试，应进入：

1. 百炼视觉模型名核对。
2. 图片输入格式对齐官方视觉示例。
3. 必要时改用更明确的视觉理解模型。
