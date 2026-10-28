# Repository Map Implementation Plan

**Goal:** 为现有 Vue/FastAPI 仓库建立可供 Codex、其他代码助手及开发者使用的功能导航、跨端边界与校验入口。

**Architecture:** 短 AGENTS.md 负责规则及按需阅读；REPO_MAP.md 负责功能定位；ARCHITECTURE.md 解释已核验链路；DEVELOPMENT.md 和 COMPATIBILITY.md 分别负责开发系统与终端浏览器。标准库脚本只读解析 Python AST 并检查地图链接/API，不导入或启动业务服务。

**Scope:** 文档和地图维护工具。用户已选择先前建议并要求建立；不改业务行为，不把静态核验表述为设备实测，不安装业务依赖，不提交或推送。

**Tech Stack:** Markdown、Python 标准库、unittest；所有仓库路径使用相对 POSIX 路径。

## Tasks

- [x] 核验入口、路由、功能服务、测试及兼容性证据，记录 README 与源码的差异。
- [x] 创建根目录/前端/后端 AGENTS.md 和四份地图文档，README 加入口并修正失效的启动指引与 Node 版本。
- [x] 先写 CLI 行为测试：有效链接、中文空格路径、坏链接、越界链接、失效 API、解析错误、JSON 导出。运行得到缺少工具导致的预期失败。
- [x] 实现 scripts/check_repo_map.py；默认检查，--json 导出实时接口索引；用真实临时仓库验证退出码与结果，不访问网络。
- [x] 验证所有新文档本地链接与 API；执行工具测试、git diff --check；记录依赖/设备测试的实际边界并独立审阅。

## Acceptance

- 能从聊天、语音、视觉、地图、讲解、推荐、知识、盲区、形象、资源、情绪与记忆定位到源码及现有测试。
- 指引含正确 cwd、Windows 和 macOS/Linux 命令、Node engines 限制及 Python 原生依赖风险。
- 明确手机/平板/桌面、权限拒绝、音频、HTTPS、弱网、WebGL 的定位与验收步骤。
- 脚本在任意 cwd 工作；路径/路由失效返回非零；JSON 不含本机绝对路径或配置秘密。
- 不将历史报告、计划中的功能或未执行的业务测试写成已通过。

## Verification evidence (2026-10-28, macOS)

- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`：8 passed。最初脚本尚未实现时 8 项均预期失败；实现后修正了测试不必要的列表顺序约束，验证实际路由集合。
- `python3 scripts/check_repo_map.py`：8 documents、42 registered HTTP routes，通过。
- 从外层 ChatGPT 项目目录运行脚本绝对路径 `--json`：通过，42 条路由，文件定位均为相对路径。
- `git diff --check`：通过。
- `python3 -m pytest --version`：失败，主机所用 Python 没有 pytest；backend/.venv 和 frontend/node_modules 均不存在。本次未安装业务依赖、启动服务、迁移数据库、运行前端构建或业务测试。
- Windows/Linux 执行与真实浏览器/手机/平板体验未测；文档提供对应命令、代码定位与验收步骤，不声明已通过。
- 独立审阅发现两个 P2：命令式路由注册被静默遗漏、Windows 绝对链接被误认作远程 scheme。均先补失败测试再修复；新增 app/router 命令式注册、Windows drive/UNC/file URL 回归。
- 最终工具回归：11 passed；8 文档、42 HTTP 路由校验及 `git diff --check` 通过。先前 8 项记录为初版结果，此处为最终结果。
- 额外核对并纠正定位：讲解静态回退位于 MapView.playNarration；鉴权依赖位于 auth.require_admin_token。
- 建图与使用测试验收时，变更位于本地分支 `codex/repository-map`，尚未 commit/push；业务源码未修改。后续提交与推送状态以 Git 历史和 GitHub 为准。
