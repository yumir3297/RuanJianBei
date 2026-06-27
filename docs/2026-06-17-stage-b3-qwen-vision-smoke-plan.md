# 2026-06-17 阶段 B3.3 Qwen 单图真实烟测计划

## 背景

B3.2 已完成 Qwen 图片识别 Provider 后端接入，并新增 `POST /api/vision/analyze`。自动化测试均使用 Mock，没有消耗百炼额度。当前项目目录内未发现适合作为景区业务烟测的图片文件。

## 本阶段目标

使用 1 张用户指定的本地图片，执行 1 次真实 Qwen 图片识别调用，验证：

1. `backend/.env` 中的 `VISION_*` 配置可用。
2. Qwen 视觉模型能真实接收图片并返回结果。
3. 后端能将视觉结果转换为 `retrieval_query`。
4. 识别结果只作为 RAG 检索线索，不作为景区事实来源。

## 本轮先做

1. 新增受控烟测脚本：`eval/scripts/qwen_vision_smoke.py`。
2. 脚本必须显式传入 `--image`。
3. 脚本必须显式传入 `--allow-network` 才会发起真实百炼调用。
4. 脚本输出 JSON 报告到 `eval/reports/qwen_vision_smoke.json`。
5. 先进行脚本编译检查，不触发真实调用。

## 本轮暂不做

1. 不使用虚拟环境依赖包自带示例图片作为业务烟测图。
2. 不批量识别图片。
3. 不接前端上传入口。
4. 不把图片识别结果写入知识库。
5. 不绕过 RAG 证据链直接回答景区事实。

## 真实调用前置条件

用户需要提供或确认：

1. 一张本地测试图片绝对路径。
2. 允许进行 1 次真实百炼 Qwen 图片识别调用。

## 预期命令

```powershell
backend\.venv\Scripts\python.exe eval\scripts\qwen_vision_smoke.py `
  --image "D:\path\to\image.jpg" `
  --question "这张图片可能对应景区哪个位置？" `
  --allow-network
```

## 完成标准

1. 脚本能生成报告。
2. 报告中 `ok=true`。
3. `provider=qwen`。
4. `retrieval_query` 非空。
5. 若调用失败，报告记录错误类型和错误信息，不扩大调用次数。
