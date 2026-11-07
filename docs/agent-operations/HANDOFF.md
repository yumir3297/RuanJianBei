# Engineering handoff

Updated: 2026-11-07. Repository: `yumir3297/RuanJianBei`.

## Resume here

- Worktree: `~/RuanJianBei-integration-ai-workbench`
- Branch: `integration/ai-workbench-final`
- Selected source baseline: `7ef0459c669ef896ca2da6c1a9fc008f708e74df` (`origin/codex/competition-integration`)
- Validated implementation commit: `8063453290be92cf683469822332fa96fc7cda09`.
- PR #3 is open: https://github.com/yumir3297/RuanJianBei/pull/3 (base `codex/competition-integration`, head `integration/ai-workbench-final`). The current PR head SHA is available with `git rev-parse HEAD`; this handoff's containing commit is available with `git log -1 --format='%H' -- docs/agent-operations/HANDOFF.md`.
- GitHub reported no branch status checks and `mergeable: UNKNOWN` at the last check; no merge was attempted.
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
- Final automated evidence on the validated implementation commit: backend 671 passed / 19 skipped; frontend 164 passed; production build succeeded with a large-chunk warning; map checker and 11 script tests passed; migration lineage has one head and selected SQLite migration tests passed 7. Focused publication recovery: 13 passed. Independent review has no remaining P0/P1. The implementation branch is pushed and PR #3 is open. See [TEST_STATUS.md](TEST_STATUS.md).

## Immediate next actions

1. Check for new commits or reviewer feedback on PR #3 before taking further action.
2. Re-run relevant tests if any source changes are made.
3. Keep `master` untouched; any additional fixes stay on this PR branch.

## Blockers and boundaries

- CASS/offline remain held: the separate branch contains a proposal and a demo implementation with placeholder map/unverified contacts; no official safety resource has been verified.
- Real mobile browsers, real providers, PostgreSQL production upgrade/concurrency and verified contacts are not available in this session.
- G1 remains partial for one unrecoverable historical evidence gap: the old main-checkout audit's 95 dirty-path count has no path manifest, while later audit counts were 107/128. Current worktrees are clean and protected; no source worktree was modified.
- Full product G2/G3 cannot be claimed complete: W03 and O01 are not implemented; several other backlog tasks are only partial or awaiting design/real data.
- K02 OCR discovery: a local macOS-only Apple Vision/OCRmyPDF wrapper exists at `~/Documents/pdf-ocr-mac/ocr-pdf`, outside the repository. Its README describes searchable-PDF and sidecar-text modes; no real document was run, output was not validated, and it is not wired into import jobs. Do not treat it as production-ready or cross-platform.
