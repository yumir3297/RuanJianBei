# V01 可编辑行程：调研与项目接入依据

调研日期：2026-10-29。本文是调研结论与开发建议，不代表 V01 已实现或性能已验证。

## 结论

采用用户已选择的“可验证的局部改线”：模型将自然语言转为有限操作，程序校验并计算改动，游客查看差异后确认，保存到 W01 的新修订。游客手动修改、对话修改、地图和讲解共用同一份行程。

“AI 生成行程”“地图联动”“有来源”“可撤销”已有公开先例，不能单独宣称首创。项目差异应围绕景区现场形成组合能力：保护人工决定与已游事实，保留需求约束，暴露不确定数据，并把行程修订连接到运营发布版本和数字人讲解。

## 1. 阅读的一手资料

### TravelPlanner：学习验收方法

- [仓库与 README](https://github.com/OSU-NLP-Group/TravelPlanner)
- [硬约束检查](https://github.com/OSU-NLP-Group/TravelPlanner/blob/e52c87f4ac348a3410c46dc3553c519db5ec5e23/evaluation/hard_constraint.py)
- [常识约束检查](https://github.com/OSU-NLP-Group/TravelPlanner/blob/e52c87f4ac348a3410c46dc3553c519db5ec5e23/evaluation/commonsense_constraint.py)

已读 README 和两份检查脚本的部分源码。该项目是多约束旅行规划基准，不是可直接嵌入本项目的游客端产品。其环境、常识、硬约束分层值得借鉴：输出格式正确不代表地点存在、时间足够、偏好满足。

采用：分项检查 + 全部约束同时满足率；区分“合法提案被拒绝”与“无效提案被拦截”。不直接套用跨城机票酒店指标，不把本地规则系统结果包装成官方基准成绩。

### iTIMO：学习局部修改与不变项评测

- [论文](https://arxiv.org/abs/2601.10609)
- [仓库](https://github.com/zelo2/iTIMO)
- [修改提示词](https://github.com/zelo2/iTIMO/blob/main/Benchmark/benchmark_prompts.py)
- [评测实现](https://github.com/zelo2/iTIMO/blob/main/Benchmark/eval.py)

已读摘要、README、提示词及评测脚本部分源码。其任务围绕 ADD、DELETE、REPLACE 与指定偏好变化，评测修改位置、候选地点以及提示约束满足情况。特别注意：数据文件名中的扰动操作与修复操作互为逆操作，不能按文件名直接当模型应执行的动作。

采用：修改正确性与未指定部分保持率分开评测；自己构建景区中文多轮样本。论文数据中的城市分布、热度、空间阈值与本景区数据不等价，不直接移植阈值或宣称迁移效果。

### JourneyPilot：学习同一成果、多种视图与版本提交

- [仓库](https://github.com/Lagom-TA/JourneyPilot)
- [变更预览、提交与幂等](https://github.com/Lagom-TA/JourneyPilot/blob/198d4c2a1a783fee8da394028dbb97c2011076db/backend/travel_agent/planning/delivery/workspace_mutations.py)
- [结构化解析](https://github.com/Lagom-TA/JourneyPilot/blob/198d4c2a1a783fee8da394028dbb97c2011076db/backend/travel_agent/planning/itinerary/parsing.py)
- [候选与地点身份结构](https://github.com/Lagom-TA/JourneyPilot/blob/198d4c2a1a783fee8da394028dbb97c2011076db/backend/travel_agent/planning/itinerary/draft.py)
- [修订相关测试](https://github.com/Lagom-TA/JourneyPilot/blob/198d4c2a1a783fee8da394028dbb97c2011076db/backend/tests/planning/itinerary/test_revision.py)

已读 README 和上述文件的部分源码。可直接观察到 preview 不移动当前版本、apply 使用版本校验、幂等请求与原始变更绑定；地点身份与一次行程中的出现项有所区分。README 描述 itinerary/map/report 从相同交付记录投影；本轮未运行该项目，不把仓库自述当作实测质量。

采用：同一行程快照驱动各视图、明确的变更预览、版本冲突和重复提交保护。其跨城研究、MCP、Redis 和多智能体技术栈不作为本项目 V01 的前提。

### LLM-Modulo：学习模型与校验器分工

- [Robust Planning with LLM-Modulo Framework](https://arxiv.org/abs/2405.20625)

已读摘要。该研究为“模型提出候选，外部检查器验证”提供参考，不代表采用该结构就能达到论文效果。本项目具体算法和收益必须自己测量。

### OR-Tools 时间窗路线：明确数据前提

- [Google 官方 VRPTW 示例](https://developers.google.com/optimization/routing/vrptw)

已读问题定义、数据模型及示例输入。时间窗求解依赖地点间旅行时间矩阵和可用时窗。现有演示坐标与文字开放说明不足以构成经核验的步行时间矩阵。

采用：先明确数据可用性，再选择优化方法。首轮做模板候选与有限改线、预算检查；有真实路网和时窗后再评估求解器。不把直线距离当实际步行距离。

## 2. 本项目实际情况

| 现有入口 | 核对结果 | V01 的接入方式 |
|---|---|---|
| `backend/app/services/recommend/engine.py` | 基于兴趣/舒适偏好选路线模板；时长数字截断不会减少景点 | 复用候选模板，新增真正的条目编辑和预算校验 |
| `frontend/src/views/tourist/RouteView.vue` | 主目录展示路线，按钮拼接自然语言交给聊天 | 路线工具成为当前行程编辑入口，按钮传稳定对象标识 |
| W01 分支 `codex/w01-tour-sessions` | Cookie 归属、快照修订、冲突保护、事件及成果引用已实现；另一个对话仍在维护验收 | 复用其权限与保存边界，不在当前主目录重新实现 |
| W01 `TourStop` | 仅名称、景点 ID、解析标记、内容版本 | 增加一次停留的 ID、停留时间、锁定、来源与进度 |
| W01 `TourSnapshot` | 无 schema_version，来源枚举未包含 AI | 版本化扩展，老快照读入升级，历史原文不改写 |
| `quick_select.py` / `schemas/selection.py` | 展示数据库整数 ID，另有 metadata `attraction_id` | 场景内景点码与当前知识条目 ID 显式映射 |
| `data/processed/knowledge_entries.json` | 38 条知识记录；部分有 LS-001 等景点码和文字 `opening_info` | 目录仅纳入有景点身份且已发布的有效条目；文字开放说明不能直接变成实时开放状态 |
| `frontend/src/constants/mapSpots.js` | 演示坐标、热度及部分代理映射，如入口映射为另一景点 | 不用作权威身份解析、实时客流或路网证明 |
| `BaseLLMService.stream_generate` | 讲解文本流接口，缺证据会返回说明文案 | 新增专用结构化意图接口，复用连接配置与并发限制；不解析游客可见回答来执行修改 |
| K01 独立检出 | 已有知识发布与版本能力，主目录尚未合入 | 通过已发布目录适配器读事实；未整合时只能验证模拟数据路径 |

核对为只读；未调用付费模型、运行外部仓库或修改其他对话的工作树。

## 3. 可对外表达的创新方向

建议产品名称：**可验证的连续伴游规划**。

1. **约束保持的局部改线**：要求去掉一个点时，明确列出哪些点、顺序和休息时长改变，保留未授权改变的内容。
2. **保护人工决定与已游事实**：人工锁定、已完成和已跳过条目不会被 AI 自动重写；“撤销改线”不撤销真实游览记录。
3. **带证据与不确定性的行程**：景点引用已发布内容版本；时间标注来源或估算，缺数据可看见，不生成虚假的精确承诺。
4. **规划与讲解连续衔接**：当前景点以对象 ID 连接地图、问答与数字人，改线后讲解上下文随确认版本更新。

这些是待实现、待评测的系统设计差异，不是已证明的行业首创、算法原创或性能优势。

## 4. 建议的评测

自建 60 个开发场景和 30 个冻结验收场景，按初始生成、明确修改、歧义/冲突、游中修改、故障/并发、内容变化分层；冻结集不参与调提示词。每例由结构化断言判断，解释文案可另做人工盲评。

比较三组：当前模板推荐；模型整份重写；模型结构化操作 + 程序校验。两种模型方案使用相同供应商、模型、候选资料和预算，记录版本与调用成本。模板法不适用的指标标 N/A，不以零分充当改进。

- 意图理解正确率、合法请求最终完成率、约束同时满足率。
- 无关条目/锁定内容保持率、游览事实保持率、虚构 ID 与无依据事实数。
- 冲突正确识别率、歧义正确追问率、未知数据正确披露率。
- 重试重复写入数、迟到提案覆盖次数、恢复内容一致性。
- 提案时延 p50/p95、调用数与用量、游客确认一次修改所需步骤。

必须把未知约束单列为“未验证”；只拒绝所有修改的系统不能靠约束通过率获得高分。硬性安全规则要求零静默覆盖、零跨游客访问；质量与时延指标先测基线再立目标。

## 5. 开发顺序建议

先独立冻结 W01 基线和 K01 内容接口，再做景点目录与版本化快照；随后手动编辑与进度；再接 AI 提案/差异/确认；最后串地图与数字人并做对照评测。W02 通用后台任务、V04 实时 GPS/客流与 W03 导出后续分别推进。

公开实现只作为设计学习来源；本轮未复制其代码或引入依赖。若后续复用代码或数据，需要按对应版本核对许可证与署名要求。
