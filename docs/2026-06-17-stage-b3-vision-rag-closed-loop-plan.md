# 2026-06-17 阶段 B3.6 图片识别接入 RAG 闭环计划

## 背景

B3.5 已证明 Qwen 图片识别可以成功处理灵山大佛图片，并生成 `retrieval_query`。当前还缺最后一段业务闭环：将图片识别结果送入官方资料 RAG，再由现有 QA Pipeline 输出带 `[证据N]` 的景区讲解。

## 本轮目标

跑通最小闭环：

```text
图片
-> Qwen 图片识别
-> retrieval_query
-> 官方资料 RAG 检索
-> DeepSeek/文本问答链路生成带证据答案
```

## 本轮做什么

1. 新增受控闭环脚本：`eval/scripts/vision_rag_smoke.py`。
2. 脚本从 `backend/.env` 读取现有 DeepSeek 与 Qwen 配置。
3. 脚本必须显式传入 `--image`。
4. 脚本必须显式传入 `--allow-network` 才会发起真实调用。
5. 先调用 `QwenVisionService` 得到视觉识别结果。
6. 再把 `retrieval_query` 拼成 QA 查询，送入现有 `QAPipeline`。
7. 报告记录：
   - 视觉识别结果
   - `retrieval_query`
   - QA 查询
   - 最终答案
   - sources 和 evidence_id
   - 事件序列
   - 是否包含 `[证据N]`
8. 输出报告：`eval/reports/vision_rag_smoke.json`。

## 本轮不做什么

1. 不接前端上传入口。
2. 不修改 `POST /api/chat/stream`。
3. 不保存游客原图。
4. 不把 Qwen 识别内容写入知识库。
5. 不让 Qwen 直接回答景区事实。
6. 不批量调用图片识别或文本问答。

## 成功判定

1. Qwen 图片识别成功，`vision_ok=true`。
2. `retrieval_query` 非空。
3. QA Pipeline 返回 `sources`。
4. 最终答案非空。
5. 最终答案包含 `[证据N]`。
6. 流式事件包含 `done`。

## 风险控制

1. 若 Qwen 失败，不继续调用 QA Pipeline。
2. 若 RAG 无证据，报告失败并记录 sources 为空。
3. 若 DeepSeek 超时，报告保留降级/错误信息，不重试。
4. 每次真实闭环烟测只执行 1 张图片。
