# 2026-06-16 阶段 B2 端到端评测开发计划

## 阶段目标

把 B1 已跑通的“真实 DeepSeek 文本问答 + 检索证据链”从单题验证升级为可量化验收链路，重点证明：

1. 景区事实问答准确率是否接近或达到赛题要求的 90%。
2. 回答是否严格基于官方资料，并能稳定给出 `[证据N]`。
3. 知识不足时是否能拒绝编造。
4. 游客主动选择、上下文追问、FAQ 快速命中、RAG + LLM 等路径是否都可评测。
5. 首 token、总耗时、缓存命中等性能指标是否满足后续优化需要。

## 当前前提

- B1 已完成真实文本 LLM 闭环。
- 当前模型供应商：DeepSeek。
- 当前模型：`deepseek-v4-pro`。
- 当前已知单题真实结果：
  - DeepSeek HTTP 200。
  - `prompt_tokens=1072`。
  - `completion_tokens=223`。
  - `total_tokens=1295`。
  - 首 token 约 `30332.97ms`。
- 当前重要风险：功能闭环已通，但延迟未达最终演示指标。

## 本阶段不做的事情

1. 不接入图片识别，不启动阶段 B3。
2. 不接入 ASR、TTS 真实供应商，不启动阶段 D。
3. 不改公共 API、不改数据库结构、不换模型供应商。
4. 不直接批量调用 DeepSeek；批量真实评测前必须再次请用户确认预算。
5. 不删除历史数据库缓存，只通过新评测 session 和缓存命名空间规避污染。

## 评测集设计

计划建立 `100` 题端到端评测集，先以 JSON 文件管理，后续可扩展为表格或后台维护。

建议文件：

```text
eval/testset/e2e_qa_100.json
```

单题字段设计：

```json
{
  "id": "B2_FACT_001",
  "category": "fact_qa",
  "query": "灵山大佛有多高？",
  "selection": null,
  "context": null,
  "expected_sources": ["灵山大佛"],
  "required_facts": ["88米", "79米", "莲花瓣9米"],
  "forbidden_facts": [],
  "expected_behavior": "answer_with_evidence",
  "notes": "核心景点事实题"
}
```

题型分布建议：

```text
fact_qa: 30 题
history_culture: 15 题
attraction_detail: 15 题
route_planning: 10 题
practical_info: 10 题
guided_selection: 8 题
followup_context: 6 题
blind_spot_refusal: 6 题
```

覆盖原则：

1. 每个核心景点至少覆盖 1-2 个事实问题。
2. 历史文化题必须覆盖“小灵山缘起、祥符禅寺、五方五佛、梵宫、五印坛城”等高频讲解点。
3. 路线题覆盖亲子、历史文化、自然风光、半日/深度游等用户意图。
4. 实用题覆盖餐饮、导游服务、穿着建议、开放信息边界。
5. 盲区题覆盖天气、实时交通、厕所实时排队、票价实时变化等知识边界。
6. 主动选择题必须带 `selection`，验证游客主动选择是否能收敛检索范围。
7. 追问题必须带 `context.last_subject`，验证“它/这里/这个景点”等指代是否可用。

## 评测脚本设计

建议新增脚本：

```text
eval/scripts/run_e2e_chat_eval.py
eval/scripts/check_e2e_testset.py
```

`check_e2e_testset.py` 只做离线校验：

1. 检查 JSON 格式。
2. 检查 id 唯一。
3. 检查 category 是否在白名单内。
4. 检查 `expected_behavior` 是否在白名单内。
5. 检查每题至少有 `required_facts` 或 `expected_sources` 或明确拒答预期。

`run_e2e_chat_eval.py` 分三种模式：

```text
--mode dry-run
```

只读取评测集并输出统计，不启动后端、不调用模型。

```text
--mode local-server
```

请求本地已启动的后端接口，适合小样本真实链路验证。

```text
--mode sampled-real
```

只跑指定数量样本，例如 5 题或 10 题。批量 100 题真实调用前必须再次确认预算。

## 自动评分规则

第一版先做确定性评分，不引入额外 LLM judge，避免额外成本。

核心指标：

```text
source_hit
required_fact_hit
forbidden_fact_absent
citation_present
refusal_correct
stream_completed
first_text_ms
total_ms
event_types
```

判定逻辑：

1. `source_hit`：`sources[*].title/source/snippet` 中命中 `expected_sources`。
2. `required_fact_hit`：回答文本中命中 `required_facts`。
3. `forbidden_fact_absent`：回答文本中不包含 `forbidden_facts`。
4. `citation_present`：需要回答的题目必须出现 `[证据`。
5. `refusal_correct`：盲区题必须出现“无法确定/没有足够资料/建议以景区官方信息为准”等边界表达。
6. `stream_completed`：必须收到 `done` 事件。
7. `accuracy_pass`：按题型组合上述指标生成通过/失败。

DeepSeek 审查后补充：

