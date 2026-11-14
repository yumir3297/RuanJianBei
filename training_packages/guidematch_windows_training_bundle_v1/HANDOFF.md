# GuideMatch 训练交接说明

## 1. 当前状态

数据、切分和哈希已冻结，可以开始开发期正式训练。尚未获得独立来源的冻结测试集，因此当前训练结果只能记为“合成开发集结果”。

冻结数据：

| 项目 | 数量/结论 |
|---|---:|
| 全量 | 900 |
| train | 765 |
| dev | 135 |
| train 标签 | reuse 256 / distinct 255 / clarify 254 |
| dev 标签 | 三类各 45 |
| family 跨集 | 0 |
| 近重复簇跨集 | 0 |
| Jaccard ≥ 0.8 跨集近重复 | 0 |
| 最大跨集相似度 | 0.777778 |

## 2. 架构与创新点

可使用的严谨名称：

> GuideMatch：面向导览重复问答归并的约束感知、多任务中文问句对 Cross-Encoder。

模型实现包含：

- **联合语义编码**：将左右问句作为 sequence pair 输入 `BAAI/bge-small-zh-v1.5`；
- **双任务头**：主头预测 `reuse/distinct/clarify`，辅助头预测 `same_target/cross_object/different_subintent/temporal_conflict/missing_reference/ambiguous_target`；
- **风险非对称损失**：对非 `reuse` 样本的 `P(reuse)` 增加惩罚，重点压低危险的错误归并；
- **确定性门控**：结构化硬冲突在生产链路中先判定，模型只负责语义不确定区；
- **阶段化训练**：先冻结编码器只训分类头，再仅解冻最后一个 Transformer block 对照。

这里的“创新”是针对导览知识复用风险的工程组合创新，不应宣称发明了新的基础模型或全新 Transformer 架构。

数据中缺失的 `poi_id` 或 `target_id` 通过“字段不存在”表达，而不是强制写 `null`；校验器与门控均按这一真实 schema 处理。

## 3. 一键流程

`start_training.ps1` 会按顺序：

1. 校验 Python 版本与文件 SHA-256；
2. 创建 `.venv-train`；
3. 从 PyTorch CUDA wheel 源安装锁定的 `torch==2.12.0`；
4. 安装其余锁定依赖；
5. 检查 CUDA 与 GPU；
6. 校验 JSONL schema、标签/原因和 train/dev 隔离；
7. 运行 TF-IDF 文本基线；
8. 对三个 seed 运行 `frozen` 与 `last_layer` 两阶段；
9. 汇总均值、标准差、每类指标、混淆矩阵和错误复用数。

默认配置见 `config/train_config.json`。为保持可复现性，除非有书面实验理由，不要在看到 dev 结果后反复修改参数。

## 4. 验收边界

### 训练包技术验收

- `scripts/verify_bundle.py` 退出码为 0；
- `scripts/validate_data.py` 返回 `passed=true`；
- 能识别 CUDA GPU，且训练过程没有回退 CPU；
- 六个神经模型运行均产生 `metrics.json`、`predictions.jsonl`、`model.pt`、tokenizer 和 encoder config；
- 每个 epoch 产生包含优化器、调度器、梯度缩放器和随机状态的 `checkpoint.pt`；可用 `--resume-from` 恢复同一阶段/seed；
- 汇总报告包含 macro-F1、每类 precision/recall/F1、混淆矩阵、`false_reuse_count`；
- 同一配置的三 seed 结果全部保留，不只展示最高分。

### 开发集建议门槛（不是对外真实性证明）

- macro-F1 ≥ 0.80；
- `reuse` precision ≥ 0.90；
- `distinct/clarify → reuse` 的 `false_reuse_rate` ≤ 0.05；
- 三 seed macro-F1 标准差 ≤ 0.03；
- 末层解冻若没有稳定优于冻结方案，则保留更简单的冻结方案。

### 正式部署前仍缺

- 独立来源的冻结测试集；
- 真实游客问法或至少人工独立编写的盲测集；
- 生产硬规则门控与模型推理的集成测试；
- 推理延迟、并发、置信度阈值和回退策略实测；
- 数据漂移、反馈回流和版本回滚机制。

## 5. 结果解释

- `raw_*` 指纯文本模型预测；
- `guarded_*` 指应用确定性硬规则后的预测；
- 论文/文书必须同时展示 raw 与 guarded，不能只展示更高者；
- 若 guarded 显著高于 raw，说明当前合成数据的结构字段提供了强信号，不能据此夸大语义模型能力；
- 选模型优先看安全指标，再看 macro-F1，不能只追求准确率。

## 6. 常见问题

### 无法访问 Hugging Face

在可联网电脑下载完整 `BAAI/bge-small-zh-v1.5` 目录，复制到 Windows，然后传入 `-ModelSource`。不要只复制单个权重文件。

### `torch.cuda.is_available()` 为 false

检查 NVIDIA 驱动和所装 PyTorch CUDA wheel。训练脚本默认要求 CUDA，会直接失败，避免悄悄用 CPU 跑数小时。

默认 CUDA wheel 源是 `cu128`。如果该电脑驱动只支持较旧 CUDA 运行时，先升级 NVIDIA 驱动；确需改 wheel 源时使用 `-TorchIndexUrl`，并在交接报告中记录实际 URL、Torch 版本与 `torch.version.cuda`。

### 显存不足

先把 `config/train_config.json` 的 `batch_size` 从 16 改为 8，并把 `gradient_accumulation_steps` 从 1 改为 2。不要先缩短文本或删数据。

### 是否可以报告真实准确率

不可以。当前只能报告“同源合成开发集上的结果”。获得独立冻结测试集后，使用 `scripts/evaluate_checkpoint.py` 单次评估，且测试集不得反向参与调参。

续训只从完整 epoch 边界恢复；须使用相同配置、训练/开发数据、阶段、seed、模型来源及设备类型。检查点采用原子替换，且只接受可信来源；本次通过 CPU 小模型中断恢复回归，尚未验证 CUDA。
