# Knowledge Consistency Implementation Plan

> Implement and verify roadmap work package A's five acceptance checks.

**Goal:** New, edited, and deleted knowledge stays consistent across database retrieval, chunks, vector index, and answer cache; failures preserve the prior usable version; queries behave safely during index rebuild.

**Architecture:** The database is authoritative. CRUD updates the entry, its chunks, cache invalidation, and a persisted knowledge generation in one transaction. Requests use vector search only when its recorded generation matches; otherwise they query current database knowledge. A complete vector generation is prepared separately and switched through an atomic pointer, so rebuild failure or in-progress work leaves the prior index available. Cache namespaces include the knowledge generation.

**Tech Stack:** FastAPI, async SQLAlchemy, Alembic, ChromaDB, Vue 3, pytest, SQLite test fixtures.

**Spec:** `docs/plans/2026-10-27-feature-roadmap.md` section 4.1; detailed knowledge draft/import workspace is tracked separately in `docs/superpowers/specs/2026-10-27-knowledge-workspace-design.md`.

## Global Constraints

- A failed create/update/delete transaction leaves the prior database row, chunks, and cache intact and identifies the failed step.
- Old vector text and stale answer cache entries cannot be returned after knowledge generation changes.
- A failed or superseded index build never marks its generation current.
- Do not run migrations against a developer database, rebuild local production indexes, or call paid providers.

## Review Focus

- Existing data migration starts in safe fallback mode until the first successful index build.
- Concurrent content changes during index build cannot mark stale vectors current.
- A process restart reads the active vector generation pointer.
- A stale in-flight answer cache write cannot be hit by a new knowledge generation.
- Delete and failed update paths leave no stale chunk or visitor-visible cache result.

## Tasks

1. **Transactional CRUD consistency:** update the entry, chunks, answer-cache invalidation, and knowledge generation in one DB transaction; expose actionable failed-stage errors; test create/update/delete and rollback.
2. **Generation-aware cache and retrieval:** isolate old cache writes; use current DB retrieval when vector generation is stale; reject stale vector content and merge current DB results; test changed/deleted knowledge.
3. **Safe index rebuild:** build a fresh Chroma collection before atomically switching; keep the old one queryable during prepare; only mark an unchanged knowledge generation indexed; test write failure, empty index, restart, and concurrent content changes.
4. **Admin visibility:** expose index generation status and explain fallback/rebuild state in the admin UI; display backend failure-stage messages; cover the status endpoint and message helper.
5. **Verification:** run focused and full backend/frontend suites, migration checks against disposable SQLite, repository map validation, diff checks, and a requirement-by-requirement audit; dispatch a fresh read-only reviewer and fix all critical/important findings.
