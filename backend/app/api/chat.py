from __future__ import annotations

import asyncio

import logging
from hashlib import sha256
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.api.capacity import acquire_capacity
from app.core.deps import get_app_settings, get_db_session
from app.models.avatar_config import AvatarConfig
from app.repositories.chat_log import ChatLogRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.repositories.qa_cache import QACacheRepository
from app.repositories.quick_topic import QuickTopicRepository
from app.repositories.route import RouteRepository
from app.repositories.visitor import VisitorRepository
from app.repositories.visitor_memory import VisitorMemoryRepository
from app.schemas.chat import ChatReplayRequest, ChatReplayResponse, ChatRequest
from app.services.llm.prompt_builder import SYSTEM_PROMPT_VERSION
from app.services.avatar.stub import StubAvatarService
from app.services.llm.openai_compatible import OpenAICompatibleLLMService
from app.services.qa.cache import QACache
from app.services.knowledge.visibility import VisibilityService
from app.services.qa.blind_spot_tracker import BlindSpotTracker
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import GuidedSelectionResolver
from app.services.qa.intent_router import IntentRouter
from app.services.qa.pipeline import QAPipeline
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog
from app.services.qa.stream_events import StreamEvent, with_sse_heartbeat
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
from app.services.tts.factory import build_streaming_tts_service, build_tts_service
from app.services.tts.replay_cache import ReplayAudioCache
from app.services.tts.speech_profile import build_speech_cache_key, build_speech_profile
from app.services.tts.stub import StubTTSService
from app.services.tts.welcome_cache import (
    _derive_model_key,
    generate_and_cache,
    get_cached,
    get_welcome_text,
)


router = APIRouter()
logger = logging.getLogger(__name__)
_cached_llm_service: OpenAICompatibleLLMService | None = None
_cached_llm_signature: tuple | None = None
_replay_audio_cache = ReplayAudioCache()
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


