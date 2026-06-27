# 2026-06-16 阶段 B1 DeepSeek 证据链问答实施报告

## 本阶段目标

把原有“检索 + 占位回答”升级为“检索 + 真实 DeepSeek 文本大模型 + 强制证据链”的最小闭环，并保持前后端现有 SSE 协议可用。

## 本次完成内容

1. 后端接入 OpenAI-compatible 流式 LLM 服务，当前配置为 DeepSeek `deepseek-v4-pro`。
2. 新增证据提示词构建器，要求回答只能基于检索资料，并使用 `[证据N]` 标注关键事实来源。
3. Pipeline 支持 LLM 流式 token、usage、finish_reason，并在服务不可用时降级为基于证据的可解释回答。
4. `sources` 事件增加 `evidence_id`，前端来源卡片可展示证据编号。
5. 新增 DeepSeek 可用性冒烟脚本与 UTF-8 SSE 闭环冒烟脚本。
6. 修复旧 QA 缓存污染问题：缓存键从 `qa:v2` 升级为 `qa:v3`，并纳入回答生成器命名空间，避免历史占位答案绕过真实 LLM。

## 关键问题与修复

现象：

- `POST /api/chat/stream` 检索已命中“小灵山的佛教缘起”。
- 返回答案仍包含“首版骨架目前使用占位回答流程”。
- SSE 中没有 `text_chunk`，说明没有进入真实 LLM 流式生成。

原因：

- 旧版占位答案已写入 `qa_cache_entries`。
- 缓存键只区分问题与选择上下文，没有区分回答生成器版本、模型、prompt 版本。
- 因此 B1 新代码被旧缓存短路。

修复：

- `build_selection_cache_key` 增加 `answer_namespace`。
- API 层根据 `provider/model/prompt/max_tokens/max_docs/max_doc_chars` 构造回答缓存命名空间。
- 新缓存键统一为 `qa:v3:<hash>`，不删除历史数据，但不会再命中旧占位缓存。

## 真实闭环验证

测试接口：

```text
POST http://127.0.0.1:8010/api/chat/stream
```

测试问题：

```text
玄奘为什么把马山命名为小灵山？
```

结果摘要：

```text
ok = true
status_code = 200
first_text_ms = 30332.97
total_ms = 31115.67
evidence_ids = 证据1, 证据2, 证据3, 证据4, 证据5
top_source = 小灵山的佛教缘起
```

模型用量：

```text
prompt_tokens = 1072
completion_tokens = 223
total_tokens = 1295
cached_tokens = 0
finish_reason = stop
```

生成答案：

```text
玄奘法师之所以将马山命名为“小灵山”，是因为他途经此地时，见这里“层峦丛翠，曲水净秀，山形酷似印度灵鹫山”[证据1]。他顿觉此地与佛法渊源深厚，于是将所译《大般若经》中的“灵鹫胜境”之名赐予此地，称其为“小灵山”[证据1]。
```

报告文件：

```text
eval/reports/deepseek_smoke_v1.json
eval/reports/chat_stream_smoke_b1.json
```

## 审查结果

已通过：

```text
backend: 58 passed
eval: 6 passed
专项测试: 15 passed
compileall: passed
frontend build: passed
```

前端构建存在既有警告：

```text
VueUse PURE annotation warning
large chunk warning
```

这些警告不影响本阶段功能闭环。

## 当前限制

1. 首 token 约 30 秒，主要受冷启动加载、本地 reranker 与真实 LLM 首包影响，尚未达到最终“小于 5 秒语音响应”的演示指标。
2. 当前只完成文本 LLM 真实闭环，图片识别、多模态模型、ASR、TTS、数字人真实驱动仍未完成。
3. B1 只证明单题真实链路可用，不等价于 90% 准确率验收；后续必须进入 B2 的 100 题评测。

## 下一步建议

1. 阶段 B2：建立 100 题端到端评测集，统计事实准确率、证据引用率、拒答合规率和延迟。
2. 根据 B2 结果优化 prompt、检索召回、缓存策略与性能。
3. 阶段 B3 前单独确认视觉模型供应商和预算，再接入真实图片识别。
