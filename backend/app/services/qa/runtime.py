from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.qa.faq_matcher import FAQMatcher
from app.services.knowledge.visibility import VisibilityService
from app.services.rag.embedder import BaseEmbedder


_faq_matcher = FAQMatcher()
_last_reload_ms = 0.0
_semantic_index_failed = False
_faq_reload_failed = False
_reload_lock = asyncio.Lock()


def faq_reload_failed() -> bool:
    return _faq_reload_failed


def set_faq_semantic_index_failed(failed: bool) -> None:
    global _semantic_index_failed
    _semantic_index_failed = failed


def faq_semantic_index_failed() -> bool:
    return _semantic_index_failed


async def get_runtime_faq_matcher(
    session: AsyncSession,
    *,
    embedder: BaseEmbedder | None = None,
    semantic_threshold: float = 0.85,
) -> FAQMatcher:
    epoch = await VisibilityService(session).read_epoch() if session is not None else None
    if not _faq_matcher.entries or (epoch is not None and getattr(_faq_matcher, "knowledge_epoch", None) != epoch):
        await reload_runtime_faq_matcher(session)
    if embedder is not None:
        try:
            _faq_matcher.ensure_semantic_index(embedder, semantic_threshold)
        except Exception:
            set_faq_semantic_index_failed(True)
            raise
        set_faq_semantic_index_failed(False)
    return _faq_matcher


async def reload_runtime_faq_matcher(session: AsyncSession) -> float:
    async with _reload_lock:
        return await _reload_runtime_faq_matcher_locked(session)


async def _reload_runtime_faq_matcher_locked(session: AsyncSession) -> float:
    global _last_reload_ms, _faq_reload_failed, _faq_matcher
    old_semantic_index = _faq_matcher.semantic_index
    candidate = FAQMatcher()
    semantic_error = None
    try:
        before = await VisibilityService(session).read_epoch() if session is not None else None
        elapsed = await candidate.reload(session)
        if old_semantic_index is not None:
            try:
                candidate.ensure_semantic_index(old_semantic_index.embedder, old_semantic_index.threshold)
            except Exception as error:
                semantic_error = error
        after = await VisibilityService(session).read_epoch() if session is not None else None
        if before != after:
            raise RuntimeError("FAQ knowledge version changed during reload")
        if before is not None:
            candidate.knowledge_epoch = before
    except Exception:
        _faq_reload_failed = True
        raise
    _faq_matcher = candidate
    _last_reload_ms = elapsed
    _faq_reload_failed = semantic_error is not None
    if semantic_error is not None:
        set_faq_semantic_index_failed(True)
        raise semantic_error
    if old_semantic_index is not None:
        set_faq_semantic_index_failed(False)
    return _last_reload_ms


def get_runtime_faq_stats() -> dict[str, int | float]:
    semantic_index = _faq_matcher.semantic_index
    return {
        "entry_count": len(_faq_matcher.entries),
        "exact_index_count": len(_faq_matcher.exact_index),
        "semantic_alias_count": semantic_index.alias_count if semantic_index else 0,
        "semantic_threshold": semantic_index.threshold if semantic_index else 0.0,
        "semantic_build_ms": semantic_index.last_build_ms if semantic_index else 0.0,
        "last_reload_ms": _last_reload_ms,
    }
