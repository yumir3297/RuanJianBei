import asyncio

from app.models.chat_log import ChatLog
from app.repositories.chat_log import ChatLogRepository
from app.tests.async_db import open_test_session


def test_chat_log_lookup_requires_matching_session_id():
    async def scenario():
        engine, session = await open_test_session()
        try:
            session.add(ChatLog(
                session_id="session-a",
                raw_query="问题",
                normalized_query="问题",
                answer="已保存答案",
                sources="[]",
            ))
            await session.commit()

            repository = ChatLogRepository(session)
            matching = await repository.get_for_session(1, "session-a")
            other_session = await repository.get_for_session(1, "session-b")
            missing = await repository.get_for_session(999, "session-a")

            assert matching is not None
            assert matching.answer == "已保存答案"
            assert other_session is None
            assert missing is None
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_chat_log_repository_round_trips_speech_metadata():
    async def scenario():
        engine, session = await open_test_session()
        try:
            metadata = {
                "answer_version": "answer-hash",
                "voice_preset": "deep-male",
                "profile_hash": "profile-hash",
            }
            log = await ChatLogRepository(session).create(
                session_id="metadata-session",
                raw_query="问题",
                normalized_query="问题",
                answer="答案",
                sources=[],
                hit_level="rag",
                latency_ms=1,
                speech_metadata=metadata,
            )
            await session.refresh(log)

            assert ChatLogRepository.decode_speech_metadata(log) == metadata
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
