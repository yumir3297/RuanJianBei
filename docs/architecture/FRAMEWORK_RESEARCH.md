# 框架调研（2026-10-30）

本文件是当时的调研快照，并非当前最新版本清单；安装或部署前应重新核对官方发布、许可证和兼容性。尚无本项目真实业务链的框架性能对照。

## 结论

若当前导游链路主要是检索、提示词、生成和流式返回，优先保留 FastAPI 和显式 pipeline，把模型、检索、会话和观测接口解耦；先用实际延迟、失败率和回答质量验证。只有出现跨请求持久执行、人工审批、复杂分支/并行和恢复等需求时，再评估引入 LangGraph；轻量 agent 框架适合需要工具调用和类型化结果但不需要复杂图状态的场景。这个建议是架构判断，未基于本项目代码性能实测。

## 包版本与约束

| 包 | PyPI 信息 | 许可证 / Python | 注意 |
|---|---|---|---|
| [LangGraph](https://pypi.org/project/langgraph/) | 1.2.18 | MIT / >=3.10 | 核心图运行库可独立使用；持久化后端需另配置。 |
| [Pydantic AI](https://pypi.org/project/pydantic-ai/) | 搜索索引存在过期：明确可见 2.62.0，部署前再次查询 PyPI JSON | MIT / >=3.10 | pydantic-ai 与 slim/extras 依赖范围不同，须锁定实际组合。 |
| [OpenAI Agents Python](https://pypi.org/project/openai-agents/) | 0.24.0 | MIT / >=3.10 | 0.x 版本，升级需回归验证；支持其他模型但兼容细节因提供商而异。 |
| [Langfuse Python SDK](https://pypi.org/project/langfuse/) | 搜索索引显示 4.15.4，可能过期 | MIT / >=3.10,<4 | SDK 许可不代表服务端各版本或托管服务许可。 |
| [Ragas](https://pypi.org/project/ragas/) | 页面版本未可靠核实，安装前核对 PyPI | Apache License / >=3.9 | 评测库，不是线上编排替代品；评测模型、成本及结果波动需控制。 |

以上版本是检索时可确认的快照，索引可能缓存；不要据此盲目升级。Python 版本交集至少 3.10，但不能推出传递依赖和现有项目兼容；应在隔离环境解析锁文件并执行集成测试。

## 流式、状态及取舍

- FastAPI pipeline：完全掌控 SSE/WebSocket、取消和业务协议；重试、幂等、状态恢复、事件顺序与观测需自行实现。最容易保留现有契约。
- LangGraph：官方定位为有状态长运行编排，提供流式、持久化、人工介入和 durable execution；生产持久化需合适的 checkpointer 与线程标识，内存实现不能跨进程恢复。图节点重试可能重复外部副作用，业务仍需幂等。见[官方项目](https://pypi.org/project/langgraph/)和[持久化文档](https://docs.langchain.com/oss/python/langgraph/persistence)。引入图状态与运行语义增加学习、迁移和调试成本。
- Pydantic AI：强调类型化工具和结构化输出，支持流式及模型适配；对简单工具调用比图编排轻。消息历史或外部 durable execution 集成不等同自动获得生产级持久恢复，需验证选定后端与中断语义。见[官方文档](https://ai.pydantic.dev/)。
- OpenAI Agents SDK：支持 agent、工具、交接、流式和 session；[流式文档](https://openai.github.io/openai-agents-python/streaming/)明确必须消费事件迭代器至结束，最后 token 后仍可能执行会话持久化；[session 文档](https://openai.github.io/openai-agents-python/sessions/)描述不同后端及压缩。外部模型的工具/流式/结构化输出支持应逐项验收。
- Langfuse 用于链路追踪和评测观察，需处理个人信息脱敏、采样、数据驻留和自托管成本；[官方文档](https://langfuse.com/docs)。Ragas 用于离线检索与回答评测，应结合人工标注基准集，避免把 LLM 评分当作事实真值；[官方文档](https://docs.ragas.io/)。两者可与任何上述编排方案组合。

## 验证建议

固定同一问题集和模型，比较首 token、整轮时延、并发、取消、断线恢复、引用正确率与成本；检查中文流式分句、TTS 衔接、工具超时和副作用去重。锁定版本后验证 Python、Pydantic、模型供应商 API、数据库和 FastAPI 的实际依赖解析；部署时分别审查 SDK、服务端、模型与第三方组件许可。当前未安装运行或进行基准测试，版本及具体集成能力仍须在目标环境复核。
