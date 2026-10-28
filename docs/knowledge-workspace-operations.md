# Knowledge workspace operations

## What is persistent

- PostgreSQL stores entries, immutable revisions, source documents and file versions, import and publication jobs, conflicts, and the retrieval epoch.
- Original uploads live under `KNOWLEDGE_UPLOAD_DIR` (default: `backend/.uploads/knowledge`). Keep this directory with the database backup; imported revisions refer to these original files.
- Chroma data lives under `CHROMA_PERSIST_DIR` (default: `kb/chroma_db`). The configured collection name also has a small `.active` pointer file. Back up the entire directory, including this pointer and old collections awaiting cleanup.
- Do not automatically delete drafts, revisions, source versions, or uploaded originals by age. A draft may be the only copy of a reviewed change.

## Backup and recovery

1. Put imports and publishing into maintenance mode, and take a PostgreSQL-consistent backup using the deployment's normal `pg_dump` process.
2. Copy the complete knowledge upload directory and Chroma persistence directory from the same maintenance window. Record the configured `DATABASE_URL`, `KNOWLEDGE_UPLOAD_DIR`, `CHROMA_PERSIST_DIR`, collection name, and embedding model name in the backup manifest. Protect the manifest and backups as application data.
3. Restore PostgreSQL first, then restore the uploaded originals and Chroma directory to their configured paths. Preserve the `.active` pointer and its referenced collection.
4. Start one backend worker and verify pending import/publication jobs reach a terminal state. Expired worker leases are reclaimed by the lifecycle worker.
5. If Chroma is missing or its pointer names a collection that cannot be read, rebuild the index from the database's current published chunks using **重建向量索引**. Rebuilding never publishes a draft. Keep the database and originals intact if the rebuild fails.
6. Verify the admin workspace shows the expected published and draft counts, review pending import conflicts, then resume uploads and publishing.

For a migration, take and verify a database backup before `alembic upgrade head`. Run the migration against a restored copy first. Keep the pre-migration backup until application startup, published retrieval, and workspace editing have been checked.

## Job recovery

- A queued import or publication is durable and will be picked up after restart.
- A worker that stops while holding a lease can be retried after the lease expires. Import batches have a **重试失败文件** action; publication jobs expose **重试发布**.
- A failed embedding or index preparation must leave the previously active Chroma collection selected. Check available disk space and model availability before retrying.
- Resolve each pending source conflict by keeping the current draft, adopting the incoming source, or saving a merged draft. Pending conflicts block publication.
- Never repair a failed job by deleting its revisions, conflict rows, or uploaded source version.

## Disk pressure and upload limits

Monitor free space on the PostgreSQL volume, upload volume, and Chroma volume. Alert before free space falls below the greater of 10% or 2 GiB; use a lower alert threshold only when the deployment's capacity plan explicitly supports it. Uploads are rejected below `KNOWLEDGE_IMPORT_MIN_FREE_BYTES` (default 100 MiB). Index rebuilds also estimate staging space and stop before collection creation when the volume lacks that reserve. At 5% free space or below, or when a write returns `ENOSPC`, pause new imports and index rebuilds, preserve all existing data, free only unrelated temporary files, and retry after capacity is restored. The upload API enforces file-count, file-size, page-count, and parse-time limits; do not raise them without corresponding storage and worker capacity.

## Index rebuild behavior

The rebuild reads only chunks whose revision is still the entry's published revision and whose entry is not withdrawn. It writes a new Chroma collection, switches the active pointer atomically after all records are written, then attempts to remove the old collection. Failed cleanup consumes space but does not change query behavior; schedule cleanup only after confirming which collection is active and backed up. A publication or withdrawal racing with a rebuild is still checked against the database at retrieval time, so an old vector cannot make an unpublished or withdrawn revision visible.
