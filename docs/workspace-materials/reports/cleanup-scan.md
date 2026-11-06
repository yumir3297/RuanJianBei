# Documentation & Legacy Cleanup：只读扫描

日期：2026-10-30。阶段：识别与引用分析；等待主 Agent 稳定集成基线。**没有删除、修改业务文件、创建分支或提交。** 本报告是唯一写入文件。

## 原提示词已找到

证据：通过 read_thread 读取聊天 `01a18b79-4451-7840-94cf-98eac2bf5aca`（标题“0 旧账清算”），返回唯一完整回合、hasMore=false。用户原文明确要求“历史设计文档与废弃前端清理”，范围涵盖旧 UI/UX、旧执行提示、比赛目标、替代架构、过期计划、已废弃源码及资产，全仓扫描。

核心约束：先只读、记录 Git/Worktree/Commit；主 Agent 有效分支合并前不删除；稳定后在独立分支/worktree 精确删除并修复引用。活跃前端、有效后端、在研功能、配置与锁文件、数据及主 Agent 架构文档不得修改。旧源码必须核对入口/import/路由/构建/运行及测试；无法确认只报告。最终交付应为独立分支 `docs/maintenance/legacy-cleanup-report.md` 与可恢复 commit。此前聊天只做粗扫，未完成引用分析或删除；其 Documents 路径不是本次目标，不能沿用为基线。

## 只读基线

已读取项目根、code/RuanJianBei 根及前后端 AGENTS，及 integration-work/main/AGENTS。

- 主代码目录 `code/RuanJianBei`：HEAD `672a104ff81c50047dff5327ca317b5e3c332eb1`，分支 codex/repository-map；大量已修改与未跟踪业务/测试/设计文件，不能当作可清理基线。
- 同 Git 的 worktree：w02-integration 与 v01-worktree 为 `098553f34cf4991240742661c4174e41f60ef0c6`；w02-worktree 为 `a8c283771e3176f3c05fb95ef76631f57566bc15`；另有 `/private/tmp/ai-guide-phase3` 已标 prunable。未修复或 prune。
- 新集成副本 `integration-work/main`：读取时 HEAD `e115eab60502dcd37fa134b5411cd459cee60552`，detached 且 status 无变更。是否已完成有效合并由主 Agent 确认，本报告不据此自行删除。

使用 rg --files、关键词搜索和源码读取，覆盖仓库 docs 之外 scripts、frontend/public、views、data/raw；额外检查 hidden/no-ignore 文档名单，排除 .git、node_modules、.venv、dist、模型索引及缓存备份目录。sources 完全保持只读、未当作删除目标。未打开业务数据库、真实 .env 或执行产物生成脚本。二进制资料仅按文件名/引用辨认，未审读内容；缓存/本机备份不视作可提交清理目标。

## A：确认失效的历史设计记录（稳定后优先删除候选）

以下明确属于 2026-10-03 迭代记录，已被同组后续记录及当前源码状态替代；仓库内按完整文件名搜索未发现外部入口引用。仍须在最终集成树重查链接。

| 文件（仓库相对） | 证据与理由 |
| --- | --- |
| docs/design/frontend-design-review-2026-10-03.md | 正文自称“本轮尚未执行页面样式改造”、下一版提案；同目录后续记录已实施这些变化。不能继续作为待开发要求。 |
| docs/design/avatar-center-layout-2026-10-03.md | 同文件先取消背景遮罩、后描述白字粗阴影等历史阶段；scenic-surfaces 明确因该版本视觉零碎而重构。固定 240/260px 与当前窗口地图布局不能等同。 |
| docs/design/scenic-surfaces-2026-10-03.md | 一次历史样式调整/截图记录，含旧构建耗时和本机 .tmp 证据，当前地图布局已另有 2026-10-29 验收；不是当前需求入口。 |

A 表仅表示文档内容与现有引用证据支持优先清理，不代表本轮已删除、构建验证或主 Agent 已确认新需求。

## B：过期但存在引用（成组处理或替换引用后删除）

