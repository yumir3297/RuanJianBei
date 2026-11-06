# Current engineering state

Updated: 2026-11-07

- Repository: `yumir3297/RuanJianBei`
- Working branch: `integration/ai-workbench-final`
- Selected source baseline: `origin/codex/competition-integration@7ef0459c669ef896ca2da6c1a9fc008f708e74df`

## Status

The selected integration branch already contains the main K01/W01/V01/W02 implementation and the repository-map commit. This round has added the missing K01 browser publication-recovery connection and corrected stale architecture/task/map documentation. The working tree is isolated from the original `codex/knowledge-workspace` checkout.

The current changes are not yet accepted as production/device validation. Real mobile browsers, live AI/TTS providers, production databases, and verified emergency resources are not available in this workspace.

## Entry points

- Handoff: [HANDOFF.md](HANDOFF.md)
- Feature progress: [TASK_BOARD.md](TASK_BOARD.md)
- Worktree/branch audit: [WORKTREE_INVENTORY.md](WORKTREE_INVENTORY.md)
- Decisions and held scope: [DECISIONS.md](DECISIONS.md)
- Actual test runs and limitations: [TEST_STATUS.md](TEST_STATUS.md)
- Code navigation: [REPO_MAP.md](../REPO_MAP.md)

## Current engineering focus

1. Stage and review the complete tested diff.
2. Commit on this isolated feature branch.
3. Push the branch and open a PR against `codex/competition-integration` (never directly to `master`).