async def build_pipeline(
    session: AsyncSession,
    settings: Settings,
    *,
    tts_voice_preset: str | None = None,
) -> QAPipeline:
    knowledge_repository = KnowledgeRepository(session)
    cache_repository = QACacheRepository(session)
    visibility_service = VisibilityService(session)
    chat_log_repository = ChatLogRepository(session)
    route_repository = RouteRepository(session)

    query_rewriter = QueryRewriter()
    faq_matcher = await get_runtime_faq_matcher(session)
    fallback_rag = RepositoryBackedRAGService(
        knowledge_repository=knowledge_repository,
        query_rewriter=query_rewriter,
        reranker=Reranker(),
    )

    embedder: SentenceTransformerEmbedder | None = None
    try:
        embedder = await asyncio.to_thread(
            get_cached_embedder,
            settings.embedding_model_name,
            str(settings.model_cache_root),
        )
        faq_matcher = await get_runtime_faq_matcher(
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
            reranker=await asyncio.to_thread(
                get_cached_reranker,
                settings.reranker_model_name,
                str(settings.model_cache_root),
                settings.reranker_batch_size,
                settings.reranker_max_length,
            ),
            fallback=fallback_rag,
            candidate_k=settings.rag_candidate_k,
            visibility=visibility_service,
        )
    except Exception:
        logger.exception("Vector RAG initialization failed; using repository-backed fallback.")
        rag_service = fallback_rag

    tts_service = StubTTSService()
    streaming_tts = None
    if settings.tts_ready:
        try:
            tts_service = build_tts_service(settings, preset=tts_voice_preset)
            # 同时创建流式 TTS 服务（工厂按 provider 分发；不支持流式时返回 None）
            streaming_tts = build_streaming_tts_service(settings, preset=tts_voice_preset)
        except Exception:
            logger.exception("TTS initialization failed; using stub.")

    return QAPipeline(
        query_rewriter=query_rewriter,
        faq_matcher=faq_matcher,
        qa_cache=QACache(cache_repository, ttl_seconds=settings.cache_ttl_seconds),
        rag_service=rag_service,
        llm_service=get_cached_llm_service(settings),
        tts_service=tts_service,
        speech_profile=build_speech_profile(settings, tts_voice_preset),
        avatar_service=StubAvatarService(),
        streaming_tts_service=streaming_tts,
        chat_log_repository=chat_log_repository,
        visitor_repository=VisitorRepository(session),
        visitor_memory_repository=VisitorMemoryRepository(session),
        guided_selector=GuidedSelectionResolver(
            knowledge_repository,
            QuickTopicRepository(session),
            route_repository,
        ),
        followup_suggestions=FollowUpSuggestionService(),
        blind_spot_tracker=BlindSpotTracker(KnowledgeBlindSpotRepository(session)),
        answer_cache_namespace=build_answer_cache_namespace(settings),
        llm_provider_name=settings.llm_provider,
        intent_router=IntentRouter(),
        knowledge_repository=knowledge_repository,
        route_repository=route_repository,
        visibility_service=visibility_service,
        vision_catalog=PublishedAttractionCatalog(K01PublishedAttractionSource(session, site_id=settings.site_id)),
        vision_site_id=settings.site_id,
    )


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    lease = acquire_capacity(request, settings, "chat")
    logger.info("Chat stream accepted: input_mode=%s text_only=%s", payload.input_mode, payload.text_only)
    async def event_generator():
        # Send a first event before local model initialization. This keeps the
        # UI responsive during a cold start and proves that the SSE link works.
        try:
            yield StreamEvent(type="status", data={"text": "正在准备导览知识..."}).to_sse()
            pipeline = await build_pipeline(
                session,
                settings,
                tts_voice_preset=payload.tts_voice,
            )
            async for event in pipeline.stream_chat(payload):
                yield event.to_sse()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Chat stream failed before completion")
            yield StreamEvent(
                type="error",
                data={"message": "导览服务处理回答时发生错误，请稍后重试。"},
            ).to_sse()
        finally:
            lease.release()

    return StreamingResponse(
        with_sse_heartbeat(event_generator()),
        media_type="text/event-stream",
        background=BackgroundTask(lease.release),
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/replay", response_model=ChatReplayResponse)
async def replay_chat_answer(
    payload: ChatReplayRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> ChatReplayResponse:
    """Re-synthesize a saved answer for its owning anonymous chat session."""
    lease = acquire_capacity(request, settings, "chat")
    try:
        log = await ChatLogRepository(session).get_for_session(
            payload.chat_log_id,
            payload.session_id,
        )
        if log is None:
            raise HTTPException(status_code=404, detail="未找到这条会话讲解记录。")
        if not settings.tts_ready:
            return ChatReplayResponse(
                base64_audio="",
                duration_ms=0,
                provider="tts_not_configured",
                available=False,
            )
        speech_metadata = ChatLogRepository.decode_speech_metadata(log)
        preset = speech_metadata.get("voice_preset") or payload.tts_voice
        profile = build_speech_profile(settings, preset)
        stored_voice_id = speech_metadata.get("voice_id")
        same_engine = (
            speech_metadata.get("provider") == profile.get("provider")
            and speech_metadata.get("model") == profile.get("model")
        )
        voice_override = stored_voice_id if same_engine and isinstance(stored_voice_id, str) else None
        if voice_override:
            profile = build_speech_profile(settings, preset, voice_override=voice_override)
        cache_key = build_speech_cache_key(log.answer, profile)
        audio = _replay_audio_cache.get(cache_key)
        if audio is None:
            try:
                audio = await build_tts_service(
                    settings,
                    preset=preset,
                    voice_override=voice_override,
                ).synthesize(log.answer)
                _replay_audio_cache.put(cache_key, audio)
            except Exception as exc:
                logger.exception("Chat answer replay TTS failed")
                raise HTTPException(status_code=503, detail="语音合成暂时不可用，请稍后重试。") from exc
        return ChatReplayResponse(
            base64_audio=audio.base64_audio,
            duration_ms=max(int(audio.duration_ms), 0),
            provider=audio.provider,
            available=bool(audio.base64_audio),
        )
    finally:
        lease.release()

@router.get("/welcome-audio")
async def get_welcome_audio(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    """Return pre-generated welcome TTS audio for the active avatar config."""
    result = await session.execute(
        select(AvatarConfig).where(AvatarConfig.is_active.is_(True))
    )
    config = result.scalar_one_or_none()
    if config is None:
        return {"base64_audio": "", "duration_ms": 0, "provider": "no_active_config"}

    model_key = _derive_model_key(config.model_path)
    voice_type = config.voice_type

    # Check cache
    cached = get_cached(model_key, voice_type)
    if cached and cached.base64_audio:
        return {
            "base64_audio": cached.base64_audio,
            "duration_ms": cached.duration_ms,
            "provider": cached.provider,
        }

    # Generate on-the-fly if TTS is available
    if settings.tts_ready:
        audio = await generate_and_cache(model_key=model_key, voice_type=voice_type)
        return {
            "base64_audio": audio.base64_audio,
            "duration_ms": audio.duration_ms,
            "provider": audio.provider,
        }

    return {"base64_audio": "", "duration_ms": 0, "provider": "tts_not_configured"}


@router.delete("/visitor-memory/{visitor_id}")
async def clear_visitor_memory(
    visitor_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """清除该游客的跨会话记忆（隐私要求：记忆可查看、可清除）。

    记忆只存行为偏好、不存身份信息；visitor_id 按匿名随机串处理，
    超长或空值直接视为无可删除记录，不暴露任何枚举能力。
    """
    if not visitor_id or len(visitor_id) > 64:
        return {"deleted": 0}
    deleted = await VisitorMemoryRepository(session).delete(visitor_id)
    return {"deleted": deleted}
