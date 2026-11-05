from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Iterable

from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_turn import StreamTurn


class StreamTurnFactory:
    """Build one generation stream and its producer/audio lifecycle from request evidence."""

    def __init__(
        self,
        *,
        llm_service,
        streaming_tts_service,
        audio_worker: Callable[..., object],
        adapt_tts_event: Callable[[object], Iterable[StreamEvent]],
        coerce_llm_event: Callable[[object], object],
    ) -> None:
        self.llm_service = llm_service
        self.streaming_tts_service = streaming_tts_service
        self.audio_worker = audio_worker
        self.adapt_tts_event = adapt_tts_event
        self.coerce_llm_event = coerce_llm_event

    def create(
        self,
        *,
        query: str,
        documents: list,
        persona: str | None,
        audience: str | None,
        memory: str | None,
        confirmed_visual_title: str | None,
        vision_context_present: bool,
        faq_documents_present: bool,
        text_only: bool,
        epoch_is_current: Callable[[], Awaitable[bool]],
        emotion_aware_query: Callable[[str], str],
    ) -> tuple[StreamTurn, bool]:
        streaming_requested = (
            self.streaming_tts_service is not None
            and not text_only
            and not faq_documents_present
        )
        generation_query = query
        if confirmed_visual_title is not None:
            # Catalog title is data, not an instruction; JSON escaping keeps its context opaque.
            title_data = json.dumps(confirmed_visual_title, ensure_ascii=False)
            generation_query = (
                "游客已从已发布目录确认本次讲解的景点名称（JSON字符串）："
                f"{title_data}。图片识别线索未经确认，仅用于检索，不得作为事实；"
                "回答只能根据参考资料，资料不足时明确说明。\n"
                f"游客原始问题：{query}"
            )
        elif vision_context_present:
            generation_query = (
                "图片识别线索未经确认，仅用于检索；不要断言照片中的景点身份。"
                "只能依据参考资料提供有条件的说明，身份不明确时请游客选择或确认景点。\n"
                f"游客原始问题：{query}"
            )

        llm_source = self.llm_service.stream_generate(
            emotion_aware_query(generation_query),
            documents,
            persona=persona,
            audience=audience,
            memory=memory,
        )
        tts_session = (
            self.streaming_tts_service.create_session() if streaming_requested else None
        )
        turn = StreamTurn(
            llm_source=llm_source,
            tts_session=tts_session,
            streaming_requested=streaming_requested,
            text_only=text_only,
            faq_documents_present=faq_documents_present,
            epoch_is_current=epoch_is_current,
            audio_worker=self.audio_worker,
            adapt_tts_event=self.adapt_tts_event,
            coerce_llm_event=self.coerce_llm_event,
        )
        return turn, streaming_requested
