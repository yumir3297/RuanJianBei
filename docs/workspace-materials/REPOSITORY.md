# AI 数字人导游：代码仓库关联

- 主仓库：https://github.com/yumir3297/RuanJianBei
- 当前项目内的代码目录：`code/RuanJianBei/`
- Git 远程：`origin` → `git@github.com:yumir3297/RuanJianBei.git`
- 默认分支：`master`，跟踪 `origin/master`
- 当前本地开发分支：`codex/repository-map`，跟踪 `origin/codex/repository-map`
- 仓库地图提交：`672a104ff81c50047dff5327ca317b5e3c332eb1`（已推送）
- 地图 PR：[RuanJianBei #1](https://github.com/yumir3297/RuanJianBei/pull/1)，当前尚未合并 master。
- 本机 SSH 已认证为 `yumir3297`，推送 dry-run 验证通过（2026-10-28）。

## 后续开发

在 `code/RuanJianBei/` 内执行代码修改、Git 和测试命令。该目录是独立的 Git 仓库；当前项目外层目录不是 Git 仓库。

AI 开发首先读取 [仓库 AGENTS.md](code/RuanJianBei/AGENTS.md) 和 [功能地图](code/RuanJianBei/docs/REPO_MAP.md)。
后续开发在包含这组文档的分支上进行，并按 AGENTS.md 在修改功能入口、接口或验证命令时同步维护地图。PR 合并前，不能假设远程 master 已包含地图。
其他入口：[架构链路](code/RuanJianBei/docs/ARCHITECTURE.md)、[跨系统开发](code/RuanJianBei/docs/DEVELOPMENT.md)、[多端矩阵](code/RuanJianBei/docs/COMPATIBILITY.md)。
建议把代码仓库根目录作为 Codex 本地开发项目目录；从当前外层 ChatGPT 项目发起任务时，明确要求读取仓库及相关目录的 AGENTS.md。

在外层项目目录也可执行只读地图校验：

```sh
python3 code/RuanJianBei/scripts/check_repo_map.py
```

Windows 使用已安装的 Python 3 命令 `python`。该工具无需业务依赖，不会启动服务或读取真实 `.env`。

先读取仓库的 `README.md` 与相关开发文档。主仓库已同时包含 `frontend/` 和 `backend/`。

`sources/` 是 ChatGPT 项目同步的只读参考资料，不得修改、移动或删除。此文件仅记录本地路径与远程地址，不代表 ChatGPT 云端会自动同步代码；代码同步使用 Git。

## 旧前端仓库备份

- 原仓库：https://github.com/yumir3297/software-cup-frontend
- 完整 Git 镜像备份：`backups/software-cup-frontend.git/`
- 备份已通过 `git fsck --full`。
- 备份完成时 `main`：`7b41a9911a62550738a7d187d6526723f5161eaf`
- 备份包含 Git 分支与历史，不包含 GitHub Issues、设置或部署配置。
- 远程仓库尚未删除。

需要恢复为可编辑目录时，运行：

```sh
git clone backups/software-cup-frontend.git code/software-cup-frontend-restored
```
