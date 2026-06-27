# 2026-06-16 阶段 B1 续作与验证计划

## 当前断点

- 阶段 B0 已完成：DeepSeek `deepseek-v4-pro` 可用性冒烟通过，接口返回 HTTP 200，并记录到 `eval/reports/deepseek_smoke_v1.json`。
- 阶段 B1 已完成主要代码：后端 LLM 接入、证据提示词、流式解析、用量事件、失败降级、前端证据编号展示、UTF-8 SSE 冒烟脚本。
- 昨天停止点：因为额度不足，中止继续真实调用；当时 `8001` 曾返回旧占位文案，判断为旧进程或未加载新版代码导致，尚未完成新版真实闭环确认。
- 今天用户已确认额度恢复，可以继续执行一次低成本真实闭环验证。

## 本次只做的事情

1. 不修改模型供应商、公共 API、数据库结构或前端主交互。
2. 先确认没有旧后端进程占用测试端口，避免误测旧代码。
3. 用当前源码重新启动一个临时新版后端端口，优先使用 `8010`，不影响用户可能自启的 `8000`。
4. 运行 `eval/scripts/chat_stream_smoke.py`，用 UTF-8 客户端请求：
   - 问题：`玄奘为什么把马山命名为小灵山？`
   - 目标接口：`POST /api/chat/stream`
5. 验证返回是否满足 B1 最小闭环：
   - `sources` 事件包含 `evidence_id`。
   - 检索源命中“小灵山的佛教缘起”等相关资料。
   - `text_chunk` 或 `text` 由真实 LLM 生成，不再出现旧占位文案。
   - 回答中包含 `[证据N]` 引用。
   - 末尾返回 `done` 事件。
6. 若失败，只记录失败原因并停止，不继续扩大改动。

## 验证标准

- 后端专项测试：`app/tests/test_llm_openai_compatible.py` 与 `app/tests/test_pipeline.py` 通过。
- Python 编译检查通过。
- 真实 SSE 冒烟报告写入 `eval/reports/chat_stream_smoke_b1.json`。
- 若真实调用成功，补写 B1 实施报告并更新当前任务摘要。

## 成本与边界

- 本轮只进行必要的低成本真实文本调用，控制在用户已批准的 DeepSeek 额度范围内。
- 不启动视觉模型、不新增视觉供应商、不做 B3 图片识别。
- 不擅自关闭用户自己的后端进程；如需要终止未知进程，会先请求用户确认。

## 执行结果

- 已完成 B1 真实闭环验证，详见 `docs/2026-06-16-stage-b1-deepseek-evidence-implementation-report.md`。
- UTF-8 SSE 验证通过，结果写入 `eval/reports/chat_stream_smoke_b1.json`。
- 修复旧 `qa:v2` 占位缓存污染问题，新缓存键升级为 `qa:v3`，并纳入回答生成器命名空间。
- 完整后端回归、评测脚本测试、Python 编译检查和前端生产构建均通过。