```text
每个 expected_behavior 必须在代码里声明 must_pass 与 optional 检查项。
```

第一版规则：

```text
answer_with_evidence.must_pass = stream_completed, source_hit, required_fact_hit, forbidden_fact_absent, citation_present
answer_with_evidence.optional = refusal_correct

refuse_without_evidence.must_pass = stream_completed, refusal_correct, forbidden_fact_absent
refuse_without_evidence.optional = source_hit, required_fact_hit, citation_present
```

解释：

1. 事实类、历史类、景点类、路线类、实用信息类题目，只要缺少证据引用就不能算通过。
2. 盲区拒答类题目不强制要求证据引用，但必须明确表达资料不足或无法确定。
3. `forbidden_fact_absent` 对所有题型都是硬性要求。

第一版准确率计算：

```text
accuracy = accuracy_pass_count / total_case_count
evidence_rate = citation_present_count / answer_with_evidence_case_count
refusal_pass_rate = refusal_correct_count / blind_spot_case_count
source_hit_rate = source_hit_count / total_case_count
```

## 输出报告设计

建议输出：

```text
eval/reports/e2e_eval_b2_dry_run.json
eval/reports/e2e_eval_b2_sampled_real.json
docs/2026-06-16-stage-b2-e2e-evaluation-implementation-report.md
```

报告包含：

1. 评测题数与分类分布。
2. 准确率、证据引用率、拒答合规率、源命中率。
3. P50/P95 首 token 延迟。
4. P50/P95 总耗时。
5. 失败样例清单。
6. 失败原因分类：检索失败、证据不足、模型未引用、回答不完整、缓存污染、超时等。
7. 下一轮修复建议。

延迟统计补充：

1. 每条结果记录 `is_cold_start`。
2. 报告同时输出 all 与 warm 两套 P50/P95。
3. 首题冷启动不从原始结果中删除，但不能让冷启动数据误导热运行性能判断。

## 开发顺序

### B2.1 评测框架骨架

只写离线代码，不调用 DeepSeek。

交付：

```text
eval/scripts/check_e2e_testset.py
eval/scripts/run_e2e_chat_eval.py
eval/testset/e2e_qa_seed.json
eval/tests/test_e2e_eval_runner.py
```

DeepSeek 审查后补充：

1. `test_e2e_eval_runner.py` 必须使用 Mock 后端返回 SSE。
2. Mock 测试至少覆盖：
   - 完整证据回答通过。
   - 缺少 `[证据N]` 引用失败。
   - 知识盲区拒答通过。
   - 出现 forbidden fact 失败。
   - 首题冷启动与后续热运行延迟分开统计。

验证：

```text
backend/.venv/Scripts/python.exe -m pytest eval/tests -q
backend/.venv/Scripts/python.exe eval/scripts/check_e2e_testset.py --testset eval/testset/e2e_qa_seed.json
```

### B2.2 100 题评测集

先根据现有官方资料、FAQ、路线、知识条目人工整理 100 题。

交付：

```text
eval/testset/e2e_qa_100.json
```

验证：

```text
check_e2e_testset.py 通过
dry-run 报告通过
```

### B2.3 小样本真实评测

先跑 5-10 题，确认：

1. 不再命中旧占位缓存。
2. SSE 事件完整。
3. 报告能正确统计引用与延迟。
4. 成本可控。

注意：

- 这里会产生真实 DeepSeek 调用费用。
- 开始前需要用户再次确认样本数量和预算。

### B2.4 批量评测与修复

在用户确认预算后再跑 100 题。

根据失败结果决定是否进入修复：

1. 检索失败：调整查询改写、Top-K、作用域或 reranker。
2. 引用缺失：调整 prompt 或后处理校验。
3. 盲区误答：强化拒答规则与边界检测。
4. 延迟过高：检查模型冷启动、reranker、缓存、FAQ 快速命中与预热。

## 费用控制策略

1. 默认开发阶段只跑 `dry-run`，不调用模型。
2. 小样本真实评测默认不超过 5 题，除非用户明确同意。
3. 批量 100 题评测前必须单独确认。
4. 报告记录每题 token 用量和总 token，便于估算成本。

## 风险与应对

1. 自动评分不能完全替代人工判断。
   - 应对：报告保留失败样例和原始回答，方便人工复核。
2. 100 题质量决定评测可信度。
   - 应对：题目必须绑定 `expected_sources` 和 `required_facts`。
3. 延迟可能受冷启动影响偏高。
   - 应对：报告区分首轮冷启动和后续请求。
4. 缓存可能影响真实评测。
   - 应对：评测 session 独立，必要时增加 `--disable-cache` 或使用新 query id，但不直接删库。

## 本次等待确认的问题

如果 DeepSeek 审查通过，下一步建议先执行 B2.1：

```text
只实现评测框架骨架 + 10 题 seed 数据 + 离线测试，不进行真实模型批量调用。
```

确认后再进入代码实现。
