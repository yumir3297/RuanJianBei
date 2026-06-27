# 2026-06-16 阶段 B2.3 小样本真实评测实施报告

## 本轮目标

在 B2.2 已完成 100 题离线评测集后，先抽取前 5 题进行真实端到端评测，验证本地后端、SSE 流式接口、真实 DeepSeek 文本链路、证据评分脚本和延迟统计是否能形成最小闭环。

## 执行范围

1. 使用测试集：`eval/testset/e2e_qa_100.json`。
2. 执行模式：`sampled-real`。
3. 真实题量：前 5 题。
4. 临时后端：`127.0.0.1:8010`，评测结束后已关闭。
5. 输出报告：`eval/reports/e2e_eval_b2_sampled_real.json`。
6. 本轮没有执行 100 题批量真实评测，也没有接入图片识别、ASR、TTS 或 Avatar Provider。

## 首轮发现的问题

首轮 5 题真实评测中，脚本没有崩溃，后端也能正常返回 SSE，但 4 道 FAQ/直答路径题目被评分为失败。失败原因不是事实错误，也不是没有来源，而是答案正文缺少内联 `[证据N]` 引用。

首轮关键现象：

1. `source_hit=true`，说明后端已返回证据来源。
2. `required_fact_hit=true`，说明核心事实命中。
3. `citation_present=false`，说明 FAQ/缓存/直答路径没有把证据编号写入最终答案文本。
4. B2.1 采纳的评分规则发挥了作用，准确暴露了“有证据对象但答案文本不可审计”的问题。

## 已完成修复

1. 在 `backend/app/services/qa/pipeline.py` 增加 `_ensure_inline_citations(answer, sources)`。
2. 在 `_emit_final_answer` 统一出口中补齐直答类答案的内联证据编号。
3. 若答案已经包含 `[证据N]`，不会重复追加。
4. 若没有 sources，不伪造引用，仍由盲区/降级逻辑处理。
5. 在 `backend/app/tests/test_pipeline.py` 新增直答路径自动补证据编号测试。
6. 在 `eval/scripts/e2e_eval_core.py` 修复纯 `text` 事件答案的首文本时间统计，避免只依赖 `token` 事件。
7. 在 `eval/tests/test_e2e_eval_runner.py` 增加纯文本事件评分覆盖。

## 复测结果

修复后重新启动临时后端并再次执行 5 题真实评测，结果如下：

```text
accuracy = 1.0
evidence_rate = 1.0
source_hit_rate = 1.0
failure_count = 0
```

5 道题均通过 `answer_with_evidence` 的全部 must_pass 条件：

1. `stream_completed`
2. `source_hit`
3. `required_fact_hit`
4. `forbidden_fact_absent`
5. `citation_present`

## 延迟记录

本轮报告区分冷启动和热运行：

```text
first_text_all:  count=5, avg=3428.76ms, p50=47.99ms, p95=16953.98ms
first_text_warm: count=4, avg=47.45ms,   p50=44.98ms, p95=52.74ms
total_all:       count=5, avg=3430.42ms, p50=49.58ms, p95=16955.98ms
total_warm:      count=4, avg=49.03ms,   p50=46.89ms, p95=53.89ms
```

说明：本轮采样前 5 题主要命中 FAQ/缓存/直答快路径，因此热运行延迟很低；冷启动仍包含模型与索引加载成本，不能直接代表最终 100 题真实 LLM 延迟。

## DeepSeek 调用与费用边界

首轮评测中出现 1 次真实 DeepSeek 文本调用，日志记录为：

```text
prompt_tokens=645
completion_tokens=262
total_tokens=907
```

修复后的复测主要命中快路径，没有继续扩大题量。本轮仍遵守“只做小样本真实评测，不跑 100 题批量真实调用”的预算边界。

## 验证结果

```text
backend app tests: 59 passed
eval tests:        9 passed
100题结构校验:     valid=true, case_count=100, error_count=0
compileall:        passed
```

临时后端进程已关闭，`8010` 端口未继续保留服务。

## 当前结论

B2.3 小样本真实评测闭环已完成。评测框架能发现“事实正确但不可审计引用缺失”的问题，后端已在统一最终答案出口补齐内联证据编号，5 题复测达到 100% 通过。

下一步不建议直接跑 100 题真实评测，应先让 DeepSeek 审查本报告与修复点；确认后可进入更大样本的受控真实评测，例如 10 到 20 题，并继续记录调用量、失败题型和冷/热延迟。
