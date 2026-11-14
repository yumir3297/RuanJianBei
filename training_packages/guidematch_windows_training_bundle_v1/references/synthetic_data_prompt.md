# GuideMatch 仿真训练集生成提示词

## 目的与边界

本提示词用于生成 GuideMatch 的**合成问句对训练候选**，不是生成公共景区事实，也不是生成最终测试集。每条记录必须沿用当前评测格式：`case_id, family_id, left, right, expected, reason, origin`。`left/right` 使用 `QuestionContext` 字段：`text` 必填，`poi_id、target_id、unit_id、queried_date` 在场景需要时填写。

当前模型任务是判断两个问句是否能安全复用同一个答案范围：`reuse | distinct | clarify`。生产决策必须先应用景点、对象、日期等确定性硬约束，再使用模型排序/分类；高相似度不能覆盖对象或时效冲突。生成数据只用于离线模型实验，不能改变此安全边界，也不能自动发布 GuideLoop 知识。

## 数据规模建议

首轮生成 **900 条训练候选**，三类各 300 条。按 100 条一批生成，共 9 批；每批每类约 33 至 34 条。经去重、字段校验和人工抽检后，目标保留至少 **600 条可用训练样本，且至少 600 个审核通过的独立 family_id，每类至少 200 个**。项目既有的门槛是至少 200 条人工核验独立问句对、每类至少 30 条；600 条是扩大后的实验目标，不是已验证的效果保证。

预估假设：生成候选中约三分之二能通过去重和审核，故生成 900 条以争取 600 条有效样本。这个通过率只是规划估计；应按实际通过率增补批次，不可直接把 900 条都计为训练数据。每批输出 `case_id` 使用 `syn-train-b01-001` 这类唯一编号。默认一条记录对应一个独立 family；仅当多条确属同一底层意图的近重复时才共用 `family_id`，不许靠同义改写凑独立样本数。最终独立 family 不足目标时，补充不同意图或场景，不扩写旧 family。

建议类别结构：

| 标签 | 候选数 | 场景构成 |
|---|---:|---|
| `reuse` | 300 | 同一目标对象下的口语改写、长短表达、倒装/冗余、近音错字或语音转写风格；时间敏感问题必须保持日期一致。 |
| `distinct` | 300 | 跨景点 90、同景点不同目标对象 90、不同日期/场次 75、同对象不同子意图 45。每个负例都要有明确冲突依据。 |
| `clarify` | 300 | 缺少目标对象 105、缺少景点范围 60、时间敏感问题缺日期 75、代词/空间指代含糊 60。必须确实缺少会改变答案的关键信息。 |

上述比例用于训练覆盖，不等于评测集比例。现有冻结 `pairs_dev.jsonl`、`pairs_test.jsonl` 和 `replay.jsonl` 不得被覆盖、扩充、改写或用于提示词示例；特别是封存集不得交给生成模型。

## 可直接使用的生成提示词

