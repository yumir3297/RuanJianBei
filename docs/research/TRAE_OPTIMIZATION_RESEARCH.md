# 检索、评测、语音与数字人优化研究来源

Trae 主仓库 `docs/optimization/` 留有五份未跟踪的研究方案，分别对照 RAGFlow、Ragas、Pipecat、TalkingHead 和 FastEmbed/ONNX。下文保留其目标、参考和验证方法；来源文档的代码基线与版本为历史快照，本次未重新验证外部源码或将方案整体接入主线。原始文件仍在 Trae 来源工作区。任何预期收益、阈值或赛题权重均不能当成已测成绩或已核实官方要求。

| 方向与来源 | 可供后续研究的想法 | 需要核验的边界 |
|---|---|---|
| [RAGFlow v0.27.2](https://github.com/infiniflow/ragflow/tree/v0.27.2) 检索与引用 | 比较向量与词项召回、候选重排、分块定位和句子到证据的关联 | 不直接混合不同分数尺度；引用标记或相似度不能证明事实受证据支持；结合现有发布 revision 与可见性重新审查 |
| [Ragas 固定版本](https://github.com/vibrantlabsai/ragas/tree/298b68274234c060deacab3cf5fb52aa3a20e885) 评测 | 区分回答忠实度、相关性、上下文精确与召回，并保留逐条判断依据 | 模型评审有偏差和成本，`1 - faithfulness` 不能直接当作事实幻觉率；须用独立人工标注校准并报告未知与失败 |
| [Pipecat](https://github.com/pipecat-ai/pipecat) 语音交互 | 研究播放中主动打断、取消传播、首音延迟和只记录可靠播放内容 | 当前录音与播放交互、供应商取消语义须按现有代码验证；VAD、常开麦克风与自动断句均需权限、误触和真机验收 |
| [TalkingHead 固定版本](https://github.com/met4citizen/TalkingHead/tree/2afe6d79779313db8909badebf46f9805a6c7b70) 数字人 | 对比口型过渡、文字/语音时间线、眨眼与手势的表现 | 不将文本驱动说成真实音频驱动；模型与动作各自许可、中文音素、设备同步和人工评价均需核验 |
| [FastEmbed 固定版本](https://github.com/qdrant/fastembed/tree/de502ca83baa2b81922cb5a46acf689f5e2c72a1) 与 ONNX | 比较加载策略、线程和可选推理引擎对冷启动、内存与延迟的影响 | 不假设换引擎或量化后向量可直接混用；检查模型许可、维度/归一化/检索质量与索引重建，保留失败回退 |

开展对照时应固定代码、资料和发布版本、题集、模型、硬件、缓存状态及并发；分别报告检索指标、人工核对的事实与引用、首字/首音、失败率、资源和费用。逐句引用和自动评分只提供核查线索，不能取代人工事实审核。具体主线实现以[代码地图](../REPO_MAP.md)、[评测方法](../../eval/HUMAN_REVIEW.md)和[验收总表](../testing/TESTING_AND_ACCEPTANCE.md)为准。
