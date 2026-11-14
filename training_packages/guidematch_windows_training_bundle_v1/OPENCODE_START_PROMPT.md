# 给 Windows OpenCode 的启动提示词

请完整复制下方内容作为 OpenCode 的第一条任务：

---

你现在接手 GuideMatch 的 Windows GPU 训练包。当前工作目录就是训练包根目录。请先完整阅读 `README.md`、`HANDOFF.md`、`config/train_config.json` 和 `data/splits/split_manifest.json`，然后完成训练，不要跳过数据与哈希校验。

目标：在本机 NVIDIA RTX 3060 上，一键完成 TF-IDF 基线、冻结编码器三随机种子训练、最后一层解冻三随机种子训练，并生成完整汇总报告。

执行要求：

1. 先运行 `powershell -ExecutionPolicy Bypass -File .\start_training.ps1`。
2. 若底座模型已在本机，改用 `-ModelSource "底座模型完整目录"`；若可正常访问 Hugging Face，保持默认 `BAAI/bge-small-zh-v1.5`。
3. 允许修复 Windows 路径、依赖安装、显存配置和脚本中的真实兼容性错误；禁止修改 `data/` 内容、标签、切分、哈希清单或为了提高 dev 分数而重写数据。
4. 如果显存不足，只把 batch size 调为 8、gradient accumulation 调为 2，并把改动写入结果说明。
5. 不得把 CUDA 失败后静默回退 CPU；先修复 CUDA 环境。
6. 训练完成后检查每个运行目录都有 `metrics.json`、`predictions.jsonl`、`model.pt`，再运行 `scripts/aggregate_results.py`。
7. 最终向我汇报：GPU 与环境版本、实际命令、数据哈希验证结果、各阶段三 seed 均值和标准差、每类 precision/recall/F1、混淆矩阵、错误复用数、耗时、最佳与最稳定方案、所有输出路径、未完成事项。
8. 结论必须写明：目前 dev 与 train 同源且均为合成数据，结果不能证明真实游客泛化；没有独立冻结测试集时，不得宣称真实场景准确率。

除非出现必须由我选择的外部条件（例如完全无法获得底座权重），否则请自行排错并持续执行到训练和报告全部完成。

---
