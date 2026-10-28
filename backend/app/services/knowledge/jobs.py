from __future__ import annotations

import asyncio
import logging

from app.core.config import Settings
from app.db.session import AsyncSessionLocal
from app.services.knowledge.publication import KnowledgePublicationService

logger = logging.getLogger(__name__)


async def run_publication_worker(settings: Settings) -> None:
    """Poll persisted jobs so queued/expired work resumes after process restart."""
    from app.api.chat import get_cached_embedder, get_cached_vector_store

    while True:
        try:
            async with AsyncSessionLocal() as session:
                queue = KnowledgePublicationService(session)
                job_ids = await queue.pending_job_ids()

            if job_ids:
                embedder = await asyncio.to_thread(
                    get_cached_embedder,
                    settings.embedding_model_name,
                    str(settings.model_cache_root),
                )
                vector_store = get_cached_vector_store(
                    str(settings.chroma_persist_root), settings.rag_collection_name
                )
                for job_id in job_ids:
                    async with AsyncSessionLocal() as session:
                        service = KnowledgePublicationService(session, embedder, vector_store)
                        await service.run_publication(job_id)
            else:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Knowledge publication worker iteration failed")
            await asyncio.sleep(2)
