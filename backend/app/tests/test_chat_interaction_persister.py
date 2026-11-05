from types import SimpleNamespace

import pytest

from app.repositories.chat_log import ChatLogRepository
from app.schemas.chat import ChatRequest
from app.services.emotion import EmotionLabel, EmotionSignal, FusedEmotion, response_policy_for


def _persister_type():
    from app.services.qa.chat_interaction_persister import ChatInteractionPersister

    return ChatInteractionPersister


@pytest.mark.asyncio
async def test_persister_writes_speech_and_emotion_metadata_before_visitor_updates():
    calls = []

    class RecordingChatLog(ChatLogRepository):
        async def create(self, **kwargs):
            calls.append("chat_log")
            self.created = kwargs
            return SimpleNamespace(id=41)

    class RecordingVisitor:
        async def upsert(self, **kwargs):
            calls.append(("visitor", kwargs))

    class RecordingMemory:
        async def record_visit(self, **kwargs):
            calls.append(("memory", kwargs))

    text_emotion = EmotionSignal(
        EmotionLabel.CONFUSED, confidence=0.8, intensity=0.6, source="text"
    )
    fused_emotion = FusedEmotion(
        EmotionLabel.CONFUSED, confidence=0.8, intensity=0.6, modalities=("text",)
    )
    profile = {
        "provider": "test-provider",
        "voice_preset": "calm",
        "voice_id": "voice-1",
        "format": "mp3",
        "sample_rate": 24000,
        "rate": 100,
        "profile_hash": "profile-1",
    }
    repository = RecordingChatLog.__new__(RecordingChatLog)
    persister = _persister_type()(
        chat_log_repository=repository,
        visitor_repository=RecordingVisitor(),
        visitor_memory_repository=RecordingMemory(),
        speech_profile=profile,
    )

    chat_log_id = await persister.persist(
        session_id="session-1",
        raw_query="原始问题",
        normalized_query="规范问题",
        answer="已生成回答",
        sources=[{"title": "资料"}],
        hit_level="rag",
        latency_ms=123,
        request=ChatRequest(
            query="原始问题", session_id="session-1", visitor_id="visitor-1"
        ),
        active_subject="景点甲",
        text_emotion=text_emotion,
        audio_emotion=None,
        fused_emotion=fused_emotion,
        response_policy=response_policy_for(fused_emotion),
    )

    assert chat_log_id == 41
    assert calls[0] == "chat_log"
    assert calls[1][0] == "visitor"
    assert calls[2] == (
        "memory",
        {
            "visitor_id": "visitor-1",
            "session_id": "session-1",
            "attraction_title": "景点甲",
            "interests": [],
            "narration_audience": "adult",
        },
    )
    assert repository.created["text_emotion"] == "confused"
    assert repository.created["fused_emotion"] == "confused"
    assert repository.created["audio_emotion"] is None
    assert repository.created["response_strategy"] == "confused"
    assert repository.created["speech_metadata"]["answer_version"]
    assert repository.created["speech_metadata"]["profile_hash"] == "profile-1"


@pytest.mark.asyncio
async def test_persister_does_not_fail_completed_answer_when_visitor_updates_fail():
    class RecordingChatLog:
        async def create(self, **kwargs):
            return SimpleNamespace(id=7)

    class FailingVisitor:
        async def upsert(self, **kwargs):
            raise RuntimeError("visitor store unavailable")

    class FailingMemory:
        async def record_visit(self, **kwargs):
            raise RuntimeError("memory store unavailable")

    persister = _persister_type()(
        chat_log_repository=RecordingChatLog(),
        visitor_repository=FailingVisitor(),
        visitor_memory_repository=FailingMemory(),
        speech_profile=None,
    )

    chat_log_id = await persister.persist(
        session_id="session-1",
        raw_query="问题",
        normalized_query="问题",
        answer="回答",
        sources=[],
        hit_level="faq_exact",
        latency_ms=2,
        request=ChatRequest(query="问题", session_id="session-1", visitor_id="visitor-1"),
        active_subject=None,
        text_emotion=None,
        audio_emotion=None,
        fused_emotion=FusedEmotion(
            EmotionLabel.NEUTRAL, confidence=0, intensity=0, modalities=()
        ),
        response_policy=response_policy_for(
            FusedEmotion(EmotionLabel.NEUTRAL, confidence=0, intensity=0, modalities=())
        ),
    )

    assert chat_log_id == 7
