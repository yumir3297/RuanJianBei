# Eval 目录说明

该目录用于维护景区问答评测、检索质量回归和延迟统计。

当前首版骨架包含：

- `testset/`：FAQ、知识问答、推荐的样例题集
- `metrics/`：准确率、延迟、检索质量的占位实现
- `scripts/`：统一回归入口和测试集构建占位脚本

后续修改以下内容时，建议同步跑回归：

- 分块策略
- 检索策略
- Prompt 模板
- 重排逻辑
- 模型接入方案

## 当前离线工具检查

2026-10-31 在集成提交 `deed34a` 的本机 Python 环境运行：

- `python -m pytest -q -p no:cacheprovider eval/tests`：16 passed。
- `python eval/scripts/check_e2e_testset.py --testset eval/testset/e2e_qa_100.json --report /private/tmp/guide-eval-validation-current.json`：100 题，格式错误 0；题集 SHA-256 为 `243992e2474a0cb5452e8c0e63a852c880724411a86bc397f90d7a73a30978fb`。

以上仅验证评测工具与题集格式，没有运行真实模型、测量回答正确率或确认题目资料权威性。题集依据、人工标注和真实服务的测量程序见 [人工核验](HUMAN_REVIEW.md)。报告写在临时目录，不覆盖仓库中的历史报告。

后续更新：流完成检查要求 HTTP 200、明确的 `done.completion=complete`，且没有 `error` 事件；不完整或缺少完成状态不能通过。更新后的评测工具测试 19 passed。旧报告沿用旧口径，不应与新报告直接对比。


## 可重复的端到端抽样

`eval/scripts/run_e2e_chat_eval.py` 默认仍为 `dry-run`；默认 `--sampling head` 保持题集顺序，`sampled-real` 未指定 `--limit` 时仍取前 5 题，`local-server` 默认执行全部题目。默认 dry-run 始终校验并报告整个题集（沿用忽略 `--limit` 的行为）。前 5 题是顺序子集，不是随机或类别代表样本。

可显式使用 `--sampling stratified --seed 37`：按题目 `category` 分层，先按类别和 ID 排序，再使用独立种子随机打乱类别顺序与类内题目，每轮从每个未耗尽类别取一题。该方法优先均衡类别覆盖，不是按原题集比例抽样；样本数小于类别数时无法覆盖所有类别。默认种子为 0，同一有效题集、参数及相同 Python 随机实现下可复现选中 ID 和执行顺序；不依赖输入行序，也不改变全局随机状态。

先离线预览 100 题集中的 16 题（8 类各 2 题）：

```sh
python eval/scripts/run_e2e_chat_eval.py --mode dry-run --testset eval/testset/e2e_qa_100.json --sampling stratified --seed 37 --limit 16 --report /tmp/e2e-sample-preview.json
```

真实对照时显式指定端点和网络授权；以下命令会发送真实请求，可能产生模型费用：

```sh
python eval/scripts/run_e2e_chat_eval.py --mode sampled-real --testset eval/testset/e2e_qa_100.json --sampling stratified --seed 37 --limit 16 --endpoint http://127.0.0.1:8000/api/chat/stream --allow-network --report /tmp/e2e-sampled-real.json
```

报告和终端输出的 `selection` 记录算法版本、种子、请求/实际题数、完整及选中类别分布、未覆盖类别、按执行顺序的题目 ID 和原题集文件 SHA-256。实际请求与报告使用同一份已选题目，避免两处独立抽样造成错配。默认 head 模式的 seed 为 null，表示种子没有生效。先校验完整题集，再选择子集；非法类别不能通过抽样被隐藏。

比较两次真实结果时核对题集 hash、选中 ID/顺序、端点及服务/模型配置，保留报告。均衡子集的未加权准确率不能直接等同于完整题集按原类别占比的准确率；首题冷启动与其余 warm 延迟继续由现有报告分别统计。dry-run 和 MockTransport 测试不证明真实服务质量。
