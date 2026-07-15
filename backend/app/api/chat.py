from __future__ import annotations

import logging
from hashlib import sha256
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.repositories.chat_log import ChatLogRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.repositories.qa_cache import QACacheRepository
from app.repositories.quick_topic import QuickTopicRepository
from app.repositories.route import RouteRepository
from app.repositories.visitor import VisitorRepository
from app.schemas.chat import ChatRequest
from app.services.llm.prompt_builder import SYSTEM_PROMPT_VERSION
from app.services.avatar.stub import StubAvatarService
from app.services.coze.client import CozeRoutePlanner
from app.services.llm.openai_compatible import OpenAICompatibleLLMService
from app.services.live_data.service import LiveDataService
from app.services.qa.cache import QACache
from app.services.qa.blind_spot_tracker import BlindSpotTracker
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import GuidedSelectionResolver
from app.services.qa.intent_router import IntentRouter
from app.services.qa.pipeline import QAPipeline
from app.services.qa.runtime import get_runtime_faq_matcher
from app.services.rag.bm25_reranker import BM25Reranker
from app.services.rag.cross_encoder_reranker import CrossEncoderReranker
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.chroma_retriever import VectorBackedRAGService
from app.services.rag.embedder import SentenceTransformerEmbedder
from app.services.rag.reranker import Reranker
from app.services.rag.resilient_reranker import ResilientReranker
from app.services.rag.retriever import RepositoryBackedRAGService
from app.services.rag.vector_store import ChromaVectorStore
from app.services.tts.bailian import BailianTTSService
from app.services.tts.stub import StubTTSService


router = APIRouter()
logger = logging.getLogger(__name__)
_cached_llm_service: OpenAICompatibleLLMService | None = None
_cached_llm_signature: tuple | None = None
TTS_VOICE_PRESETS = {
    "gentle-female": "longwan_v3",
    "calm-female": "longxiaoxia_v3",
    "deep-male": "longsanshu_v3",
    "lively-female": "longanqin_v3",
}


