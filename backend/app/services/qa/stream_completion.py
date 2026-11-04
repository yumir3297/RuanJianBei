from __future__ import annotations

from app.services.qa.stream_answer import StreamAnswerBuffer


def final_audio_segments(
    answer: StreamAnswerBuffer,
    *,
    faq_documents_present: bool,
    text_only: bool,
    streaming_requested: bool,
    streaming_tts_failed: bool,
    tts_confirmed_chars: int,
) -> tuple[str, ...]:
    """Choose only the unsent answer text that needs HTTP TTS at stream completion."""
    if text_only:
        return ()

    if faq_documents_present:
        text = answer.full_answer.strip()
    elif streaming_requested and streaming_tts_failed:
        text = answer.full_answer[tts_confirmed_chars:].strip()
    elif not streaming_requested:
        text = answer.sentence_buffer.strip()
    else:
        text = ""

    return (text,) if text else ()
