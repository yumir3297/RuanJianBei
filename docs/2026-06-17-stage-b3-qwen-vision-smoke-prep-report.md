# 2026-06-17 阶段 B3.3 Qwen 单图真实烟测准备报告

## 本轮目标

为 1 张图片的真实 Qwen 视觉识别烟测做好受控执行准备，确保不会误触发百炼调用或误写正式报告。

## 已完成内容

1. 新增计划文档：`docs/2026-06-17-stage-b3-qwen-vision-smoke-plan.md`。
2. 新增烟测脚本：`eval/scripts/qwen_vision_smoke.py`。
3. 搜索项目目录内图片，未发现适合景区业务烟测的图片。
4. 脚本要求显式传入 `--image`。
5. 脚本要求显式传入 `--allow-network` 才会真实调用百炼。
6. 脚本默认输出报告：`eval/reports/qwen_vision_smoke.json`。
7. 修正守门逻辑：未传 `--allow-network` 或图片不存在时，不写正式报告。

## 当前未执行

1. 未进行真实 Qwen 网络调用。
2. 未消耗百炼额度。
3. 未生成正式烟测报告。
4. 未接前端图片上传入口。
5. 未把图片结果接入聊天 RAG 主链路。

## 验证结果

```text
脚本编译检查: passed
后端完整回归: 65 passed
守门验证:     未传 --allow-network 时拒绝调用，且不写正式报告
```

## 真实烟测命令模板

```powershell
backend\.venv\Scripts\python.exe eval\scripts\qwen_vision_smoke.py `
  --image "D:\你的图片路径\test.jpg" `
  --question "这张图片可能对应景区哪个位置？" `
  --allow-network
```

## 下一步需要用户提供

1. 一张本地测试图片的绝对路径。
2. 明确允许进行 1 次真实百炼 Qwen 图片识别调用。

收到后只执行 1 次真实调用，并将结果写入 `eval/reports/qwen_vision_smoke.json` 和新的 B3.3 真实烟测报告。