| 文件 | 当前引用/风险 |
| --- | --- |
| docs/superpowers/plans/2026-10-04-geolocation-audio-guide.md | 内含个人 Windows 绝对路径执行示例；10-05 分众计划引用链路范式。不能单文件删除留断链。 |
| docs/superpowers/plans/2026-10-05-分众化讲解与跨会话记忆.md | 旧实现计划与历史复核相互链接；实际 audience/memory 已有代码与测试，旧未勾选步骤不能当作当前待办。 |
| docs/superpowers/plans/2026-10-05-分众化讲解与跨会话记忆-可行性验证报告.md | 包含历史失败数量、未提交 coze/live_data 清理及耗时估计；被上项引用，地图明确历史测试报告不代表当前基线。 |
| docs/superpowers/specs/2026-10-04-geolocation-audio-guide-design.md | 上述两计划依赖，需将整组历史链重查后处理；保留当前 MapView/useNarration/guide.py 实现。 |

## C：旧前端实现候选（未获构建和运行依据，暂不删除）

| 文件 | 已核实/剩余验证 |
| --- | --- |
| frontend/src/views/HomePage.vue | router/index.js 没有加载；全仓按名称搜索仅地图说明命中。当前 `/` 与 welcome/select 重定向至 TouristView → ChatView。尚未对最终集成树做构建、测试及预览。 |
| frontend/src/views/LandingPage.vue | 同样没有路由加载，保留自身 ThreeAvatar/背景等共享依赖，不能跟随候选连删依赖。 |
| frontend/standalone-login.html | frontend/一键启动前端.md:48 明确提供双击预览入口；非 import 不等于无用途。需替换或移除该说明并确认独立预览是否仍需要。 |
| frontend/public/map-tester.html | public 静态直达页面不需要源码 import；可能用于地图验收，尚未确认退役。 |
| frontend/public/motion-tester.html | 动作调试页面通过 `/motions/` 动态加载；可能用于模型动作验收，不得因无路由误删。 |

当前无 C 类达到用户要求的构建+运行+测试证据。未运行构建或测试，因为此阶段禁止写业务工作区且稳定基线仍在形成。

## D：明确保留

- `AGENTS.md`、`README.md`、`docs/REPO_MAP.md`、`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT.md`、`docs/COMPATIBILITY.md`、`docs/REPO_MAP_USABILITY.md`：现行导航、架构及验证入口。架构归主 Agent。
- `docs/plans/2026-10-27-feature-roadmap.md`、`docs/plans/2026-10-28-ai-workbench-backlog.md`：AGENTS/地图仍指向，不能因时间较早当作失效比赛目标。
- 10-27/28/29 的 K01/W01/W02/V01、流式、共享播放、幂等、非 WAV、安全、语速、重播、profile 设计/计划/研究与验收资料，以及 selling-points：含正在整合或刚实现功能；逐项有效性待主 Agent 审计，不能按目录一刀切删除。
- TouristView/ChatView/MapView/RouteView/ExploreView/QuizView、ThreeAvatar/AvatarDisplay、设备 composables：当前实际路由或 ChatView 工具/降级链路。
- `frontend/public/assets/slides/*`：touristCatalog.js 显式引用；`assets/bg-scenic.png` 被 style.css/useScenicBackground 引用；models/motions 被预设与 ThreeAvatar 动态加载。不能根据旧 LandingPage 候选连带删除。
- `data/raw` 的两份 DOCX 属业务知识数据，排除删除；eval 和 evaluation 虽名称相近，地图区分评测用途，不能凭名称断定重复。
- `scripts/competition_check.ps1`：地图仍将其列作 Windows 检查入口。比赛命名不是废弃证据。
- 所有 sources、备份 Git 镜像、其他 worktree 和未跟踪业务改动。

## E：待主 Agent 当前需求确认

