"""Isolated local API harness for true GuideLoop chat/SSE routing without model downloads."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import create_engine

import app.models  # noqa: F401
from app.api.router import api_router
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.db.base import Base
from app.schemas.selection import SelectionContext
from app.services.avatar.stub import StubAvatarService
from app.repositories.guide_loop import GuideLoopRepository
from app.services.qa.cache import QACache
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.intent_router import IntentRouter
from app.services.qa.pipeline import QAPipeline
from app.services.rag.query_rewriter import QueryRewriter
from app.services.tts.stub import StubTTSService

DATABASE = os.environ.get("GUIDELOOP_TEST_DATABASE", "/private/tmp/guideloop-http-sse.db")
URL = "sqlite+aiosqlite:///" + DATABASE
sync = create_engine("sqlite:///" + DATABASE)
Base.metadata.create_all(sync)
sync.dispose()
engine = create_async_engine(URL)
Sessions = async_sessionmaker(engine, expire_on_commit=False)


class EmptyCache:
    async def get(self, key): return None
    async def set(self, *args, **kwargs): return None
    async def invalidate(self, *args, **kwargs): return None

class EmptyRag:
    async def retrieve(self, *args, **kwargs): return []

class LocalLLM:
    async def stream_generate(self, query, documents, *, persona=None, audience=None, memory=None):
        yield "本地回放基线回答。"

class LocalLogs:
    def __init__(self, session): self.session = session
    async def create(self, **kwargs):
        # The production ChatLogRepository commits at the end of a response,
        # which also persists the GuideLoop live-check row in this session.
        await self.session.commit()
        return SimpleNamespace(id=1, **kwargs)

class LocalSelector:
    async def resolve(self, query, selection, context):
        return ResolvedInteraction(selection=selection or SelectionContext(), scope=None, resolution_source="test-harness", active_subject=None)

async def session_dependency():
    async with Sessions() as session:
        yield session

settings = Settings(app_env="test", guide_loop_pilot_enabled=True, admin_password=os.environ.get("ADMIN_PASSWORD", "admin123"), admin_token_secret="guideloop-local-http-harness-secret")
app = FastAPI()
app.state.guide_loop_now = lambda: datetime.fromisoformat(os.environ.get("GUIDELOOP_FROZEN_NOW", "2026-11-10T12:00:00+08:00"))
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5178", "http://localhost:5178"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)
app.dependency_overrides[get_db_session] = session_dependency
app.dependency_overrides[get_app_settings] = lambda: settings

async def build_pipeline(session, settings, *, tts_voice_preset=None, guide_loop_now=None):
    del tts_voice_preset
    return QAPipeline(
        query_rewriter=QueryRewriter(), faq_matcher=FAQMatcher(), qa_cache=QACache(EmptyCache(), 60),
        rag_service=EmptyRag(), llm_service=LocalLLM(), tts_service=StubTTSService(),
        avatar_service=StubAvatarService(), chat_log_repository=LocalLogs(session),
        guided_selector=LocalSelector(), followup_suggestions=FollowUpSuggestionService(),
        intent_router=IntentRouter(), guide_loop_repository=GuideLoopRepository(session), guide_loop_enabled=True,
        guide_loop_now=guide_loop_now,
    )

from app.api import chat as chat_api
chat_api.build_pipeline = build_pipeline
