# 2026-06-16 阶段 B2.1 端到端评测框架实施报告

## 本轮目标

在不调用 DeepSeek、不产生 API 费用的前提下，先搭建端到端评测框架骨架，确保后续 100 题整理和小样本真实评测有可审计的评分逻辑。

## 已采纳的审查建议

1. 明确 `expected_behavior` 的评分规则。
   - `answer_with_evidence.must_pass = stream_completed, source_hit, required_fact_hit, forbidden_fact_absent, citation_present`
   - `refuse_without_evidence.must_pass = stream_completed, refusal_correct, forbidden_fact_absent`
2. 新增 Mock 后端测试，覆盖完整证据回答、缺少引用、知识盲区拒答、出现禁用事实等评分路径。
3. 评测结果中标记 `is_cold_start`，报告同时预留 all 与 warm 两套延迟统计，避免首题冷启动拉偏热运行 P95。

## 新增文件

```text
eval/scripts/e2e_eval_core.py
eval/scripts/check_e2e_testset.py
eval/scripts/run_e2e_chat_eval.py
eval/testset/e2e_qa_seed.json
eval/tests/test_e2e_eval_runner.py
```

## 功能说明

### `check_e2e_testset.py`

离线校验评测集，不启动后端，不调用模型。

校验内容：

1. JSON 必须是数组。
2. `id` 必须非空且唯一。
3. `category` 必须在白名单内。
4. `expected_behavior` 必须在白名单内。
5. 证据回答题必须提供 `expected_sources` 和 `required_facts`。
6. 拒答题不能提供 `required_facts`。

### `run_e2e_chat_eval.py`

支持三种模式：

```text
dry-run
local-server
sampled-real
```

当前已验证 `dry-run`。联网模式必须显式传入 `--allow-network`，防止误触发真实调用。

### `e2e_eval_core.py`

核心能力：

1. 读取并校验评测用例。
2. 解析 SSE 事件。
3. 对单题进行确定性评分。
4. 生成准确率、证据引用率、拒答合规率、源命中率。
5. 生成首题冷启动与后续热运行延迟统计字段。

## Seed 评测集

当前 `eval/testset/e2e_qa_seed.json` 共 10 题：

```text
fact_qa: 1
history_culture: 1
attraction_detail: 1
route_planning: 2
practical_info: 1
guided_selection: 1
followup_context: 1
blind_spot_refusal: 2
```

覆盖点：

1. 景点事实。
2. 历史文化。
3. 景点特色。
4. 路线规划。
5. 实用信息。
6. 游客主动选择。
7. 连续追问上下文。
8. 知识盲区拒答。

## 验证结果

```text
新增 Mock 测试: 2 passed
eval 全量测试: 8 passed
compileall eval/scripts eval/tests: passed
check_e2e_testset.py: valid=true, case_count=10
run_e2e_chat_eval.py --mode dry-run: passed
```

生成报告：

```text
eval/reports/e2e_eval_b2_dry_run.json
```

## 当前边界

1. 本轮没有调用 DeepSeek。
2. 本轮没有启动本地后端。
3. 本轮没有整理完整 100 题。
4. 自动评分仍是确定性规则，不能完全替代人工复核。

## 下一步建议

进入 B2.2：基于现有官方资料、FAQ、路线、知识条目整理 `eval/testset/e2e_qa_100.json`，并先用 `check_e2e_testset.py` 与 `dry-run` 全量验证，不产生 API 费用。
