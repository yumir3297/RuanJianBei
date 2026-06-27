# 2026-06-17 阶段 B3.2 Qwen 图片识别 Provider 接入报告

## 本轮目标

在用户确认使用千问并完成 `backend/.env` 视觉配置后，将 B3.1 的厂商无关 Vision Provider 骨架扩展为可调用百炼 Qwen 视觉模型的后端能力。

## 已完成内容

1. 在 `Settings` 中新增 `VISION_*` 配置读取。
2. 新增 `QwenVisionService`，支持 OpenAI-compatible Chat Completions 图片输入。
3. 新增 `POST /api/vision/analyze` 后端接口。
4. 新增 `VisionAnalyzeResponse` 响应结构。
5. 更新 `backend/.env.example`，加入视觉配置示例。
6. 在应用生命周期中关闭缓存的 Vision Provider 客户端。
7. 新增 Qwen Provider 单元测试和 Vision API 单元测试。

## 接口说明

接口：

```text
POST /api/vision/analyze
```

请求方式：

1. 请求体直接传图片二进制内容。
2. `Content-Type` 设置为图片类型，例如 `image/jpeg` 或 `image/png`。
3. 可选 query 参数：
   - `question`：用户对图片的自然语言问题。
   - `filename`：图片文件名，用于调试和检索线索。

响应字段：

1. `scene_summary`
2. `detected_text`
3. `candidate_attractions`
4. `visual_tags`
5. `query_hints`
6. `retrieval_query`
7. `confidence`
8. `provider`

## Qwen Provider 设计

`QwenVisionService` 会把图片转为 base64 data URL，并向百炼 OpenAI-compatible 地址发送非流式请求。

发送给模型的系统提示明确要求：

1. 只输出 JSON。
2. 图片识别结果只能作为检索线索。
3. 不把视觉模型输出当作景区事实来源。
4. 必须返回可审计字段，例如候选景点、OCR 文本、视觉标签和置信度。

如果模型返回非 JSON 文本，后端会尽量解析 JSON；解析失败时会把文本作为低结构化 `scene_summary`，避免接口崩溃。

## 本轮没有做

1. 没有执行真实 Qwen 网络调用。
2. 没有批量识别图片。
3. 没有接前端上传入口。
4. 没有修改 `POST /api/chat/stream`。
5. 没有保存游客上传原图。
6. 没有把图片识别结果写入知识库。
7. 没有让视觉模型直接回答景区事实。

## 验证结果

```text
B3 相关专项测试: 6 passed
后端完整回归:   65 passed
路由导入检查:   /api/vision/analyze 已注册
compileall:     passed
```

自动化测试使用 `httpx.MockTransport` 模拟百炼响应，没有消耗 API 额度。

## 下一步建议

下一步进入 B3.3：使用 1 张真实图片做 Qwen 图片识别烟测。

执行前需要用户提供或指定：

1. 一张本地测试图片路径。
2. 是否允许进行 1 次真实百炼调用。

烟测通过后，再接前端上传入口，并把 `retrieval_query` 接入后续 RAG 问答链路。
