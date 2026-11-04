# Agent 与评测框架调研（核对于 2026-11-04）

版本、维护状态和许可可能继续变化。版本以 PyPI 当前 stable artifact 和各项目官方 release 页面交叉核对；GitHub 已发布但 PyPI 尚未显示的版本单独注明。此为源码与官方资料研究，没有安装候选框架，也没有项目级延迟、成本或回答质量对照。

## 候选包与兼容性

| 项目 | 当前 stable / 最近发布 | 许可与 Python | 对本项目的接口和成本 | 结论 |
|---|---|---|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph) | 1.2.19，GitHub release 2026-10-30 | MIT；>=3.10 | 图状态、分支、streaming、checkpoint；核心包依赖 `langchain-core`。可将现有模型适配器封装为节点，但需把 SSE 事件、取消、checkpoint 状态和外部副作用幂等接入图运行时。 | 若复杂行程链经测量确需跨节点恢复/分支，可做单任务 PoC；目前先不加。 |
| [Pydantic AI](https://github.com/pydantic/pydantic-ai) | PyPI 2.65.0（2026-11-03）；GitHub 2.66.0 tag 于 11-04 出现，PyPI 页面尚显示 2.65.0 | MIT；>=3.11 | typed agent、结构化输出、工具、流式、provider adapters；可适配 OpenAI-compatible Provider。比完整图轻，但替换 `BaseLLMService` 会扩大现有流式与结构化事件的适配范围。 | 适合需要 Agent 决策/类型化工具的边界 PoC；当前问答主链不需要。 |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | 0.24.0，PyPI 2026-10-15；GitHub 有 0.24.0-alpha.6 预览版 | MIT；>=3.10 | 支持 function tools、MCP、handoff、guardrail、streaming 和 session；声明可适配多家模型，但必须验证 DeepSeek 兼容接口和当前 SSE/TTS 事件映射。Alpha 版近期 API 变化明显。 | 多 Agent/handoff 对现有需求没有已证收益；不作为线上默认编排。 |
| [Langfuse Python SDK](https://github.com/langfuse/langfuse-python) | 5.1.0，PyPI 2026-10-30；服务端 4.75.0，GitHub 2026-11-04 | SDK MIT；>=3.11。Server 主仓 MIT，`ee/` 除外。Python v5 要 Langfuse v4.59+。 | OpenTelemetry tracing/evals，不负责请求编排；支持 OpenAI client 与 OTel 接入。需配置服务或账号、敏感字段脱敏、采样、数据驻留和异步导出。 | 可以作为可选观测层，待有测试环境及隐私规则后再接入。 |
| [Ragas](https://github.com/vibrantlabsai/ragas) | 0.4.3，PyPI 2026-01-13 | Apache-2.0；>=3.9 | 离线 RAG/回答评估；包本身带 datasets、LangChain 生态等依赖，不应进入在线问答依赖。模型裁判需人工标注样本校准。 | 用于离线实验的候选，不是 Agent 或运行时框架。 |

本仓库 README 声明 Python 3.13+；`backend/requirements.txt` 固定 FastAPI 0.116.1 和 Pydantic 2.11.7，但仓库尚未以 `requires-python` 声明最低版本。上述候选的 Python 版本均覆盖 README 声明版本；仍需在目标环境解析完整依赖，不能据最低版本推断依赖组合兼容。

## 架构比较

### A. 保留 FastAPI 显式 Pipeline，逐步拆出有明确边界的业务节点

保留目前可用的 FAQ、缓存、RAG、证据、SSE、TTS 和错误回退。已有 `QAPipeline` 仍控制简单问答快速通道；确定性路线和受众解析已拆为独立模块，多模态确认目录与检索范围正在拆为 `vision_evidence` 节点。成本是路由状态、取消和事件顺序仍需本项目维护。

### B. 局部采用 LangGraph

只把确有多分支、需要检查点恢复或人工审批的复杂任务放入图中，简单 FAQ/缓存继续走原链。这样可以保留流式问答，同时为复杂工作流增加状态可观察性；代价是双重编排模型、额外依赖以及图状态与现有任务/事件状态之间的同步。

### C. 局部采用轻量 Agent SDK

Pydantic AI 或 OpenAI Agents SDK 可为工具调用和结构化结果提供现成循环。代价是现有 `BaseLLMService`、多 Provider 行为、事件协议和任务持久化必须逐项适配；工具函数自身并不因此成为 Agent。

**当前选择 A。** 真实代码中，复杂行程提案已由持久化 worker 负责任务执行与用户确认，普通问答主要是确定性路由、知识检索和流式生成。尚无项目实验显示 B 或 C 能提升约束满足率、恢复成功率、来源忠实度或端到端时延。先继续按业务职责拆 Pipeline；若接下来有一条跨多步骤、需恢复或需人工确认而现有 worker 难以维护的真实任务，再以固定输入做 B/C 单链路 PoC。PoC 只有在复杂任务收益明确且简单问答、SSE、TTS 与取消不回退时才扩大。

这是一项基于源码结构和现有自动化测试的架构判断，不是框架性能结论。上述版本、依赖及许可需在真正加锁前重查；模型和托管服务的许可不由 SDK 许可证覆盖。

## 验证门槛

框架 PoC 与当前实现用相同问题集、数据、Provider、机器和并发测量：简单问答 P50/P95、首 Token、完整回答、语音首响、来源绑定、事实忠实度、复杂任务约束完成率、工具错误率、取消/恢复、token 与 API 成本。Ragas 可辅助离线评分，但需保留人工核对；Langfuse tracing 仅在脱敏和数据驻留可接受时启用。没有基线与真实 Provider/设备结果时，不报告性能收益。
