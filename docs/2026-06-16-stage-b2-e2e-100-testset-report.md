# 2026-06-16 阶段 B2.2 100 题端到端评测集实施报告

## 本轮目标

在不调用 DeepSeek、不产生 API 费用的前提下，把 B2.1 的 10 题 seed 扩展为完整 100 题端到端评测集，并先通过离线校验和 dry-run 验证结构可用。

## 已完成内容

1. 新增 `eval/scripts/build_e2e_qa_100.py`。
   - 通过确定性本地脚本生成 `eval/testset/e2e_qa_100.json`。
   - 脚本内置分类数量检查，避免题型分布漂移。
   - 生成后自动复用 `validate_cases` 做结构校验。
2. 新增 `eval/testset/e2e_qa_100.json`。
   - 共 100 题。
   - 全部题目包含 `expected_behavior`。
   - 证据回答题包含 `expected_sources` 与 `required_facts`。
   - 盲区拒答题不包含 `required_facts`，并设置 `forbidden_facts`。
3. 更新 `eval/tests/test_e2e_eval_runner.py`。
   - 新增 100 题文件存在性、数量、分类分布和结构有效性测试。
4. 生成 dry-run 报告。
   - `eval/reports/e2e_eval_b2_100_dry_run.json`

## 题型分布

```text
fact_qa: 30
history_culture: 15
attraction_detail: 15
route_planning: 10
practical_info: 10
guided_selection: 8
followup_context: 6
blind_spot_refusal: 6
```

行为分布：

```text
answer_with_evidence: 94
refuse_without_evidence: 6
```

## 覆盖范围

1. 核心景点事实：尺寸、开放信息、位置、演出时间等。
2. 历史文化：小灵山缘起、祥符禅寺、五方五佛、世界佛教论坛、赵朴初、五明智慧等。
3. 景点详情：大照壁、九龙灌浴、百子戏弥勒、梵宫、五印坛城、曼飞龙塔、拈花湾相关景点等。
4. 路线规划：历史文化、自然风光、亲子家庭、首次游览、半日核心游等。
5. 实用信息：最佳游览时间、餐饮、住宿、穿着、携带物品、导游服务、文明礼仪等。
6. 游客主动选择：通过 `selection.attraction_id` 验证游客选择对回答范围的约束。
7. 连续追问：通过 `context.last_subject` 验证“它/这里/这个景点”的上下文指代。
8. 知识盲区：天气、排队、停车位、座位、票价、实时客流等不应编造的实时问题。

## 验证结果

```text
build_e2e_qa_100.py: ok=true, case_count=100
check_e2e_testset.py: valid=true, case_count=100
run_e2e_chat_eval.py --mode dry-run: passed
eval tests: 9 passed
compileall eval/scripts eval/tests: passed
```

生成报告：

```text
eval/reports/e2e_eval_b2_100_dry_run.json
```

## 本轮边界

1. 没有启动后端。
2. 没有调用 DeepSeek。
3. 没有产生 API 费用。
4. 本轮只验证评测集结构和评分框架兼容性，尚未验证真实回答准确率。

## 下一步建议

进入 B2.3 前需要用户再次确认：

1. 是否启动本地后端进行小样本真实评测。
2. 小样本题量，建议先跑 5 题。
3. 本轮真实调用预算。

确认后建议执行：

```text
backend/.venv/Scripts/python.exe eval/scripts/run_e2e_chat_eval.py --mode sampled-real --limit 5 --allow-network --testset eval/testset/e2e_qa_100.json
```

如果小样本暴露评分脚本或提示词问题，先修复后再考虑 100 题批量真实评测。
