# 2026-06-17 阶段 B3.1 图片识别 Provider 骨架实施报告

## 本轮目标

在不绑定真实厂商、不新增外部依赖、不修改公共 API 的前提下，先为后续图片识别接入建立稳定的服务层骨架。

## 已完成内容

1. 新增 `backend/app/services/vision/` 目录。
2. 新增 `BaseVisionService` 抽象接口。
3. 新增 `VisionResult` 数据结构。
4. 新增 `StubVisionService`，用于本地开发和自动化测试。
5. 新增 `test_vision_service.py`，覆盖检索线索生成和 Stub 非权威结果。
6. 更新 `docs/CURRENT_TASK_SUMMARY.md`，记录 B3.1 状态。

## 关键设计

`VisionResult` 当前包含：

1. `scene_summary`：图片场景描述。
2. `detected_text`：图片 OCR 文本。
3. `candidate_attractions`：候选景点名称。
4. `visual_tags`：视觉标签。
5. `query_hints`：额外检索提示。
6. `confidence`：模型置信度。
7. `provider`：模型供应商标识。
8. `raw`：原始响应摘要或调试字段。

`VisionResult.as_retrieval_query()` 会把视觉结果和用户问题合并为 RAG 检索查询。这个设计明确保证：图片识别结果只作为检索线索，不作为最终事实来源。

## 本轮未做

1. 未接入阿里云百炼或智谱真实 API。
2. 未新增 API Key、Base URL 或模型名配置。
3. 未新增 HTTP 上传接口。
4. 未修改数据库 Schema。
5. 未修改前端。
6. 未保存游客上传图片。
7. 未让图片识别结果绕过 RAG 证据链回答。

## 审查与修复

首次测试时发现两个测试写法问题：

1. 字符串 `count` 会把“疑似灵山大佛广场”中的子串也算入“灵山大佛”次数。
2. 当前项目未安装 `pytest-asyncio`，不能使用 `@pytest.mark.asyncio`。

已修复为：

1. 按 `；` 分隔检索查询后检查精确项去重。
2. 使用 `asyncio.run()` 执行 Stub 异步方法，避免新增依赖。

## 验证结果

```text
vision 专项测试: 2 passed
后端完整回归:   61 passed
compileall:     passed
```

## 下一步建议

下一步进入 B3.2 前需要确认真实图片识别 Provider：

1. 阿里云百炼 Qwen 视觉理解。
2. 智谱 GLM-5V-Turbo。

确认后再新增真实 Provider 配置、HTTP 图片上传接口和前端拍照/上传入口。真实 Provider 接入后仍必须保持“图片识别 -> 检索线索 -> RAG 证据回答”的链路，不允许图片模型直接编造景区事实。
