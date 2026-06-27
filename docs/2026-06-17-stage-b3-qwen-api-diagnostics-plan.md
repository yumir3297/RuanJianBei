# 2026-06-17 阶段 B3.4 Qwen API 可用性诊断计划

## 背景

B3.3 已对灵山大佛图片执行 1 次真实 Qwen 图片识别调用，但请求最终 `ReadTimeout`。用户在 Qwen 工作台未看到 token 额度消耗，因此需要判断问题到底来自：

1. API Key 或权限。
2. Base URL。
3. 模型名。
4. 图片输入格式。
5. 网络或超时时间。

## 本轮目标

先不重试图片识别，只做低成本 API 可用性诊断，确认 `backend/.env` 中的 Qwen 配置是否能完成最小请求。

## 本轮做什么

1. 新增受控诊断脚本：`eval/scripts/qwen_api_diagnostics.py`。
2. 脚本从 `backend/.env` 读取 `VISION_*` 配置。
3. 脚本默认不联网，必须传 `--allow-network` 才会发请求。
4. 诊断 `GET /models`，用于观察兼容接口和鉴权是否可达。
5. 诊断 `POST /chat/completions`，使用 `max_tokens=1` 的最小文本请求验证模型名是否可调用。
6. 生成脱敏报告：`eval/reports/qwen_api_diagnostics.json`。

## 本轮不做什么

1. 不再发送图片。
2. 不做第二次图片识别重试。
3. 不修改 `.env` 中的 API Key。
4. 不修改模型供应商。
5. 不接前端上传入口。
6. 不把任何返回内容当作景区事实。

## 完成标准

1. 诊断脚本编译通过。
2. 未授权联网时不会写正式报告。
3. 真实诊断报告记录 HTTP 状态、错误类型、模型名和最小请求 usage。
4. 根据诊断结果决定下一步是调超时、换模型名，还是修图片输入格式。
