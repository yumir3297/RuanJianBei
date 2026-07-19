from app.services.tts.streaming import StreamingTTSSession


def test_task_finished_emits_done_without_waiting_for_socket_close() -> None:
    session = StreamingTTSSession("test-key")

    session._handle_json_message({"header": {"event": "task-finished"}, "payload": {}})
    session._handle_json_message({"header": {"event": "task-finished"}, "payload": {}})

    assert session.try_receive().type == "done"
    assert session.try_receive() is None


def test_sentence_timestamps_are_normalized_to_one_timeline() -> None:
    session = StreamingTTSSession("test-key")
    first = [{"text": "你", "begin_time": 0, "end_time": 100}]
    second = [{"text": "好", "begin_time": 0, "end_time": 120}]

    normalized_first = session._normalize_word_timestamps(first)
    normalized_second = session._normalize_word_timestamps(second)

    assert normalized_first[0]["begin_time"] == 0
    assert normalized_second[0]["begin_time"] == 100
    assert normalized_second[0]["end_time"] == 220
