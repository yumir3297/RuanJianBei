# 本地 worktree 与分支状态

核对时间：2026-11-14。路径是本机当前环境的绝对路径，状态数量包含已修改、已暂存和未跟踪路径；它们不是可直接合并的提交数量。

当前待处理来源分组：共 5 个带未提交改动的来源 worktree。GuideLoop 是正在审示/合并的来源；另外 4 个是游客/管理端拆分、CASS、下一站上下文 RAG、讲解策略。总集成 worktree 已包含这些来源的部分文件和测试，但因为来源仍是脏工作区，尚不能把它们记为可追溯的正式合并提交。

| 工作区 | 分支/HEAD | 状态路径数 | 处理建议 |
|---|---|---:|---|
| `/Users/yumir/.codex/worktrees/competition-final-integration/RuanJianBei` | detached `aa83aedd` | 173 | 当前总集成工作区；保留所有未提交变更，按本台账选择性审示 |
| `/Users/yumir/.codex/worktrees/admin-tourist-split-v2/RuanJianBei-integration-ai-workbench` | `codex/admin-tourist-split-v2` | 73 | 游客/管理端拆分来源；只按已核对文件迁移 |
| `/Users/yumir/.codex/worktrees/cass-guide/RuanJianBei-integration-ai-workbench` | `feat/cass-guide` | 32 | CASS 来源；保留状态、安全和策略改动，真实预警仍未验收 |
| `/Users/yumir/.codex/worktrees/guideloop-pilot/RuanJianBei` | `feat/guideloop-pilot` | 42 | GuideLoop 试验来源；保留为开发/测试能力 |
| `/Users/yumir/.codex/worktrees/tour-context-rag/RuanJianBei` | detached | 60 | 下一站/上下文来源；需与当前 K01 revision 语义核对 |
| `/Users/yumir/.codex/worktrees/tour-narration-policy/RuanJianBei` | detached | 159 | 讲解策略来源；存在后续刷新，不能按旧快照覆盖 |
| `/Users/yumir/.codex/worktrees/guideweave-pilot/RuanJianBei` | `codex/guideweave-integration` | 0 | 当前干净，可作为只读对照 |
| `/Users/yumir/RuanJianBei` | `codex/knowledge-workspace` | 0 | 知识工作区基线，只读对照 |
| `/Users/yumir/RuanJianBei-integration-ai-workbench` | `integration/ai-workbench-final` | 0 | 已提交的工作台对照，不直接覆盖总集成工作区 |
| `/Users/yumir/.local/share/opencode/worktree/7bdc47/k02-ai-knowledge-pipeline` | detached | 0 | K02 知识管线只读对照 |

## 处理规则

- 总集成工作区当前是 detached HEAD 且有大量未提交/未跟踪路径；禁止整体 `reset --hard`、`clean -fd` 或把整个工作区一次性复制到主线。
- 迁移前先按功能在 [REPO_MAP](../REPO_MAP.md) 和 [合并前审示结论](MERGE_READINESS.md) 登记入口、测试和来源；同一文件多来源修改必须逐块审示。
- CASS、GuideLoop、离线陪游和行程提案已有本地合成证据，但来源 worktree 的未提交变更不能因此视为已合并提交。
- 来源快照、stash bundle、Trae 参考归档位于工作区外的保全目录；它们用于恢复和审计，不应作为运行时依赖或直接提交。
- 本表只描述当前本地状态，不证明分支已推送、提交已合并或生产部署可用。

## 当前合并顺序

1. GuideLoop：先完成当前正在进行的审示，确认与 K01 已发布 revision、游客入口隔离和管理端复测边界。
2. 游客/管理端拆分：以当前总集成的双端构建和边界测试为基线，回溯来源改动清单，形成单独可追溯提交。
3. CASS：保留安全暂停、定位、情境策略和模拟演示；真实预警源继续标为未验收。
4. 下一站上下文 RAG：核对目录摘要、行程进度和 revision 变化，避免把旧上下文覆盖新状态。
5. 讲解策略：以最新 refresh 快照为准，逐文件/逐块迁移，不能用旧来源 worktree 整体覆盖。
