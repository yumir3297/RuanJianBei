# GuideMatch 训练资产整合记录

## 当前状态

用户确认训练已完成；当前本地试接入使用下述 seed 13 候选权重，来源报告称已在 CUDA 机器训练。训练完成情况和独立真实评测尚未由本次复现验证。本次从 GuideLoop 工作区复制 `training_packages/guidematch_windows_training_bundle_v1/`，保留代码、冻结的合成数据、配置、Windows 启动脚本与校验清单；来源目录未修改。该 Windows 训练包中未发现权重，另一个交接包包含候选权重。

包声明 Windows 10/11、NVIDIA CUDA、Python 3.10/3.11；冻结训练集 765 条和开发集 135 条均为同源合成数据，没有独立真实测试集。实际训练需要其底座模型与 CUDA 环境，当前本机未运行训练。

## 续训限制

当前脚本在每个完整 epoch 保存原子替换的 `checkpoint.pt`，包含模型、优化器、调度器、梯度缩放器、最佳结果和 Python/NumPy/PyTorch 随机状态。恢复时核对配置、训练/开发数据哈希、模型来源、阶段、seed 与设备类型。CPU 小模型中断后恢复与不间断运行的权重一致；中断发生在 epoch 内时从上一个完整 epoch 重跑。CUDA、真实底座模型及真实训练尚未验证。只加载可信检查点，且相同远程模型名称不保证远程权重未变化；建议使用固定版本的本地底座。

## 验证与文档

2026-11-12：`python3 scripts/verify_bundle.py` 校验 40 个文件通过；`python3 -m unittest discover -s tests -p 'test_*.py'` 通过 2 项。它们只验证交接包完整性及数据约束，不验证 CUDA 训练、训练完成或模型质量。原始使用说明在训练包 `README.md` 和 `HANDOFF.md`。PyTorch 的训练状态恢复要求见 [研究记录](RESEARCH.md)。

2026-11-13：CPU 合成小模型中断恢复回归通过，包含配置变化拒绝；这不证明 CUDA 训练或模型质量。

## 另发现的候选权重与交接包

2026-11-13 再次清点时，在 GuideLoop 来源工作区发现另一份 `training_packages/guidematch_mainline_handoff_20261112/`，其中 `models/guidematch_final/model.pt` 约 93 MiB；它不属于上面 Windows 训练包。该文件的 SHA-256 与交接包清单及说明中的 `c999999e8f78149bdfdbb9830a4590b43046c0e47e79c05a363cf2c0a0d0842e` 一致。当前 GuideLoop 来源 132 个未跟踪文件及补丁已另存于工作目录 `source-snapshots/guideloop-refresh-*` 并核对普通文件哈希，旧快照保留。

来源报告称该候选来自 seed 13，曾在另一台 CUDA 机器训练、校准和测试；这是交接材料的历史陈述，本机尚未加载或复现。报告也说明无独立真实游客测试集、许可和并发长稳等问题，阈值按同源合成开发集选取，不能据此声称真实场景效果。所谓“主线接入”指来源 Windows 工作区，不代表当前集成库。该候选是否适用于比赛应先核对当前 FAQ/RAG 接口、失败回退、安全约束及运行设备，并在隔离环境验证；不覆盖用户尚未完成的训练任务，也不自动启用或将权重提交到仓库。

### 2026-11-13 静态兼容核查

| 项目 | 当前集成库与候选的差异 | 接入前条件 |
|---|---|---|
| FAQ 路由 | 集成库经 `AnswerKnowledgePathResolver` 和 `faq_path_resolver` 处理 FAQ、缓存与可见性；候选快照在旧 `QAPipeline` 中直接插入门控 | 在现有解析链内设计门控，保留知识版本、作用域和缓存边界，不能整文件覆盖 |
| 候选输入 | 候选依赖 FAQ 匹配别名、查询/条目结构化元数据；当前 `FAQMatchResult` 未暴露匹配别名，现有语义门控也未提供快照中的元数据接口 | 明确 exact/fuzzy/semantic 的候选来源、缺失字段与日期语义，覆盖无法取得候选的行为 |
| 设备和加载 | 候选默认要求 CUDA；本机实际 `torch.cuda.is_available()` 为 false、MPS 可用，但候选没有 MPS 路径。来源加载使用 `torch.load(..., weights_only=False)` | 不在本机伪称模型已运行；隔离核查可信权重格式与安全加载，目标设备上测推理、超时和降级 |
| 回退 | 来源报告称不可用时回原 FAQ/RAG，可能失去模型门控；当前链路已有确定性语义约束 | 明确不可用或异常时的安全策略，测试不误复用、提问澄清、可见性与流式事件 |
| 质量 | 来源复用同源合成开发集调参，日期元数据路径未接通，报告列出不同子意图误复用 | 使用独立样例和真实人工审核资料，单独验收不同对象、日期、子意图、缺失字段与误复用，不把历史分数当作本机结果 |

上述静态核查时，比赛本地演示保留原 FAQ/RAG 路径，候选权重仅保存；后续本地试接入见下一节。

## 本地实际链路接入（2026-11-14）

