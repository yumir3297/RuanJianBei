# 数据血缘与冻结信息

## 来源

本包数据来自 GuideMatch 合成数据集 `guidematch-synthetic-v1`。原始批次为 `data/source/batches/b01.jsonl` 至 `b09.jsonl`，合并源文件为 `data/source/pairs_train.jsonl`。

生成约束与提示词快照保存在 `references/synthetic_data_prompt.md`。质量报告保存在 `data/reports/`。

## 冻结哈希

- `pairs_train.jsonl`: `a82cc9a5ecd8ca71af6f0239928a321af413cc3d7c8b79d81eb470b850eadcfa`
- `train.jsonl`: `f2cdd124a8de68a108506748c0fc9f62e70e4614d3173d49eff3ceee9dfd1578`
- `dev.jsonl`: `914d5262a9f39e4b9a55f872206489ce8c9a68730a741a3d31605ae589436866`
- `cluster_assignments.json`: `acba7a6372e96bc0f820641622d176ceb5013847a771d1e81a157cb03496a0ef`
- `split_builder.py`: `b8d727b92c1f8c5c4a77de74b1119a704076b0e2d940b87abdce1d0d2f90ab47`

完整包内文件校验见 `CHECKSUMS.sha256`。任何数据文件哈希变化都应停止训练并查明原因，不能自动接受新哈希。

## 切分方法

使用 `family_id + 规范化字符 bigram Jaccard` 构建 union-find 近重复簇，阈值 0.8，再整簇放入 train 或 dev。固定 seed 为 `guidematch-synthetic-v1-r2`。切分实现快照为 `data/splits/split_builder.py`，详细统计见 `data/splits/split_manifest.json`。

## 明确限制

数据全部由同一套生成逻辑构造。近重复隔离降低了直接泄漏，但不消除生成器风格、模板和场景范围偏差。当前 dev 是开发集，不是独立测试集。
