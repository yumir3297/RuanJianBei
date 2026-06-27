# 2026-06-17 阶段 B3.6 图片识别接入 RAG 闭环实施报告

## 本轮目标

将 B3.5 已验证成功的 Qwen 图片识别结果接入官方资料问答链路，完成最小多模态业务闭环：

```text
图片
-> Qwen 图片识别
-> retrieval_query
-> 官方资料 RAG/FAQ 检索
-> 带 [证据N] 的景区讲解
```

## 已完成内容

1. 新增受控闭环脚本：`eval/scripts/vision_rag_smoke.py`。
2. 新增执行计划：`docs/2026-06-17-stage-b3-vision-rag-closed-loop-plan.md`。
3. 脚本要求显式传入 `--image` 和 `--allow-network` 才会真实调用。
4. 脚本先调用 `QwenVisionService` 分析图片。
5. 脚本将 `retrieval_query` 拼入 QA 查询，并明确标注“图片识别线索仅用于检索官方资料，不作为事实来源”。
6. 脚本复用现有 `QAPipeline`，不新造问答逻辑。
7. 脚本输出报告：`eval/reports/vision_rag_smoke.json`。

## 本轮真实烟测

图片：

```text
D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png
```

执行命令：

```powershell
backend\.venv\Scripts\python.exe eval\scripts\vision_rag_smoke.py `
  --image "D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png" `
  --question "请根据这张图片识别出的线索，基于官方资料介绍它最可能对应的景区景点。" `
  --allow-network
```

## 结果摘要

```text
overall_ok = true
vision_ok = true
qa_ok = true
```

Qwen 图片识别结果：

```text
model = qwen3.7-plus
confidence = 0.95
elapsed_ms = 26007.04
candidate_attractions = 无锡灵山大佛、灵山胜境、祥符禅寺
```

QA 闭环结果：

```text
elapsed_ms = 32624.87
evidence_ids = 证据1
has_inline_citation = true
event_types = context, status, sources, text, followups, done
```

最终回答：

```text
灵山大佛佛像高88m（主体高度79m+莲花瓣高度9m），含台基总高101.5m，耗铜量达725吨，由2000块铸铜面板拼接而成，[证据1]
```

来源：

```text
灵山胜境 景点结构化数据集.docx - 灵山胜境 / 灵山大佛
```

## 重要说明

本轮 QA 命中了现有 FAQ/快速证据路径，因此最终回答没有再触发 DeepSeek 生成，而是直接返回官方资料来源下的结构化答案。这个结果仍满足本轮目标：图片识别结果已成功引导到官方资料证据回答，且最终答案包含 `[证据1]`。

如果后续需要展示“图片识别 + DeepSeek 生成式讲解”路径，可在 B3.7 使用更开放的问题或禁用 FAQ 快路径做单独烟测；这需要再次确认调用次数。

## 合规说明

1. Qwen 视觉输出只作为检索线索。
2. 景区事实来自官方资料包构建的 FAQ/RAG 证据。
3. 最终答案包含证据编号。
4. 本轮未保存游客原图，未写入知识库。
5. 未修改现有 `POST /api/chat/stream`。

## 验证结果

```text
后端完整回归: 66 passed
compileall:   passed
```

## 结论

B3.6 已完成多模态最小业务闭环。当前系统已经可以证明：

```text
游客图片输入
-> 真实多模态大模型 Qwen 参与识别
-> 识别线索进入官方资料检索
-> 输出带证据的景区讲解
```

下一步建议进入前端接入阶段：在游客端增加图片上传入口，并复用后端 `POST /api/vision/analyze` 与后续 RAG 闭环逻辑。