本次在现有 FAQ 解析器接入可选门控：仅 development/test 显式设置 `GUIDEMATCH_ENABLED=true` 和 `GUIDEMATCH_MODEL_DIR=<包含 model.pt、tokenizer、encoder_config 的目录>` 时启用；精确 FAQ 保持原路径，模糊及语义候选使用对应别名与查询进行推理。默认要求 CUDA；本机比赛演示显式设置 `GUIDEMATCH_DEVICE=cpu`。模型返回 distinct 或 clarify 时不复用该 FAQ，继续现有检索；目前不向游客直接输出澄清问题。启用期间禁用共享答案缓存读取，避免绕过门控。加载或推理失败时禁止非精确 FAQ 复用，转入现有检索；生产不会启用此门控。权重以 `weights_only=True` 加载，需本机安装兼容的 PyTorch/transformers。

来源版的结构化景点、对象和日期冲突及单侧缺失规则已实现。FAQ 候选路径现把已有 FAQ 索引能够识别的景点和意图传入规则；跨已知景点、不同已知意图或一侧缺失时，在模型推理前阻止 FAQ 复用，并有路径级测试。该信息是从 FAQ 索引派生的，不等于已核验的景点 ID；未知或两边都缺失仍无法由这条规则判断。日期使用文本中明确的日期词差异保守拦截，不是完整日期解析，也没有把服务端结构化日期传入。用户确认比赛阶段采用现有模型，真实资料与独立评测仍待验证。

隔离 SQLite、合成 FAQ 和本机真实 HTTP/SSE 检查：FAQ 为“从门口到大佛要走多久？”，提问“从门口到灌浴要走多久？”时，关闭门控错误返回该 FAQ，开启后不返回该 FAQ；原问题精确匹配两种模式均返回。两种模式 HTTP 200 且 SSE done；这不是完整真实游客质量验收。

对同一 135 条曾用于开发的合成 dev 问句对做单候选 FAQ 路由前后对照：distinct 45 条中，误复用从 30 降至 1；clarify 45 条中，复用从 22 降至 0；reuse 45 条中，复用从 26 降至 21。未命中 FAQ 的样本不调用模型，指标只衡量 FAQ 复用决策，不衡量后续 RAG 答案正确率；该开发集反复用于训练选型，结果有偏差。可用 `backend/scripts_compare_guidematch.py --model-dir <目录> --pairs <jsonl>` 复现。相关 FAQ、pipeline 和门控回归 61 项通过。真实游客独立评测、结构化硬规则、并发/延迟及许可证仍待完成。

后续加入保守文本日期拦截并按交接配置恢复低阈值分支后，同一数据集复测：distinct 误复用仍为 30→1，clarify 为 22→0，reuse 为 26→18；对应 FAQ、pipeline、结构化规则与异常回退回归 71 项通过。seed 13 的 8 个模型文件已从来源交接包复制到集成工作区 `.cache/guidematch/seed13` 并逐文件哈希比对；该缓存被 Git 忽略，换机器需另行按交接包恢复。统一本地演示脚本显式开启 CPU 并在启动前实际加载权重。

接入 FAQ 索引中的可识别景点/意图后，相关回归为 72 项通过；路径级测试确认跨已知景点在模型之前被拒绝。同一 135 条合成数据再次运行得到相同计数（distinct 30→1、clarify 22→0、reuse 26→18）；该单候选基准的分类均为 general，不代表景点索引硬规则在真实数据上的覆盖率。

换机器可从可信的原交接包恢复模型：`python scripts/install_guidematch_model.py <交接包>/models/guidematch_final`。安装器校验固定的 8 项 SHA-256，写入本仓库 `.cache/guidematch/seed13`；已存在时只检查，不覆盖。隔离目录验证了首次安装、重复校验和损坏文件拒绝；模型文件本身不进入 Git，交接包仍须另行保存和传递。

真实服务的开关对照现可重跑：从仓库根目录使用本项目 Python 执行 `GUIDEMATCH_MODEL_DIR="$PWD/.cache/guidematch/seed13" python backend/scripts_guidematch_api_smoke.py`。脚本新建临时 SQLite、启动两次本机 API，并检查模型加载异常日志和 SSE；不能替代真实资料评测。本机四个开关/问题组合均通过。

### 2026-11-13 隔离 CPU 加载冒烟

在独立进程中以 `torch.load(..., map_location="cpu", weights_only=True)` 成功读取候选，顶层包含 `state_dict`、`labels`、`reasons` 和 `metadata`；使用来源快照的模型结构严格加载状态字典，再使用本地 tokenizer 对两组合成问题做 CPU 前向推理，输出形状分别为 `(2, 3)` 和 `(2, 6)`，数值有限。两组预测分别为 `reuse` 和 `distinct`，仅证明这两次调用可以运行，不能据此推断准确率或安全性。未执行来源的 `weights_only=False` 加载路径，未改其默认 CUDA 限制，也未接入当前问答链路；CUDA、延迟、并发、独立评测和真实资料仍待验证。实际部署仍需验证输入、权重完整性、资源限制及失败回退，不能把受限加载当作完整安全保证。

GuideLoop 来源中另有评测脚本、fixtures、历史结果截图、xlsx 收集表和候选模型包。评测脚本与 fixtures 已纳入当前集成库；`eval/results/`、`outputs/`、xlsx 收集表和未验收的大体积候选权重保留在来源快照/私有归档，不作为运行时或生产发布资产。