@lru_cache(maxsize=2)
def get_cached_embedder(model_name: str, cache_dir: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(
        model_name,
        cache_dir=Path(cache_dir),
        local_files_only=True,
    )


@lru_cache(maxsize=2)
def get_cached_vector_store(persist_dir: str, collection_name: str) -> ChromaVectorStore:
    return ChromaVectorStore(Path(persist_dir), collection_name)


@lru_cache(maxsize=2)
def get_cached_reranker(
    model_name: str,
    cache_dir: str,
    batch_size: int,
    max_length: int,
) -> ResilientReranker:
    try:
        fallback: Reranker | None = BM25Reranker()
    except Exception:
        logger.exception("BM25 reranker initialization failed; stable vector order is the final fallback.")
        fallback = None

    try:
        primary: Reranker | None = CrossEncoderReranker(
            model_name=model_name,
            cache_dir=Path(cache_dir),
            batch_size=batch_size,
            max_length=max_length,
            local_files_only=True,
        )
    except Exception:
        logger.exception(
            "CrossEncoder reranker is unavailable in the local D-drive cache; using explicit fallback."
        )
        primary = None

    return ResilientReranker(primary=primary, fallback=fallback)


def get_cached_llm_service(settings: Settings) -> OpenAICompatibleLLMService:
    global _cached_llm_service, _cached_llm_signature
    signature = (
        settings.llm_provider,
        settings.llm_base_url,
        settings.llm_model,
        sha256(settings.llm_api_key.encode("utf-8")).hexdigest() if settings.llm_api_key else "",
        settings.llm_temperature,
        settings.llm_max_tokens,
        settings.llm_connect_timeout_seconds,
        settings.llm_first_token_timeout_seconds,
        settings.llm_read_timeout_seconds,
        settings.llm_total_timeout_seconds,
        settings.llm_max_concurrency,
        settings.llm_max_evidence_documents,
        settings.llm_max_evidence_chars_per_document,
    )
    if _cached_llm_service is None or signature != _cached_llm_signature:
        _cached_llm_service = OpenAICompatibleLLMService(settings)
        _cached_llm_signature = signature
    return _cached_llm_service


async def close_cached_llm_service() -> None:
    global _cached_llm_service, _cached_llm_signature
    if _cached_llm_service is not None:
        await _cached_llm_service.aclose()
    _cached_llm_service = None
    _cached_llm_signature = None


def build_answer_cache_namespace(settings: Settings) -> str:
    return "|".join(
        (
            "answer:v1",
            f"provider={settings.llm_provider}",
            f"model={settings.llm_model or 'stub'}",
            f"prompt={SYSTEM_PROMPT_VERSION}",
            f"temperature={settings.llm_temperature}",
            f"max_tokens={settings.llm_max_tokens}",
            f"max_docs={settings.llm_max_evidence_documents}",
            f"max_doc_chars={settings.llm_max_evidence_chars_per_document}",
        )
    )


def build_pipeline(
    session: Session,
    settings: Settings,
    *,
    tts_voice_preset: str | None = None,
) -> QAPipeline:
    knowledge_repository = KnowledgeRepository(session)
    cache_repository = QACacheRepository(session)
    chat_log_repository = ChatLogRepository(session)
    route_repository = RouteRepository(session)

    query_rewriter = QueryRewriter()
    faq_matcher = get_runtime_faq_matcher(session)
    fallback_rag = RepositoryBackedRAGService(
        knowledge_repository=knowledge_repository,
        query_rewriter=query_rewriter,
        reranker=Reranker(),
    )

    embedder: SentenceTransformerEmbedder | None = None
    try:
        embedder = get_cached_embedder(
            settings.embedding_model_name,
            str(settings.model_cache_root),
        )
        faq_matcher = get_runtime_faq_matcher(
            session,
            embedder=embedder,
            semantic_threshold=settings.faq_semantic_threshold,
        )
    except Exception:
        logger.exception(
            "FAQ semantic index initialization failed; exact and fuzzy FAQ matching remain available."
        )

    try:
        if embedder is None:
            raise RuntimeError("Local embedding model is unavailable.")
        rag_service = VectorBackedRAGService(
            vector_store=get_cached_vector_store(
                str(settings.chroma_persist_root),
                settings.rag_collection_name,
            ),
            embedder=embedder,
            query_rewriter=query_rewriter,
            reranker=get_cached_reranker(
                settings.reranker_model_name,
                str(settings.model_cache_root),
                settings.reranker_batch_size,
                settings.reranker_max_length,
            ),
            fallback=fallback_rag,
            candidate_k=settings.rag_candidate_k,
        )
    except Exception:
        logger.exception("Vector RAG initialization failed; using repository-backed fallback.")
        rag_service = fallback_rag

    tts_service = StubTTSService()
    if settings.tts_provider == "bailian" and settings.tts_api_key:
        try:
            tts_service = BailianTTSService(
                api_key=settings.tts_api_key,
                base_url=settings.tts_base_url,
                model=settings.tts_model,
                voice=TTS_VOICE_PRESETS.get(tts_voice_preset, settings.tts_voice),
                timeout_seconds=settings.tts_timeout_seconds,
                use_compatible_api=False,
            )
        except Exception:
            logger.exception("Bailian TTS initialization failed; using stub.")

    return QAPipeline(
        query_rewriter=query_rewriter,
        faq_matcher=faq_matcher,
        qa_cache=QACache(cache_repository, ttl_seconds=settings.cache_ttl_seconds),
        rag_service=rag_service,
        llm_service=get_cached_llm_service(settings),
        tts_service=tts_service,
        avatar_service=StubAvatarService(),
        chat_log_repository=chat_log_repository,
        visitor_repository=VisitorRepository(session),
        guided_selector=GuidedSelectionResolver(
            knowledge_repository,
            QuickTopicRepository(session),
            route_repository,
        ),
        followup_suggestions=FollowUpSuggestionService(),
        blind_spot_tracker=BlindSpotTracker(KnowledgeBlindSpotRepository(session)),
        answer_cache_namespace=build_answer_cache_namespace(settings),
        intent_router=IntentRouter(),
        live_data_service=LiveDataService(settings),
        coze_route_planner=CozeRoutePlanner(
            run_url=settings.coze_run_url,
            token=settings.coze_token,
            timeout_seconds=settings.coze_timeout_seconds,
        ) if settings.coze_enabled else None,
        knowledge_repository=knowledge_repository,
        route_repository=route_repository,
    )


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    pipeline = build_pipeline(
        session,
        settings,
        tts_voice_preset=payload.tts_voice,
    )

    async def event_generator():
        async for event in pipeline.stream_chat(payload):
            yield event.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
