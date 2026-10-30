# AI 数字人导游技术文档（工作草稿）

> 本稿依据当前集成工作副本的代码、测试和文档整理，供参赛材料核对，不是最终提交版。真实模型、真实设备、PostgreSQL 多 worker 和赛事官方评分及视频规则尚未完成验证；不得将下列设计或自动化测试描述为实际运行成绩。项目名称、参赛团队、场景及截图待补充。

## 一、项目概述

本项目面向景区游客，提供文字、语音和图像交互入口，结合景区知识回答问题，并支持游客保存、编辑行程和确认 AI 修改提案。游客侧还包括地图、讲解和数字人展示；管理侧提供知识和资源管理入口。当前功能边界和实际接口以 `docs/REPO_MAP.md`、`docs/ARCHITECTURE.md` 及对应源码为准。

## 二、需求与设计目标

游客需要快速了解景点信息、依据自身时间和偏好规划游览，并在行程变化时查看修改建议。系统需要将资料来源、游客输入和未知信息区分开，让游客在应用建议前看到变化；服务不可用时应提供可理解的反馈和手动入口。运营人员需要管理可发布的景区资料。需求属于项目设计目标，并非已验证的用户调研结论。

## 三、总体架构

前端采用 Vue 3、Pinia、Vite，数字人使用 Three.js/VRM；后端采用 FastAPI、SQLAlchemy、Alembic，业务服务连接 SQL 数据、检索索引和可配置的外部服务。前端通过 HTTP 和 SSE 与后端交互。见 `frontend/package.json`、`backend/requirements.txt`、`backend/app/api/router.py`、`docs/ARCHITECTURE.md`。

游客提问经 `frontend/src/views/tourist/ChatView.vue`、`frontend/src/composables/useSSEStream.js` 进入 `backend/app/api/chat.py` 和 `backend/app/services/qa/pipeline.py`。流程按实际分支使用 FAQ、缓存、检索、模型及语音服务，不代表每次请求都调用大模型。SSE 传递文字、来源、音频及完成或错误事件。

## 四、AI 与知识方案

知识问答结合 FAQ 和检索结果生成回答；知识发布及可见性由后端知识服务管理，问答链路对发布版本变化进行检查。模型服务由配置决定，未配置真实供应商时存在 stub 或降级路径；检索结果及来源展示不自动证明回答真实，仍需逐条核对。见 `backend/app/services/qa/pipeline.py`、`backend/app/services/knowledge/`、`backend/app/core/config.py`。

视觉识别与最终问答是独立阶段。游客可以从已发布目录选择景点，后端校验站点、景点代码和发布版本后限定检索；未经确认时开放检索并提示。模型线索和用户选择不证明照片识别正确，已发布资料也不自动等同官方资料。提供浏览器语音识别与录音转写：部分转写可确认或修正，浏览器识别和符合自动发送条件的转写会直接提交。语音可通过服务端合成与前端播放。支持与体验受供应商、模型、浏览器权限和设备影响；不得依据接口存在推断真实环境成功。见 `backend/app/api/vision.py`、`backend/app/api/voice.py`、`frontend/src/composables/useRecorder.js`、`frontend/src/composables/useAudioPlayer.js`。

## 五、行程功能实现

游客游览任务保存版本化快照；行程约束包括必去、排除和可用时间。确定性校验识别已知冲突，缺失时长、路段或未解析名称标为未核实；系统没有因此保证实际路网、开放时间或可达性。相关实现见 `backend/app/services/itinerary/mutations.py`、`backend/app/services/itinerary/provenance.py`。

AI 修改先生成提案，后台任务保存状态；系统校验快照、景点目录和版本，游客查看差异并明确确认后才生成新行程版本。服务端重建来源，避免直接信任客户端证据；外部调用结果不确定时要求用户确认重复调用风险。见 `backend/app/services/tool_execution/handlers.py`、`backend/app/repositories/tool_execution.py`、`backend/app/repositories/tour_session.py`、`frontend/src/stores/tourSessions.js`。未核实提案仍可由用户确认应用，应清楚展示其限制。

## 六、测试与部署

测试覆盖示例：`backend/app/tests/test_pipeline.py`、`test_stream_knowledge_integration.py`、`test_itinerary_provenance.py`、`test_tour_progress_and_proposals.py`、`test_tool_execution_acceptance.py`，以及 `frontend/tests/proposal-recovery.test.mjs`。这些测试使用隔离数据或假供应商，不能直接代表真实设备和供应商性能。100 题评测集格式检查和评测脚本单元测试曾在隔离条件下通过，格式通过不等于回答准确；见 `eval/testset/e2e_qa_100.json`、`eval/tests/`。

后端在 `backend/` 目录按照 `docs/DEVELOPMENT.md` 配置数据库、数据与模型后运行 `python -m uvicorn main:app`；持久提案需另启动 `python -m app.services.tool_execution.worker`。前端在 `frontend/` 运行 `npm ci` 和 `npm run dev`。启动可能执行迁移、初始化及模型预热，不能把示例命令理解为所有平台均已验收。真实密钥不得写入文档或提交。

目前知识库按配置使用单站点数据库，不是逐条多租户隔离。W02 迁移的父节点调整以旧迁移未部署为前提，已有数据库须先核查版本和 schema，参见 `docs/development/W02_INTEGRATION.md`。停止浏览器等待并不等于取消服务端任务或撤回供应商调用；不确定的外部结果可能产生重复调用费用。

## 七、特点与局限

本方案将行程建议与用户确认分开，采用版本、幂等和任务状态约束异步操作，并区分发布资料、游客输入及未知信息。这是实现思路，不构成对竞品或创新性的量化比较。

待完成：以固定题集和发布知识版本测试真实模型准确性、引用支持率、费用和延迟；在真实手机和浏览器验证录音、播放、定位及数字人；在隔离 PostgreSQL 验证多 worker 租约与并发；执行浏览器到任务恢复、证据展示和确认的完整闭环。官方赛道评分、视频及附件规则仍需从对应届次组委会原始文件确认。此前历史报告的数字不作为本稿成绩。
