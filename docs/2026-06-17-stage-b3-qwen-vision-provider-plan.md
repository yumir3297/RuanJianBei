# 2026-06-17 阶段 B3.2 Qwen 图片识别 Provider 接入计划

## 背景

B3.1 已完成厂商无关的图片识别 Provider 骨架。用户已确认图片识别供应商使用千问，并已在 `backend/.env` 中配置 `VISION_PROVIDER=qwen`、`VISION_API_KEY`、`VISION_BASE_URL`、`VISION_MODEL`。

## 本轮目标

接入可真实调用的 Qwen 图片识别 Provider，并提供后端图片分析接口，使游客图片可以被识别为 RAG 检索线索。

## 本轮做什么

1. 在 `Settings` 中读取 `VISION_*` 配置。
2. 新增 `QwenVisionService`，通过 OpenAI-compatible Chat Completions 方式请求百炼视觉模型。
3. 图片以 base64 data URL 形式发送给视觉模型。
4. 要求视觉模型返回 JSON，字段包括：
   - `scene_summary`
   - `detected_text`
   - `candidate_attractions`
   - `visual_tags`
   - `query_hints`
   - `confidence`
5. 新增 `POST /api/vision/analyze`，接收图片文件和可选问题，返回识别结果与 `retrieval_query`。
6. 新增单元测试，使用 `httpx.MockTransport` 验证请求格式、响应解析和错误降级。
7. 更新当前任务摘要和实施报告。

## 本轮不做什么

1. 不直接跑批量真实图片识别。
2. 不把图片识别结果写入知识库。
3. 不修改数据库 Schema。
4. 不修改现有 `POST /api/chat/stream`。
5. 不让视觉模型直接回答景区事实。
6. 不接前端上传页面。
7. 不保存游客上传原图。

## 风险控制

1. 若 `VISION_*` 配置不完整，接口返回 Stub/降级结果，不发起真实请求。
2. 若 Qwen 返回非 JSON 文本，后端会尽量提取文本并转成检索线索。
3. 若 Provider 网络异常，后端返回低置信度降级结果，不影响原文本问答。
4. 自动化测试只使用 Mock，不消耗百炼额度。

## 正确业务链路

```text
游客上传图片
-> Qwen 视觉模型分析图片
-> 后端生成 retrieval_query
-> 后续用 retrieval_query 进入 RAG
-> 最终讲解仍必须引用官方资料证据
```

## 完成标准

1. Qwen Provider 单元测试通过。
2. 图片分析 API 单元测试通过。
3. 后端完整回归通过。
4. 编译检查通过。
5. 报告记录本轮未发生真实批量调用。