```text
你是 GuideMatch 中文问句匹配数据集生成器。请生成仅供离线训练候选使用的合成问句对，不要生成景区事实，不要声称数据来自真实游客。

【任务定义】
给定 left 和 right 两个游客问句及其结构化场景上下文，判断能否安全复用同一个答案范围。请按“问句文本 + 已明确提供的结构化字段”一起判断：
- reuse：景点、目标对象、子意图和必要的时间范围一致，两个问法在本场景下可由同一答案回答。
- distinct：有明确证据表明答案范围不同，例如景点不同、目标对象不同、时间敏感问题日期不同，或虽指向同一对象但实际子意图不同。
- clarify：影响答案的景点、目标对象、单元或必要日期，在问句和结构化字段中都没有被明确补足，无法安全确认是否同一需求。

语义相似度不能覆盖景点、对象、日期等范围冲突。不要把“信息缺失”伪装成明确冲突；不要把明确的不同对象标成 clarify。不得根据熟悉的景点常识补造事实。

【结构化字段与标签的一致性，优先级最高】
1. `poi_id、target_id、unit_id、queried_date` 是本条样本提供给匹配器的上下文，不是生成器的猜测。只有场景明确给出时才填写；不能为了让样本看起来完整而推断或补齐。
2. `clarify` 必须有可机器观察到的缺失：至少一侧缺少本任务所需的 `poi_id`、`target_id`、`unit_id` 或时间敏感问题的 `queried_date`。若文本含“那个/它/旁边”等指代且指代对象会改变答案，必须省略对应的范围字段；若现有字段仍把范围完整标明，则不要标 `clarify`。
3. 当前 `QuestionContext` 没有对话历史字段。不得依赖未提供的上一轮对话、画面位置、手势或“游客眼前所指”来制造歧义。无法用现有字段表达的纯视觉/跨轮指代场景，不生成。
4. 如果 left 和 right 两侧所有与本问题有关的范围字段都已明确且相同，不要因为文本中出现代词或口语省略就标 `clarify`。若文本与结构化字段互相矛盾，该样本作废，不要自行决定信哪一方。
5. 时间敏感问题的 `queried_date` 表示该问句发生的日期，不是事实有效期。按当前项目匹配规则关注“今天、明天、后天、现在、下一场、几点、什么时候、日期、演出、活动、开放”等表达。含“今天/明天/后天”时，必须相对 `SIMULATED_TODAY` 正确计算；无法明确锚定日期的场景按缺失日期处理。其他时间表达若当前硬规则未覆盖，不要伪称已通过时间硬约束，应放入待规则扩展用例而非本批训练集。
6. 写入 `target_id` 前确认它表达的是当前匹配任务实际需要的范围。不可一边写入已确定的目标范围，一边又声称目标不明。现有 schema 无法表达的细粒度差异应剔除，不扩展字段、不编造上下文。

【本批参数】
批次编号：{{BATCH_ID}}
本批总量：{{BATCH_SIZE，推荐100}}
目标标签数量：reuse={{N_REUSE}}，distinct={{N_DISTINCT}}，clarify={{N_CLARIFY}}
本批目标景点/对象清单：{{POI_TARGET_CATALOG}}
允许的场景覆盖：{{SCENARIO_QUOTAS}}
模拟当天基准：{{SIMULATED_TODAY，必填，例如2026-11-12；纯合成时钟，不代表真实日期安排}}
允许使用的模拟日期范围：{{DATE_RANGE，例如2026-11-10至2026-11-20；只用于构造日期冲突，不代表真实活动安排}}
已用 case_id 清单：{{USED_CASE_IDS}}
已用 family_id/意图清单：{{USED_FAMILIES}}

【项目场景约束】
仅使用 poi_id `bathing`（九龙灌浴）和 `buddha`（灵山大佛）。target_id 必须从本批给定目录中选择，不得发明 ID。可以使用目录中已有对象，例如 prince、nirvana、right_hand、base_figures、statue_height、restroom、accessibility、bath_show、exit_route、lotus_ornament、gesture_figure、temple_event、figure_height、mausoleum、lotus_platform、statue_location、route、ticket_price、experience；未明确提供的对象请不要创造。

问题文本只能表达询问，不得在问句里植入未经给定的答案或新的事实。对场次、营业、票价等动态问题，时间字段只作模拟上下文；必须明确是合成日期，不可写成真实运营时间。若需要 `unit_id`，只使用本批目录给出的值；没有就省略。

【多样性要求】
1. 生成自然、简短、符合中文游客现场口语的表达；混合普通话口语、礼貌问法、省略句、短句、少量语音转写错字和重复表达。不要写成整齐的模板句。
2. 避免只替换“什么/啥/哪一个”的机械改写。不同 family 应改变真实意图或场景，不要批量复制同一个骨架。
3. 同一个 family_id 表示同一底层意图/场景家族的近重复、改写或对照。默认每条记录生成不同的独立 family；确有多条配对属于同一底层意图时才共享 family_id。不同底层意图必须使用不同 family_id，不能用多条改写冒充独立案例。
4. reuse 对两侧必须有足够一致的范围字段；时间敏感时两侧 queried_date 相同。表达可不同，但答案范围要真相同。
5. distinct 的硬冲突要在字段中可见：cross_object 两侧 poi/target 明确不同；temporal_conflict 两侧日期明确不同；different_subintent 说明同一对象下回答任务不同。
6. clarify 至少一侧缺少对判定必要的结构化字段，而且文本不能消除该缺失。纯文本里有模糊代词但两侧范围字段已完整一致，不构成 clarify。不要仅为凑数而把普通短问句都标 clarify。
7. `reason` 只能使用：same_target、cross_object、temporal_conflict、different_subintent、missing_reference、ambiguous_target。按标签选择相符原因。
8. 每条 `case_id` 唯一。所有记录 `origin` 固定为 `synthetic_case`。不得输出真实姓名、联系方式、游客身份标识或任何个人数据。

【输出格式】
只输出 JSONL，每行一个合法 JSON 对象，不要 Markdown、代码围栏、解释、汇总或行间注释。字段必须且只能是：
{"case_id":"syn-train-{{BATCH_ID}}-001","family_id":"syn-family-...","left":{"text":"...","poi_id":"bathing","target_id":"prince"},"right":{"text":"...","poi_id":"bathing","target_id":"prince"},"expected":"reuse","reason":"same_target","origin":"synthetic_case"}

字段规则：
- `case_id` 全数据唯一，格式 syn-train-批次号-三位序号。
- `family_id` 稳定标识底层意图家族。近重复不得拆成不同 family。
- `left.text` 和 `right.text` 非空，最长 280 字。
- 每个上下文只输出已知且需要的字段；未知字段省略，不要输出 null 或空字符串。
- `queried_date` 使用 YYYY-MM-DD。仅在场景确实涉及时间且该日期已给定时填写。
- 时间表达与 `queried_date` 必须逐条一致；例如写“今天”时，该侧日期就是 `SIMULATED_TODAY`，写“明天”时日期比模拟当天晚一天。批次参数必须提供明确的模拟当天；不允许拿生成日期自动代替模拟日期。
- `expected` 只能是 reuse、distinct、clarify。
- `reason` 与预期标签逻辑一致；origin 固定 synthetic_case。
- 输出前做逐条反向检查：把该行的两个 QuestionContext 交给项目的范围规则，在高相似度情形下，所有 `poi_conflict、target_conflict、date_conflict、missing_date、unknown_scope、missing_target` 都必须得到与 expected 一致的决策。若文本语义标签与规则输出不一致，删除或重做该行，不要让模型标签绕过硬规则。
- 不得把“可能是同一意图”当作 distinct，也不得把“缺少业务事实/无法核实答案内容”混作 clarify。本任务只标注两个问句能否共享答案范围，不判断答案事实是否正确。
- 严格按本批参数输出准确条数和各标签数量。输出前在内部逐行复核标签、范围字段和计数，但不要输出复核过程。
```

