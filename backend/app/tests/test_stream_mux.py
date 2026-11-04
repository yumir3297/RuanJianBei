from types import SimpleNamespace

from app.services.qa.stream_mux import StreamMuxState


def test_stream_mux_tracks_terminal_events_and_tts_fallback_progress():
    mux = StreamMuxState(streaming_requested=True)

    assert mux.consume("llm", "token").llm_payload == "token"
    mux.consume("tts_connected", None)
    delivery = mux.consume(
        "tts",
        SimpleNamespace(type="word_timestamps", data={"characters": 7}),
    )
    assert delivery.tts_payload.type == "word_timestamps"
    assert mux.tts_confirmed_chars == 7

    mux.consume("tts", SimpleNamespace(type="error", data={}))
    assert mux.tts_failed
    assert mux.tts_done

    mux.consume("llm_done", None)
    assert mux.llm_done


def test_stream_mux_marks_connection_failure_for_http_fallback():
    mux = StreamMuxState(streaming_requested=True)

    delivery = mux.consume("tts_connect_error", RuntimeError("offline"))

    assert delivery.warning == "connect"
    assert mux.tts_failed
    assert mux.tts_done
