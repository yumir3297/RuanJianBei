# GuideMatch Windows 训练交接包

本目录可整体复制到配有 NVIDIA RTX 3060 的 Windows 电脑，并由 OpenCode 或人工一键启动训练。

## 一句话结论

双击 `START_HERE.cmd`（或在 PowerShell 执行 `powershell -ExecutionPolicy Bypass -File .\start_training.ps1`），脚本会校验冻结数据、创建独立虚拟环境、安装锁定的 CUDA 版 PyTorch 与训练依赖，然后依次运行文本基线、冻结编码器训练和末层解冻训练。

## 训练目标

输入两个游客问句，输出：

- `reuse`：可复用同一答案；
- `distinct`：必须区分回答；
- `clarify`：缺少关键范围，需要追问。

训练模型是**约束感知的多任务中文问句对 Cross-Encoder**：

1. BGE 中文编码器联合编码两个问句；
2. 主任务头预测三分类；
3. 辅助任务头预测六类判定原因，约束表示学习；
4. 损失函数增加“把 distinct/clarify 错判成 reuse”的风险惩罚；
5. 景点、对象等确定性冲突仍由模型外的硬规则门控，模型不能覆盖硬冲突。

结构字段不作为神经模型输入，避免模型只读 `poi_id/target_id` 就“猜中”标签造成数据泄漏。

## Windows 最短用法

前提：Windows 10/11、NVIDIA 驱动正常、Python 3.10 或 3.11、可访问 PyPI 与 Hugging Face（或已准备本地底座模型）。

```powershell
cd <本目录>
.\START_HERE.cmd
```

如底座权重已离线保存：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_training.ps1 -ModelSource "D:\models\bge-small-zh-v1.5"
```

完整执行会运行 3 个随机种子。首次下载和安装依赖耗时取决于网络；RTX 3060 6GB/12GB 均可运行默认配置。

训练阶段每个 epoch 会保存 `checkpoint.pt`，其中包含模型、优化器、学习率调度器、梯度缩放器、最佳权重、早停状态和随机数状态。中断后可用以下方式继续同一阶段和 seed：

```powershell
python .\scripts\train_guidematch.py --config .\config\train_config.json --model-source BAAI/bge-small-zh-v1.5 --stage frozen --seed 13 --output-dir .\outputs\runs\frozen-seed13 --resume-from .\outputs\runs\frozen-seed13\checkpoint.pt
```

续训必须使用相同的阶段、seed、底座模型和兼容配置；恢复检查点不等于训练已完成或效果已验证。

## 产物位置

所有结果写入 `outputs/`，包括：

- `environment.json`：Python、PyTorch、CUDA、GPU 环境；
- `data_validation.json`：数据结构、标签分布与切分隔离检查；
- `baseline_tfidf/metrics.json`：TF-IDF 基线；
- `runs/<阶段>-seed<随机种子>/`：模型权重、配置、逐条预测和指标；
- `summary.json`、`summary.md`：多阶段、多种子汇总。

## 数据边界

- 900 条数据全部是合成数据；train 765 条，dev 135 条。
- train/dev 已按 family 与字符 bigram 近重复簇隔离。
- dev 与 train 来自同一生成器，只能用于开发期比较和调参。
- 本包**没有合格的独立冻结测试集**，所以不能据此宣称真实游客准确率或真实场景泛化。
- 正式对外验收前，应补充来自独立来源、完全冻结且不参与调参的测试集。

更完整的执行与验收说明见 [HANDOFF.md](HANDOFF.md)，给 OpenCode 的启动提示词见 [OPENCODE_START_PROMPT.md](OPENCODE_START_PROMPT.md)。

续训只从完整 epoch 边界恢复；须使用相同配置、训练/开发数据、阶段、seed、模型来源及设备类型。检查点采用原子替换，且只接受可信来源；本次通过 CPU 小模型中断恢复回归，尚未验证 CUDA。