| 文件 | 保留理由/确认点 |
| --- | --- |
| DESIGN.md | 现存是通用景区/中央数字人/可访问性规范，并非原先灵山比赛视觉目标；旧 review 引用它。主 Agent 尚未发布替代设计要求，不能认定整份废弃。 |
| docs/superpowers/specs/2026-10-02-multi-scenic-guide-proposal.md | 现路线图:42 明确保留其隔离与配置设计参考，属于需求/架构范围，交主 Agent 决定；不可自行删。 |
| docs/superpowers/plans/2026-10-28-repository-map.md | 地图实现历史计划，可归档/删除候选；需稳定后确认主 Agent 是否仍依此验收。 |
| scripts/build_product_design_docx.py | 写入“软件杯提交物/…/产品设计文档”；源码树未列出其 Markdown 输入，疑为旧提交物生成器。不得运行来验证，它会写产物；比赛交付是否退役未确认。 |
| scripts/build_work_description_pdf.py、build_deployment_docx.py、build_revision_reinforcement_doc.py、extract_competition_data.py、render_pdf_contact_sheets.py | 与比赛资料/文档产物相关，需逐个读依赖、确认交付职责及输入；目前仅识别，尚无充分删除依据。 |
| docs/superpowers/plans/2026-10-28-k01-stream-integration.patch | 未跟踪且与当前 K01 整合有关；稳定后比较已吸收内容再决定，不能提前删除。 |
| .superpowers/sdd/*/progress.md | 本机执行进度，可能未纳入 Git，不能当作已提交遗留内容盲删。 |

## 后续工作与交付门槛

等待主 Agent 指定最终稳定 commit；随后创建独立 cleanup worktree，仅对已确认 A/B 文档和经过验证 C 文件逐路径处理，修复有效入口断链。禁止修改配置、锁文件、数据、有效代码及主 Agent 架构。

在 cleanup worktree 运行仓库要求的地图检查、scripts/tests、git diff --check；若删除前端源码/资源则运行 npm test、npm run build 并检查实际入口及调试页用途。当前报告仅有静态引用依据，没有声称测试通过。最终报告补删除清单、修复引用、保留理由、实际命令与 commit；本轮清理 commit：无。


## 2026-10-30 更新：独立清理实施准备（未执行）

本节更新前面的扫描快照。**当前仅准备计划；未删除、未创建 worktree/分支、未修改 integration-work/v01 或原始 code 目录。本回合唯一写入是本报告。** 前述播放器冲突与 W02 前端任务为主 Agent 单独授权的集成工作，已经交还；不属于本节清理操作。

### 基线与启动条件

本次只读确认 `integration-work/v01` HEAD 为 `ec3f7a646e7caec70fa00bcae1f897f7c7b22deb`，分支 `codex/competition-integration`；工作区仅 `?? frontend/node_modules`。该依赖入口不属于清理，不提交、不删除、不修改其目标。worktree list 目前仅此集成副本。主 Agent 报告自动化已通过，但真实运行验收仍在进行；**自动化通过不能替代稳定集成确认，清理继续等待。** 若真实验收产生新提交，实施前重新记录新 HEAD、工作区、引用及内容 hash，不能直接照本表删除。

### 精确文档删除清单：7 文件，单独文档提交

下面是准备交给稳定后独立清理 worktree 的 allowlist，除此以外的文件不加入删除。它包括 A 三份旧 UI 迭代记录与 B 四份相互引用的历史实施资料。若基线中的任一 hash 不同，先重读与重查再决定。不是当前删除批准，也未形成清理 commit。

| 序号 | 仓库相对路径 | 跟踪/内容证据 | 逐项引用影响及处理 |
| --- | --- | --- | --- |
| 1 | `docs/design/frontend-design-review-2026-10-03.md` | 已跟踪，5012 bytes；SHA-256 `ab41e4850738a9322ae371f9159ffee32dbe082dc9c3a5fa1e7b85cea3cbcad6` | 没有外部文件名/路径引用；正文引用 DESIGN.md，删除引用源不需要修改被引用文件。 |
| 2 | `docs/design/avatar-center-layout-2026-10-03.md` | 已跟踪，6361 bytes；SHA-256 `2d158f9c47d5985802fcb9cc1db77761b106ce963163aa2a0543aac0cfd421ff` | 没有外部文件名/路径引用；含旧 .tmp 截图/备份说明，既不追删 .tmp，也不删当前组件。 |
| 3 | `docs/design/scenic-surfaces-2026-10-03.md` | 已跟踪，3517 bytes；SHA-256 `23a78a4b40b1554111cdbc6ed0a143aad3f3bbf808ffda4b16cac54edfc6ce55` | 没有外部文件名/路径引用；记录已实施旧样式，不改 guide-page.css/guide-tools.css。 |
| 4 | `docs/superpowers/plans/2026-10-04-geolocation-audio-guide.md` | 已跟踪，43572 bytes；SHA-256 `5d045d4a18f5bd63332d9271eaa5d8e13ceccf10a0a58b55e118d695414c4f03` | 入边：10-05 分众计划:800；出边：geolocation spec:11。与四文件历史组一起删除，不留下该组内断链。 |
| 5 | `docs/superpowers/plans/2026-10-05-分众化讲解与跨会话记忆.md` | 已跟踪，68177 bytes；SHA-256 `5a76b31309740c2b5b8a4e013cc898d849bbaadc38d37088b989a2514d26abc3` | 入边：可行性报告:3；出边：多景区 spec、geolocation spec:11，可行性报告:17，geolocation plan:800。删除本文件仅移除这些出边，保留多景区 spec。 |
| 6 | `docs/superpowers/plans/2026-10-05-分众化讲解与跨会话记忆-可行性验证报告.md` | 已跟踪，5113 bytes；SHA-256 `bfdcefd832af988032859061900df365b9b036b471cb0ac21435ecc87b89ec85` | 入边：分众计划:17；出边：分众计划:3。两文件一起删除，历史测试数不迁入新报告。 |
| 7 | `docs/superpowers/specs/2026-10-04-geolocation-audio-guide-design.md` | 已跟踪，11213 bytes；SHA-256 `d6dabdc71fffb6b48b0b18c8cd62b661ab9d4219c081a0397ab6e3ce234256c6` | 入边：geolocation plan:11、分众计划:11。均在拟删除组内；没有现行地图/README/AGENTS 引用该 spec。 |

引用核对方法：在当前集成树运行 `rg -n` 搜索上述完整 basename、相关路径、DESIGN.md、HomePage/LandingPage、standalone-login 与 tester；随后使用 `git grep -n -I ... HEAD` 复核已提交源码及文档，避免 node_modules、旧 worktree 与未跟踪缓存污染。该文本搜索没有覆盖外部书签、远程文档或 Markdown 锚点，不把“无命中”当作运行验证。

七文件合并处理时，现有 README/AGENTS/地图/导航没有指向它们的入边，预计不需修改任何有效导航。若最终基线新出现有效入边，只修改该入边为当前功能地图/架构已有相应定位；不能把历史内容搬回新文档，也不越权改主 Agent 架构文件。若必须改其架构入口，交主 Agent 处理后再推进。

本轮计划保留 `DESIGN.md` 和多景区 spec：前者是通用景区设计规范，不能等同已废弃的原比赛视觉约束；后者被当前路线图:42 引用，属于主 Agent 需求/架构范围。七文档删除后，其保存的 Git 历史仍可恢复，不复制到 archive 继续充当开发目标。

### 源码及其余历史候选：全部暂缓

| 精确候选 | 当前入边/运行风险 | 决策与未来门槛 |
| --- | --- | --- |
| `frontend/src/views/HomePage.vue` | 当前 router 不导入，已提交文件名搜索仅 `docs/REPO_MAP.md:28`；未发现 import.meta.glob/require.context 加载入口。 | C 类保留；如以后确认退役，需要删除后完整 npm test/build、浏览器 `/`、`/tourist/welcome`、`/tourist/select` 和后台登录入口检查；更新地图:28过时说明。当前验收尚未闭环，不随文档提交删除。 |
| `frontend/src/views/LandingPage.vue` | 同上；自身引用 `/assets/bg-scenic.png`，该资源仍被全局样式与背景 composable 使用。 | C 类保留；即使之后删组件也不删背景或共享依赖。 |
| `frontend/standalone-login.html` | 启动指南:48 明确双击打开入口。 | E 类保留；用户仍可通过直达/本地 HTML 使用，需先确定是否撤下独立预览并同步指南。 |
| `frontend/public/map-tester.html` | public 自动发布直达页，不能靠无 import 断定死代码。 | E 类保留；待地图调试用途确认及实际运行验收。 |
| `frontend/public/motion-tester.html` | public 直达动作调试，动态 `/motions/` URL。 | E 类保留；不删其模型/动作资源。 |
| `scripts/build_product_design_docx.py` | 已提交文本未找到其他文件调用；脚本本身读旧比赛大纲、输出比赛设计 DOCX。 | E 类保留；缺输入与比赛命名不是停止使用证据，需确认比赛交付职责。 |
| `scripts/build_work_description_pdf.py` | 未查到已提交入口调用；生成比赛说明 PDF。 | E 类保留；不执行会写产物的脚本。 |
| `scripts/build_deployment_docx.py` | 未查到已提交入口调用；生成启动部署文档。 | E 类保留；部署文档仍可能有交付用途。 |
| `scripts/build_revision_reinforcement_doc.py` | 未查到已提交入口调用；旧日期整改材料生成器。 | E 类保留；待是否替代的明确证据。 |
| `scripts/extract_competition_data.py` | 未查到已提交入口调用；可能处理比赛/知识输入。 | E 类保留；不得误删仍供业务资料处理使用的脚本。 |
| `scripts/render_pdf_contact_sheets.py` | 未查到已提交入口调用；可通用用于 PDF 视觉检查。 | E 类保留；不能仅因同目录比赛脚本认定其废弃。 |
| `docs/superpowers/plans/2026-10-28-repository-map.md` | 已提交文本未找到完整文件名入边；内容与现地图验收有关。 | E 类保留，待主 Agent 确认验收资料不再需要；不扩入七文件清单。 |
| `docs/superpowers/plans/2026-10-28-k01-stream-integration.patch` | 本次整合已吸收哪些片段仍需逐 hunk 比较；不能按 patch 存在推断重复。 | E 类保留。 |

仍保留前表全部 D 类：当前业务代码/数据库与输入数据、近期功能设计与验收证据、有效需求入口、架构、配置/锁文件、资源及原始项目/sources/备份。没有以“旧比赛目标”为由新增任意源码删除目标。

### 可恢复实施方案（只写方案，命令尚未执行）

1. **等待基线**：主 Agent 完成真实运行验收并明确稳定 commit，记录完整 SHA；核对其包含 K01/W01/V01/W02、媒体和语音已验证行为。重新运行 status/worktree list 及七文件的引用/hash核对。基线更新不使用旧 HEAD 偷跑。
2. **隔离**：从稳定 SHA 建立独立 `codex/legacy-cleanup` 分支与 `integration-work/legacy-cleanup` worktree。若名称/路径已存在则检查后另选新名字，不覆盖、不 reset、不 prune 其他 worktree。不操作原始 `code/RuanJianBei` 的未提交修改；不复用正在验收的 worktree。
3. **先留基线证据**：在独立树运行 `python3 scripts/check_repo_map.py`、`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/tests -p "test_*.py"`、`git diff --check`，记录结果与可比范围。若基线本身失败，先反馈，不以清理掩盖。
4. **精确删除**：逐文件核对本 allowlist 后，用 Git 正常删除这七个已跟踪路径。不用目录通配符、不用 git clean、不移动到 archive、不删 .tmp 或其他文件；不通过复制/覆盖整目录做清理。
5. **交付报告**：新建 `docs/maintenance/legacy-cleanup-report.md`，只记录实际删除、原因、保留/待迁移项、修复的引用、验证与基线 SHA。内容不复刻旧方案。若清理本身没有入边改动，明确写“无需修复现行入口引用”，不要虚构修复。
6. **检查**：再次运行地图检查、scripts 单测、diff --check，并对全部已跟踪 Markdown 做本地目标存在性检查（补足地图检查器仅覆盖 DOCUMENTS 八份文档的限制；锚点与远程链接单列未测）。检查 diff 仅七删除 + 一报告 + 确有必要的导航修复。纯文档删除不启动后端、不调模型、不迁移数据；C 类代码仍保留。
7. **可审查提交**：只暂存上述 allowlist 与报告/必要引用修复；检查 staged diff 后提交，示例消息 `docs: remove superseded frontend design and implementation plans`。主 Agent 通过提交 SHA 审阅并 cherry-pick 到集成线，不自动推送/合并。报告先写稳定基线与实际检查，提交后通过交付消息记录 SHA，避免为将 commit 自身 SHA 写进同一 commit 而反复 amend。
8. **恢复**：合入前可直接不 cherry-pick 清理提交；合入后通过 `git revert <cleanup_commit>` 新增反向提交恢复七文档与报告改动。只需查看历史则 `git show <stable_sha>:<path>`；绝不为恢复而 hard reset 主线或覆盖其他未提交文件。后续源码清理应使用另一个独立提交，不能混入本次文档删除。

### 本次准备检查结果

已确认 commit、worktree、七文件跟踪性/尺寸/hash、已提交文本引用及保留范围。没有运行删除后的测试，当前没有“清理后通过”的结论。主 Agent 的自动化通过与此前本 Agent 的集成测试不是未来清理提交的验证证据。清理 worktree：未创建；清理 commit：无；需主 Agent：真实运行验收完成后确认稳定 SHA。


## 2026-10-30 更新：独立准备副本已建立，仍未删除/提交

主 Agent 最新更正要求“稳定集成基线尚未确认，只准备独立副本和精确删除验证方案”。本节严格遵循该更正；此前允许清理提交的消息不再作为当前删除授权。

- 独立副本：`integration-work/legacy-cleanup-prep`，通过本地 `git clone --no-hardlinks --single-branch --branch codex/competition-integration` 建立；不是 linked worktree，没有 `.git/objects/info/alternates`，不共享工作区或依赖入口。
- 准备分支：`codex/legacy-cleanup-prep`；HEAD `40544857eddccd6fb84044fe2e17098976d0c5fd`，与克隆时集成 HEAD 相同。本副本 status 干净，未带入源工作区未跟踪的 `frontend/node_modules`。
- origin 是本地 `integration-work/v01`；未 fetch 网络、未 push、未合并。该 origin 仅为快照来源，**后续也不得 push 回集成副本**。
- 七文档 allowlist 的内容与上节 ec3f7a6 完全一致：True；已有尺寸/hash仍适用。没有扩大删除清单。
- 在本副本对全部已跟踪 Markdown 执行“虚拟删除”引用检查：仅在内存中把七文件视为不存在，解析未删除 Markdown 的相对链接并匹配目标，受影响的存活 Markdown 链接数量：0。没有删除或移动磁盘文件。此检查不覆盖外部书签、HTML直达、动态代码或纯文本非链接，前节完整 basename 搜索作为补充。
- 本副本运行基线检查：`python3 scripts/check_repo_map.py` 通过（8 documents、83 registered HTTP routes）；`python3 -m unittest discover -s scripts/tests -p 'test_*.py'` 11/11 通过；`git diff --check` 通过。Python 禁止写 bytecode。未启动服务、未跑迁移、未访问真实数据库/模型，未安装依赖。

后续删除验证方案继续沿用七路径 allowlist：稳定 SHA 确认后先核对副本与该 SHA，不一致则建立新独立快照（不覆盖或 reset 此准备副本），复核 hash/入边，再精确删除并记录报告。纯文档清理仅在独立分支形成原子提交；源码/资产/配置/数据/sources/其他工作树仍全部排除。删除前后重复上述地图/11条单测/链接检查及 staged allowlist 审核。当前全部七文档仍存在；清理提交数为零，浏览器和worker真实运行验收不因这些基线检查而被标为完成。
