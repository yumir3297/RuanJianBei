from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.qa.faq_matcher import FAQMatcher
from app.services.rag.embedder import BaseEmbedder


_faq_matcher = FAQMatcher()
_last_reload_ms = 0.0
_semantic_index_failed = False


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
    if not _faq_matcher.entries:
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
    global _last_reload_ms
    had_semantic_index = _faq_matcher.semantic_index is not None
    try:
        _last_reload_ms = await _faq_matcher.reload(session)
    except Exception:
        if had_semantic_index and _faq_matcher.semantic_index is None:
            set_faq_semantic_index_failed(True)
        raise
    if had_semantic_index:
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