## 生成后验收

1. 每批做 JSON 解析、必填字段、枚举、长度、唯一 `case_id` 检查；检查 `distinct/cross_object` 两侧景点或目标范围确实不同，`distinct/temporal_conflict` 两侧日期均存在且不同；检查 `clarify` 的缺失范围字段确实未被文本或上下文补足。
2. 去除完全重复问句对、仅标点变化和机械同义词替换。按 `family_id` 聚合近重复，不把改写数冒充独立意图数。
3. 对每个 family 至少抽核一个代表样本；所有硬冲突负例、所有 `clarify` 样本和所有动态日期样本建议全检。错误标签、虚构对象 ID、日期字段不合逻辑、文本与字段不一致、无法由当前 schema 表达的指代、事实性断言均剔除或修正后重新核验。
4. 训练候选文件单独存放，例如 `eval/data/guidematch-synthetic-v1/pairs_train.jsonl`，并生成 manifest，记录生成器模型/版本、提示词版本、批次、时间、标签分布、family 数、去重数、审核数和文件 SHA-256。
5. 只将通过审核的训练候选用于训练。开发集应使用独立场景家族；阈值只在开发集选择。当前冻结封存集保持不变且不用于训练、提示词示例或阈值选择。若全仿真开发集也由同一提示词生成，报告中必须标明同源偏差，并补做独立生成器或人工编写的外部回放后再声称泛化。
6. 统一比较规则基线与模型：同一数据、同一范围硬约束、同一阈值选择流程。报告 macro-F1、每类 precision/recall、confusion matrix、错误归并数（distinct/clarify 被判 reuse）和 abstention/clarify 行为；不要只报告总体准确率。

## 结果表述边界

这批数据全部是合成数据。通过离线指标只能说明模型在该合成分布上的结果，不能写成真实游客准确率、真实场景收益或已经实现长期知识积累。训练样本数量、独立 family 数和人工审核数量要分开报告。
