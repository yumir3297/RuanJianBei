import asyncio

from app.services.qa.stream_mux import StreamMuxState
from app.services.qa.streaming_tts_buffer import StreamingTTSBuffer
from app.services.qa.streaming_tts_controller import StreamingTTSController


class RecordingSession:
    def __init__(self, fail_send=False):
        self.sent = []
        self.finished = 0
        self.fail_send = fail_send

    async def send_text(self, text):
        if self.fail_send:
            raise RuntimeError("socket closed")
        self.sent.append(text)

    async def finish(self):
        self.finished += 1


def test_streaming_tts_controller_flushes_and_finishes_buffer_once():
    async def run():
        state = StreamMuxState(streaming_requested=True)
        state.tts_connected = True
        buffer = StreamingTTSBuffer()
        buffer.append("完整句子。")
        finished = asyncio.Event()
        session = RecordingSession()
        controller = StreamingTTSController(session, state, buffer, finished)

        assert await controller.flush_ready()
        state.llm_done = True
        assert await controller.finish_if_ready()
        assert not await controller.finish_if_ready()
        return session, finished, state

    session, finished, state = asyncio.run(run())
    assert session.sent == ["完整句子。"]
    assert session.finished == 1
    assert finished.is_set()
    assert state.tts_finish_sent


def test_streaming_tts_controller_routes_send_failure_to_http_fallback():
    async def run():
        state = StreamMuxState(streaming_requested=True)
        state.tts_connected = True
        buffer = StreamingTTSBuffer()
        buffer.append("足够长的流式语音片段用于发送。")
        controller = StreamingTTSController(
            RecordingSession(fail_send=True), state, buffer, asyncio.Event()
        )

        result = await controller.flush_ready()
        return result, state

    result, state = asyncio.run(run())
    assert not result
    assert state.tts_failed
    assert state.tts_done
