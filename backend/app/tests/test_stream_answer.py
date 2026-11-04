from app.services.qa.stream_answer import StreamAnswerBuffer


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
