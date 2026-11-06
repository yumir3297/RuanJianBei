# Worktree and branch inventory

Audit date: 2026-11-07. Remote refs were fetched from `origin`; no remote branch was deleted or force-updated. Local checkout paths below are shell-expanded `~` paths, not portable repository facts.

## Registered worktrees at audit

| Path | Branch / HEAD | Status | Classification |
|---|---|---|---|
| `~/RuanJianBei` | `codex/knowledge-workspace@914c030b2e2cb339d64d22dec7a53efce4843e8f` | Clean at inspection; no source edits made there | `HOLD` — original checkout preserved; all 9 K01 commits are ancestors of selected integration baseline |
| `~/RuanJianBei-integration-ai-workbench` | `integration/ai-workbench-final@7ef0459c669ef896ca2da6c1a9fc008f708e74df` at creation | New isolated working tree; contains this round's changes | `CONTINUE` — active integration worktree |

`git worktree list --porcelain` showed only those two registered worktrees after creation. Historical worktree paths mentioned in earlier reports are not current registered worktrees. A missing worktree registration does not prove that no external session or untracked directory exists; no historical directory was deleted or pruned.

## Remote branches and treatment

| Ref | SHA | Relationship / useful content | Treatment |
|---|---|---|---|
| `origin/master` | `540568e231bbda10bfdfdeceaea4041aa681b078` | GitHub default branch; base ancestor | `HISTORICAL` — not edited directly |
| `origin/codex/competition-integration` | `7ef0459c669ef896ca2da6c1a9fc008f708e74df` | 432 commits ahead of master; its parent `3bba074` is code/integration state and the tip adds archived delivery reports; contains both map and K01 lineages | `MERGE` — chosen source baseline for the isolated branch, not a direct merge to master |
| `origin/integration/ai-workbench-final` | `8063453290be92cf683469822332fa96fc7cda09` at initial PR creation | This round's tested implementation commit; PR #3 may advance with docs-only handoff updates | `CONTINUE` — pushed; PR #3 is open against `codex/competition-integration` |
| `origin/codex/repository-map` | `672a104ff81c50047dff5327ca317b5e3c332eb1` | One map commit beyond master; ancestor of selected integration | `ALREADY_INCLUDED` |
| local `codex/knowledge-workspace` | `914c030b2e2cb339d64d22dec7a53efce4843e8f` | Nine K01 commits beyond master; ancestor of selected integration | `ALREADY_INCLUDED` |
| `origin/codex/workspace-snapshot-main-checkout` | `22973a8da7ebbb2390dbfdde21c8af89e2ab705b` | Snapshot commit on map ancestry; historical audit recorded many exact-blob matches plus superseded/unscoped design paths | `PARTIAL_PICK` — no wholesale merge; current remaining differences were reviewed and found redundant, superseded or outside confirmed scope |
| `origin/codex/workspace-snapshot-v01` | `e747a49a764c683276d83ce86728dd468e2432f8` | Snapshot of V01 tree, parent `098553f`; older UI/editor and implementation snapshots | `PARTIAL_PICK` — useful backend behavior was integrated or replaced by later implementation; do not overwrite current UI/store or migration history |
| `origin/codex/workspace-snapshot-w02` | `a8c86d51084bd027b1e345f9a47d6619a7d9f5e7` | Snapshot of W02 tree, parent `a8c2837`; durable-job sources | `PARTIAL_PICK` — current W02 implementation extends it; its divergent `f1b4c9d76e20` migration must not be cherry-picked |
| `origin/codex/workspace-snapshot-w02-integration` | `7614b0ec0c5952fbd5cb928db492daae64e532fd` | W02/V01 integration snapshot, parent `098553f` | `PARTIAL_PICK` — no wholesale merge; later integrated job/proposal implementation has stronger version fences and recovery checks |
| `origin/feat/location-guide-opt` | `09aca67e433f2f9a012933f1b686398084d33fc3` | Diverges from current integration; 7 commits beyond master, including offline companion, placeholders and a CASS-Guide proposal | `HOLD` — preserve branch; do not treat draft as confirmed architecture or placeholders as verified safety data |

## GitHub work

- Open PR #1: `codex/repository-map` → `master`, https://github.com/yumir3297/RuanJianBei/pull/1. Its code is already in the selected integration baseline; this audit did not merge or close the PR.
- Open PR #3: `integration/ai-workbench-final` → `codex/competition-integration`, https://github.com/yumir3297/RuanJianBei/pull/3. Created after the initial branch/issue inventory; contains implementation commit `8063453290be92cf683469822332fa96fc7cda09`.
- Open Issue #2: C01/W01 browser acceptance, https://github.com/yumir3297/RuanJianBei/issues/2. It remains an external device-acceptance item.
- Initial `gh pr list --state all` found no other PRs before #3 was created; `gh issue list --state all` found no other issues at audit time.

## Snapshot safety and migration note

All listed source refs remain available on GitHub. No source worktree was modified. Integration history contains the reconciled Alembic lineage and durable proposal fields; the old W02 migration with the same revision ID but a different parent is not equivalent and cannot be overlaid safely. Historical audit evidence: `docs/development/WORKTREE_AUDIT_2026-11-05.md`; it has detailed content comparisons but also explicitly records a legacy path-count gap and device/database limitations.
