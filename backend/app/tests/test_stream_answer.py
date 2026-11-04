from app.services.qa.stream_answer import StreamAnswerBuffer
from app.services.qa.stream_completion import final_audio_segments


def test_stream_answer_buffer_keeps_partial_sentence_and_emits_completed_text():
    answer = StreamAnswerBuffer()
    answer.append("第一句。第二句")

    assert answer.full_answer == "第一句。第二句"
    assert answer.take_speakable_sentences() == ["第一句。"]
    assert answer.sentence_buffer == "第二句"


def test_stream_answer_buffer_preserves_existing_comma_length_boundary():
    answer = StreamAnswerBuffer()
    answer.append("逗号前面八个字，后续内容")

    assert answer.take_speakable_sentences() == ["逗号前面八个字，"]
    assert answer.sentence_buffer == "后续内容"


def test_final_audio_prefers_full_faq_text_over_partial_stream_offsets():
    answer = StreamAnswerBuffer()
    answer.append("经过改写的片段")

    assert final_audio_segments(
        answer,
        faq_documents_present=True,
        text_only=False,
        streaming_requested=True,
        streaming_tts_failed=True,
        tts_confirmed_chars=3,
    ) == ("经过改写的片段",)


def test_final_audio_fallback_starts_after_confirmed_streaming_characters():
    answer = StreamAnswerBuffer()
    answer.append("前面已确认，后面需要补播。")

    assert final_audio_segments(
        answer,
        faq_documents_present=False,
        text_only=False,
        streaming_requested=True,
        streaming_tts_failed=True,
        tts_confirmed_chars=5,
    ) == ("，后面需要补播。",)


def test_final_audio_uses_http_tts_tail_and_skips_text_only_requests():
    answer = StreamAnswerBuffer()
    answer.append("已经切句。未完成尾句")
    answer.take_speakable_sentences()

    assert final_audio_segments(
        answer,
        faq_documents_present=False,
        text_only=False,
        streaming_requested=False,
        streaming_tts_failed=False,
        tts_confirmed_chars=0,
    ) == ("未完成尾句",)
    assert final_audio_segments(
        answer,
        faq_documents_present=False,
        text_only=True,
        streaming_requested=False,
        streaming_tts_failed=False,
        tts_confirmed_chars=0,
    ) == ()
