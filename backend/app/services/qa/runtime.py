from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.qa.faq_matcher import FAQMatcher
from app.services.rag.embedder import BaseEmbedder


_faq_matcher = FAQMatcher()
_last_reload_ms = 0.0


def get_runtime_faq_matcher(
    session: Session,
    *,
    embedder: BaseEmbedder | None = None,
    semantic_threshold: float = 0.85,
) -> FAQMatcher:
    if not _faq_matcher.entries:
        reload_runtime_faq_matcher(session)
    if embedder is not None:
        _faq_matcher.ensure_semantic_index(embedder, semantic_threshold)
    return _faq_matcher


def reload_runtime_faq_matcher(session: Session) -> float:
    global _last_reload_ms
    _last_reload_ms = _faq_matcher.reload(session)
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
