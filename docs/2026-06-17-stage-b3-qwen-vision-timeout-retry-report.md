# 2026-06-17 阶段 B3.5 Qwen 图片识别超时重试报告

## 本轮目标

验证 B3.3 图片识别失败是否主要由视觉请求读超时过短导致。B3.4 已确认百炼 Base URL、API Key 和 `qwen3.7-plus` 模型名可用，因此本轮只临时调大超时，对同一张图片重试 1 次。

## 执行方式

本轮未永久修改 `backend/.env`，只在命令执行时临时覆盖：

```text
VISION_READ_TIMEOUT_SECONDS=60
VISION_TOTAL_TIMEOUT_SECONDS=90
```

执行图片：

```text
D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png
```

执行命令：

```powershell
$env:VISION_READ_TIMEOUT_SECONDS='60'
$env:VISION_TOTAL_TIMEOUT_SECONDS='90'
backend\.venv\Scripts\python.exe eval\scripts\qwen_vision_smoke.py `
  --image "D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png" `
  --question "这张图片可能对应景区哪个位置？请提取可用于景区资料检索的线索。" `
  --allow-network
```

## 真实调用结果

本轮执行 1 次真实 Qwen 图片识别调用，烟测通过。

```text
ok = true
provider = qwen
model = qwen3.7-plus
elapsed_ms = 20686.45
confidence = 0.95
error_type = null
```

报告文件：

```text
eval/reports/qwen_vision_smoke.json
```

## 识别结果摘要

Qwen 成功识别出图片中的核心视觉元素：

1. 候选景点：`灵山大佛`、`灵山胜境`、`祥符禅寺`、`无锡灵山景区`。
2. 视觉标签：`大佛`、`青铜佛像`、`释迦牟尼像`、`寺庙建筑`、`红墙红瓦`、`青山背景`、`佛教文化`、`透视构图`。
3. 场景描述：图片展示一尊巨大的青铜立佛，前景有红瓦寺庙建筑和较小佛像。

这些内容已合并成 `retrieval_query`，用于后续 RAG 检索。

## 合规说明

图片识别结果只作为检索线索，不作为景区事实来源。后续如果要向游客讲解灵山大佛高度、历史、位置或文化内涵，仍必须进入官方资料 RAG 并输出 `[证据N]`。

## 验证结果

```text
B3 专项测试: 7 passed
compileall:   passed
```

## 结论

B3.3 的失败主要是超时配置过短导致。调大视觉请求超时后，Qwen 图片识别闭环可以成功运行，满足“真实多模态大模型参与业务”的关键技术前提。

## 下一步建议

进入 B3.6：将图片识别返回的 `retrieval_query` 接入后端 RAG 问答闭环。

建议先做后端最小闭环：

1. 新增一个受控接口或脚本，把 `retrieval_query` 送入现有 QA Pipeline。
2. 确认最终回答引用官方资料 `[证据N]`。
3. 不让 Qwen 视觉结果直接回答景区事实。
4. 测通后再接前端图片上传入口。
