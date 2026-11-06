# Engineering handoff

Updated: 2026-11-07. Repository: `yumir3297/RuanJianBei`.

## Resume here

- Worktree: `~/RuanJianBei-integration-ai-workbench`
- Branch: `integration/ai-workbench-final`
- Selected source baseline: `7ef0459c669ef896ca2da6c1a9fc008f708e74df` (`origin/codex/competition-integration`)
- Current changes are being prepared on this branch. Before commit, verify the final diff and tests; after commit, identify the commit containing this file with `git log -1 --format='%H' -- docs/agent-operations/HANDOFF.md`.
- Never continue by modifying `master` or the original `~/RuanJianBei` checkout.

## Read first

1. `git status --short --branch`, `git rev-parse HEAD`, `git worktree list --porcelain`.
2. This file, [TASK_BOARD.md](TASK_BOARD.md), [WORKTREE_INVENTORY.md](WORKTREE_INVENTORY.md), [TEST_STATUS.md](TEST_STATUS.md), and [REPO_MAP.md](../REPO_MAP.md).
3. Compare any newer commits/PRs against the recorded HEAD before continuing.

## Completed in this round so far

- Audited registered worktrees, all fetched remote refs, open PR/Issue and historical audit evidence; source snapshots remain intact.
- Selected the integration baseline and created this isolated integration branch.
- Wired persistent K01 publication recovery to the admin UI. The UI restores known jobs by GET; unknown create results require an explicit same-idempotency-key recovery; browser storage failure fails closed.
- Independent review identified and the current diff addresses definitive 4xx stale-draft rejection, lost retry responses, status polling after unmount, and read-only recovery when only in-memory job ID persistence failed.
- Added the missing pinned async pytest plugin and corrected stale knowledge architecture, feature map and backlog claims.
- Final automated evidence on the current change set: backend 671 passed / 19 skipped; frontend 164 passed; production build succeeded with a large-chunk warning; map checker and 11 script tests passed; migration lineage has one head and selected SQLite migration tests passed 7. Focused publication recovery: 13 passed. Independent review has no remaining P0/P1. Commit, push and PR remain. See [TEST_STATUS.md](TEST_STATUS.md).

## Immediate next actions

1. Inspect the final diff and verify `git diff --check`.
2. Commit on `integration/ai-workbench-final`.
3. Push the feature branch and open a PR targeting `codex/competition-integration`, not `master`.

## Blockers and boundaries

- CASS/offline remain held: the separate branch contains a proposal and a demo implementation with placeholder map/unverified contacts; no official safety resource has been verified.
- Real mobile browsers, real providers, PostgreSQL production upgrade/concurrency and verified contacts are not available in this session.
- Full product G2/G3 cannot be claimed complete: W03 and O01 are not implemented; several other backlog tasks are only partial or awaiting design/real data.
