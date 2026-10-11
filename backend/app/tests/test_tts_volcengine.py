"""火山引擎豆包 TTS 服务测试（TDD RED 阶段）。

契约对标现有 Bailian 实现，保证 pipeline 与前端无需感知切换：
- BaseTTSService.synthesize(text) -> TTSAudio
  成功 provider="volcengine"；失败/不可用降级 provider="volcengine_unavailable"
- StreamingTTSSession: connect / send_text / finish / try_receive / receive / close
- StreamingTTSEvent: audio_chunk | word_timestamps | sentence_begin | task_started | done | error
- word_timestamps.data = {words, sentence_index, original_text, characters}
  characters 为【累计】已确认字符数（pipeline 用 max() 消费做降级重合成定位）
- words 元素键: {"text": str, "begin_time": int ms, "end_time": int ms}
  （pipeline._words_to_viseme_timeline 读取 word["text"]）

火山 v3 双向流式协议（wss://openspeech.bytedance.com/api/v3/tts/bidirection）：
- 二进制帧：header(4B) + event(4B) + [session_id(4B len + bytes)] + payload_len(4B) + payload
- 服务端字幕（enable_subtitle=true）在 TTSSentenceEnd(351) 之后以独立 TTSSubtitle(364) 事件返回
  （官方事件段 350-352 连续编号为早期推测；seed-tts-2.0 线上实测 TTSSubtitle=364），
  startTime/endTime 为【秒】(float)，需 ×1000 转为 int ms。
"""

import asyncio
import base64
import gzip
import json
import struct

import websockets

from app.services.tts import volcengine as ve
from app.services.tts.base import TTSAudio


# ─────────────────────────────── 测试辅助 ───────────────────────────────


def _server_frame(
    event: int,
    session_id: str | None,
    payload: bytes,
    message_type: int = 0b1001,
    serialization: int = 0b0001,
    compression: int = 0b0000,
) -> bytes:
    """构造一帧模拟火山服务端响应的二进制帧（flags=0b0100 表示携带 event number）。"""
    frame = bytearray(
        [
            0b0001_0001,  # version=1, header_size=4
            (message_type << 4) | 0b0100,
            (serialization << 4) | compression,
            0x00,
        ]
    )
    frame.extend(struct.pack(">i", event))
    if session_id is not None:
        sid = session_id.encode()
        frame.extend(struct.pack(">I", len(sid)))
        frame.extend(sid)
    frame.extend(struct.pack(">I", len(payload)))
    frame.extend(payload)
    return bytes(frame)


class FakeWebSocket:
    """按预置脚本回放服务端帧的假 WebSocket；脚本用尽即模拟服务端关闭连接。"""

    def __init__(self, script: list[bytes]) -> None:
        self._script = list(script)
        self.sent: list[bytes] = []
        self.closed = False

    async def send(self, data) -> None:
        self.sent.append(bytes(data))

    async def recv(self) -> bytes:
        if not self._script:
            raise websockets.ConnectionClosed(None, None)
        return self._script.pop(0)

    async def close(self) -> None:
        self.closed = True


def _install_fake_ws(monkeypatch, fake: FakeWebSocket) -> list[dict]:
    """把 websockets.connect 替换为返回 fake 的桩，并记录调用参数。"""
    calls: list[dict] = []

    async def fake_connect(url, additional_headers=None, **kwargs):
        calls.append({"url": url, "headers": additional_headers})
        return fake

    monkeypatch.setattr(ve.websockets, "connect", fake_connect)
    return calls


def _run(coro):
    return asyncio.run(coro)


async def _collect_events(session, limit: int = 64):
    """从会话持续 receive 直到 done/error/超时，返回事件列表。"""
    events = []
    while len(events) < limit:
        event = await session.receive(timeout=0.5)
        if event is None:
            break
        events.append(event)
        if event.type in ("done", "error"):
            break
    return events


def _subtitle_payload(index: int, words: list[dict], text: str = "") -> dict:
    # seed-tts-2.0 线上实测 TTSSubtitle(364) 载荷：words/text 在顶层（与 SentenceEnd 同构），无 sentence 嵌套
    return {"phonemes": [], "index": index, "text": text, "words": words}


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode()


# ─────────────────────────────── 协议帧 ───────────────────────────────


def test_event_constants_match_volcengine_protocol() -> None:
    """事件号必须与火山 v3 双向流式协议官方定义一致。"""
    assert ve.Event.START_CONNECTION == 1
    assert ve.Event.FINISH_CONNECTION == 2
    assert ve.Event.CONNECTION_STARTED == 50
    assert ve.Event.CONNECTION_FAILED == 51
    assert ve.Event.CONNECTION_FINISHED == 52
    assert ve.Event.START_SESSION == 100
    assert ve.Event.FINISH_SESSION == 102
    assert ve.Event.SESSION_STARTED == 150
    assert ve.Event.SESSION_FINISHED == 152
    assert ve.Event.SESSION_FAILED == 153
    assert ve.Event.TASK_REQUEST == 200
    assert ve.Event.TTS_SENTENCE_START == 350
    assert ve.Event.TTS_SENTENCE_END == 351
    assert ve.Event.TTS_RESPONSE == 352
    # 字幕独立事件（在 SentenceEnd 之后返回）；seed-tts-2.0 线上实测为 364
    assert ve.Event.TTS_SUBTITLE == 364


def test_create_start_connection_frame_layout() -> None:
    frame = ve.create_start_connection_frame()
    assert frame[0] == 0b0001_0001  # version=1 | header_size=4
    assert frame[1] >> 4 == 0b0001  # Full client request
    assert frame[1] & 0x0F == 0b0100  # flags: 含 event number
    assert frame[2] >> 4 == 0b0001  # JSON serialization
    assert frame[2] & 0x0F == 0b0000  # 无压缩
    assert frame[3] == 0x00  # reserved
    assert struct.unpack(">i", frame[4:8])[0] == ve.Event.START_CONNECTION
    payload_len = struct.unpack(">I", frame[8:12])[0]
    assert json.loads(frame[12 : 12 + payload_len]) == {}


def test_start_session_frame_roundtrip() -> None:
    meta = {
        "event": 100,
        "req_params": {
            "speaker": "zh_female_cancan_uranus_bigtts",
            "audio_params": {
                "format": "pcm",
                "sample_rate": 24000,
                "enable_subtitle": True,
            },
        },
    }
    frame = ve.create_start_session_frame("sess-1", meta)
    parsed = ve.parse_frame(frame)
    assert parsed["event"] == ve.Event.START_SESSION
    assert parsed["session_id"] == "sess-1"
    assert json.loads(parsed["payload"]) == meta


def test_task_request_frame_roundtrip() -> None:
    frame = ve.create_task_request_frame("欢迎来到灵山胜境", "sess-2")
    parsed = ve.parse_frame(frame)
    assert parsed["event"] == ve.Event.TASK_REQUEST
    assert parsed["session_id"] == "sess-2"
    assert json.loads(parsed["payload"]) == {
        "event": 200,
        "req_params": {"text": "欢迎来到灵山胜境"},
    }


def test_finish_session_and_finish_connection_frames() -> None:
    parsed = ve.parse_frame(ve.create_finish_session_frame("sess-3"))
    assert parsed["event"] == ve.Event.FINISH_SESSION
    assert parsed["session_id"] == "sess-3"
    assert json.loads(parsed["payload"]) == {}

    # 连接级结束帧不携带 session_id
    parsed = ve.parse_frame(ve.create_finish_connection_frame())
    assert parsed["event"] == ve.Event.FINISH_CONNECTION
    assert parsed["session_id"] in (None, "")


def test_parse_frame_gzip_json_payload() -> None:
    """服务端 JSON 帧常为 gzip 压缩，parse_frame 必须解压后再返回。"""
    body = _json_bytes({"text": "你好", "words": []})
    frame = _server_frame(
        ve.Event.TTS_SENTENCE_END, "s4", gzip.compress(body), compression=0b0001
    )
    parsed = ve.parse_frame(frame)
    assert parsed["event"] == ve.Event.TTS_SENTENCE_END
    assert parsed["session_id"] == "s4"
    assert parsed["payload"] == body


def test_parse_frame_raw_audio_frame() -> None:
    frame = _server_frame(
        ve.Event.TTS_RESPONSE, "s5", b"\x01\x02\x03", serialization=0b0000
    )
    parsed = ve.parse_frame(frame)
    assert parsed["event"] == ve.Event.TTS_RESPONSE
    assert parsed["payload"] == b"\x01\x02\x03"


def test_parse_frame_error_frame() -> None:
    """message_type=0b1111 的错误帧：error_code(4B) + error_size(4B) + message。"""
    message = "invalid parameter"
    frame = (
        bytes([0b0001_0001, 0b1111_0000, 0b0000_0000, 0x00])
        + struct.pack(">i", 45000001)
        + struct.pack(">I", len(message))
        + message.encode()
    )
    parsed = ve.parse_frame(frame)
    assert parsed["event"] == 45000001
    assert parsed["error_message"] == "invalid parameter"


# ─────────────────────────────── 鉴权头 ───────────────────────────────


def test_auth_headers_legacy_app_id_mode() -> None:
    svc = ve.VolcengineTTSService(app_id="app-123", access_key="token-456")
    headers = svc._build_auth_headers()
    assert headers["X-Api-App-Key"] == "app-123"
    assert headers["X-Api-Access-Key"] == "token-456"
    assert headers["X-Api-Resource-Id"] == ve.DEFAULT_RESOURCE_ID


def test_auth_headers_api_key_mode() -> None:
    svc = ve.VolcengineTTSService(api_key="xkey-789", resource_id=ve.DEFAULT_RESOURCE_ID)
    headers = svc._build_auth_headers()
    assert headers["X-Api-Key"] == "xkey-789"
    assert headers["X-Api-Resource-Id"] == ve.DEFAULT_RESOURCE_ID


# ─────────────────────────────── 非流式合成 ───────────────────────────────


def test_synthesize_empty_text_returns_empty_audio_without_network(
    monkeypatch,
) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("空文本不应建立网络连接")

    monkeypatch.setattr(ve.websockets, "connect", _boom)
    svc = ve.VolcengineTTSService(api_key="k")
    audio = _run(svc.synthesize("   "))
    assert isinstance(audio, TTSAudio)
    assert audio.base64_audio == ""
    assert audio.duration_ms == 0
    assert audio.provider == "volcengine"


def test_synthesize_collects_audio_and_estimates_duration(monkeypatch) -> None:
    pcm = bytes(48000)  # 24000Hz / 16bit / mono -> 恰好 1.0 秒
    fake = FakeWebSocket(
        [
            _server_frame(ve.Event.CONNECTION_STARTED, "sess", b"{}"),
            _server_frame(ve.Event.SESSION_STARTED, "sess", b"{}"),
            _server_frame(ve.Event.TTS_RESPONSE, "sess", pcm, serialization=0b0000),
            _server_frame(
                ve.Event.SESSION_FINISHED,
                "sess",
                _json_bytes({"usage": {"text_words": 2}}),
            ),
            _server_frame(ve.Event.CONNECTION_FINISHED, "sess", b"{}"),
        ]
    )
    calls = _install_fake_ws(monkeypatch, fake)

    svc = ve.VolcengineTTSService(app_id="app-123", access_key="token-456", voice="zh_female_cancan_uranus_bigtts")
    audio = _run(svc.synthesize("你好"))

    assert audio.provider == "volcengine"
    # 非流式 audio 事件要能被前端 AudioContext.decodeAudioData() 解码，必须是 WAV 容器而非裸 PCM
    decoded = base64.b64decode(audio.base64_audio)
    assert decoded[:4] == b"RIFF"
    assert decoded[8:12] == b"WAVE"
    data_marker = decoded.index(b"data", 12)
    assert int.from_bytes(decoded[data_marker + 4 : data_marker + 8], "little") == len(pcm)
    assert decoded[data_marker + 8 : data_marker + 8 + len(pcm)] == pcm
    assert audio.duration_ms == 1000

    # 端点与鉴权
    assert calls[0]["url"] == ve.BIDIRECTIONAL_WS_URL
    headers = calls[0]["headers"]
    assert headers["X-Api-App-Key"] == "app-123"
    assert headers["X-Api-Access-Key"] == "token-456"

    # 发送顺序：start_connection → start_session → task_request → finish_session
    sent_events = [ve.parse_frame(m)["event"] for m in fake.sent]
    assert sent_events[:4] == [
        ve.Event.START_CONNECTION,
        ve.Event.START_SESSION,
        ve.Event.TASK_REQUEST,
        ve.Event.FINISH_SESSION,
    ]
    # 全文一次性作为 TaskRequest 文本发出
    task_meta = json.loads(ve.parse_frame(fake.sent[2])["payload"])
    assert task_meta["req_params"]["text"] == "你好"
    # start_session 请求参数：pcm / 24000 / enable_subtitle
    start_meta = json.loads(ve.parse_frame(fake.sent[1])["payload"])
    audio_params = start_meta["req_params"]["audio_params"]
    assert start_meta["req_params"]["speaker"] == "zh_female_cancan_uranus_bigtts"
    assert audio_params["format"] == "pcm"
    assert audio_params["sample_rate"] == 24000
    assert audio_params["enable_subtitle"] is True


def test_synthesize_connection_failure_returns_unavailable(monkeypatch) -> None:
    async def failing_connect(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(ve.websockets, "connect", failing_connect)
    svc = ve.VolcengineTTSService(api_key="k")
    audio = _run(svc.synthesize("你好"))
    assert audio.provider == "volcengine_unavailable"
    assert audio.base64_audio == ""
    assert audio.duration_ms == 0


# ─────────────────────────────── 流式会话 ───────────────────────────────


def test_streaming_session_emits_audio_chunks_and_done(monkeypatch) -> None:
    fake = FakeWebSocket(
        [
            _server_frame(ve.Event.CONNECTION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.SESSION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.TTS_RESPONSE, "s", b"chunk-a", serialization=0b0000),
            _server_frame(ve.Event.TTS_RESPONSE, "s", b"chunk-b", serialization=0b0000),
            _server_frame(ve.Event.SESSION_FINISHED, "s", b"{}"),
        ]
    )
    _install_fake_ws(monkeypatch, fake)

    async def scenario():
        session = ve.VolcengineStreamingTTSSession(api_key="k")
        await session.connect()
        await session.send_text("你好，")
        await session.send_text("欢迎来到灵山胜境。")
        await session.finish()
        events = await _collect_events(session)
        tail = session.try_receive()
        await session.close()
        return events, tail

    events, tail = _run(scenario())
    types = [ev.type for ev in events]
    assert types.count("audio_chunk") == 2
    audio_payloads = [ev.data for ev in events if ev.type == "audio_chunk"]
    assert audio_payloads == [b"chunk-a", b"chunk-b"]
    assert types[-1] == "done"
    # 队列已排空
    assert tail is None


def test_streaming_session_converts_subtitle_seconds_to_ms(monkeypatch) -> None:
    """TTSSubtitle(364，线上实测事件号) 的 startTime/endTime 为秒，必须转为 int ms 且文本键为 text。

    本测试故意使用字面量 364 而非 Event 常量，钉死线上真实事件号，防止常量漂移。
    """
    fake = FakeWebSocket(
        [
            _server_frame(ve.Event.CONNECTION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.SESSION_STARTED, "s", b"{}"),
            _server_frame(
                ve.Event.TTS_SENTENCE_START,
                "s",
                _json_bytes({"text": "欢迎来到灵山胜境。"}),
            ),
            _server_frame(ve.Event.TTS_RESPONSE, "s", b"audio", serialization=0b0000),
            _server_frame(
                ve.Event.TTS_SENTENCE_END,
                "s",
                _json_bytes({"text": "欢迎来到灵山胜境。", "words": []}),
            ),
            _server_frame(
                364,
                "s",
                _json_bytes(
                    _subtitle_payload(
                        0,
                        [
                            {"word": "欢迎", "startTime": 0.0, "endTime": 0.155},
                            {"word": "来到", "startTime": 0.155, "endTime": 0.285},
                        ],
                        text="欢迎来到灵山胜境。",
                    )
                ),
            ),
            _server_frame(
                ve.Event.SESSION_FINISHED,
                "s",
                _json_bytes({"usage": {"text_words": 4}}),
            ),
        ]
    )
    _install_fake_ws(monkeypatch, fake)

    async def scenario():
        session = ve.VolcengineStreamingTTSSession(api_key="k")
        await session.connect()
        await session.send_text("欢迎来到灵山胜境。")
        await session.finish()
        events = await _collect_events(session)
        await session.close()
        return events

    events = _run(scenario())
    types = [ev.type for ev in events]

    # SentenceStart → sentence_begin（data 为文本）
    begin_event = next(ev for ev in events if ev.type == "sentence_begin")
    assert begin_event.data == "欢迎来到灵山胜境。"

    # Subtitle → word_timestamps
    ts = next(ev for ev in events if ev.type == "word_timestamps")
    words = ts.data["words"]
    assert [w["text"] for w in words] == ["欢迎", "来到"]
    assert words[0]["begin_time"] == 0
    assert words[0]["end_time"] == 155
    assert words[1]["begin_time"] == 155
    assert words[1]["end_time"] == 285
    assert isinstance(words[0]["begin_time"], int)
    assert ts.data["sentence_index"] == 0
    assert ts.data["original_text"] == "欢迎来到灵山胜境。"
    # characters 为累计已确认字符数（本句 2 词共 4 字）
    assert ts.data["characters"] == 4
    assert "done" in types


def test_streaming_session_accumulates_sentence_timeline(monkeypatch) -> None:
    """第二句字幕又从 0 计时时，必须追加偏移，保持整段回答单一时间轴。"""
    fake = FakeWebSocket(
        [
            _server_frame(ve.Event.CONNECTION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.SESSION_STARTED, "s", b"{}"),
            # 句 1：0 - 300ms
            _server_frame(
                ve.Event.TTS_SENTENCE_START, "s", _json_bytes({"text": "灵山"})
            ),
            _server_frame(
                ve.Event.TTS_SENTENCE_END,
                "s",
                _json_bytes({"text": "灵山", "words": []}),
            ),
            _server_frame(
                ve.Event.TTS_SUBTITLE,
                "s",
                _json_bytes(
                    _subtitle_payload(0, [{"word": "灵山", "startTime": 0.0, "endTime": 0.3}])
                ),
            ),
            # 句 2：服务端重新从 20ms 计时
            _server_frame(
                ve.Event.TTS_SENTENCE_START, "s", _json_bytes({"text": "大佛"})
            ),
            _server_frame(
                ve.Event.TTS_SENTENCE_END,
                "s",
                _json_bytes({"text": "大佛", "words": []}),
            ),
            _server_frame(
                ve.Event.TTS_SUBTITLE,
                "s",
                _json_bytes(
                    _subtitle_payload(1, [{"word": "大佛", "startTime": 0.02, "endTime": 0.15}])
                ),
            ),
            _server_frame(ve.Event.SESSION_FINISHED, "s", b"{}"),
        ]
    )
    _install_fake_ws(monkeypatch, fake)

    async def scenario():
        session = ve.VolcengineStreamingTTSSession(api_key="k")
        await session.connect()
        await session.finish()
        events = await _collect_events(session)
        await session.close()
        return events

    events = _run(scenario())
    ts_events = [ev for ev in events if ev.type == "word_timestamps"]
    assert len(ts_events) == 2

    first_words = ts_events[0].data["words"]
    assert first_words[0]["begin_time"] == 0
    assert first_words[0]["end_time"] == 300
    assert ts_events[0].data["sentence_index"] == 0
    assert ts_events[0].data["characters"] == 2

    second_words = ts_events[1].data["words"]
    assert second_words[0]["begin_time"] == 320  # 300 偏移 + 20
    assert second_words[0]["end_time"] == 450  # 300 偏移 + 150
    assert ts_events[1].data["sentence_index"] == 1
    # characters 跨句累计：2 + 2
    assert ts_events[1].data["characters"] == 4


def test_streaming_session_accepts_inline_words_from_sentence_end(monkeypatch) -> None:
    """1.0 模型（enable_timestamp）的字级时间戳内嵌在 TTSSentenceEnd.words 中。"""
    fake = FakeWebSocket(
        [
            _server_frame(ve.Event.CONNECTION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.SESSION_STARTED, "s", b"{}"),
            _server_frame(
                ve.Event.TTS_SENTENCE_END,
                "s",
                _json_bytes(
                    {
                        "text": "你好",
                        "words": [
                            {"word": "你", "startTime": 0.01, "endTime": 0.1},
                            {"word": "好", "startTime": 0.1, "endTime": 0.2},
                        ],
                    }
                ),
            ),
            _server_frame(ve.Event.SESSION_FINISHED, "s", b"{}"),
        ]
    )
    _install_fake_ws(monkeypatch, fake)

    async def scenario():
        session = ve.VolcengineStreamingTTSSession(api_key="k")
        await session.connect()
        await session.finish()
        events = await _collect_events(session)
        await session.close()
        return events

    events = _run(scenario())
    ts = next(ev for ev in events if ev.type == "word_timestamps")
    words = ts.data["words"]
    assert [w["text"] for w in words] == ["你", "好"]
    assert words[0]["begin_time"] == 10
    assert words[0]["end_time"] == 100
    assert words[1]["begin_time"] == 100
    assert words[1]["end_time"] == 200
    assert ts.data["characters"] == 2


def test_streaming_session_session_failed_emits_error(monkeypatch) -> None:
    fake = FakeWebSocket(
        [
            _server_frame(ve.Event.CONNECTION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.SESSION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.TTS_RESPONSE, "s", b"audio", serialization=0b0000),
            _server_frame(
                ve.Event.SESSION_FAILED,
                "s",
                _json_bytes({"message": "voice not found"}),
            ),
        ]
    )
    _install_fake_ws(monkeypatch, fake)

    async def scenario():
        session = ve.VolcengineStreamingTTSSession(api_key="k")
        await session.connect()
        await session.send_text("你好")
        await session.finish()
        events = await _collect_events(session)
        await session.close()
        return events

    events = _run(scenario())
    error_events = [ev for ev in events if ev.type == "error"]
    assert error_events, "SESSION_FAILED 必须产出 error 事件"
    assert "voice not found" in str(error_events[0].data)


def test_streaming_session_connect_failure_raises_runtime_error(monkeypatch) -> None:
    async def failing_connect(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(ve.websockets, "connect", failing_connect)

    async def scenario():
        session = ve.VolcengineStreamingTTSSession(api_key="k")
        try:
            await session.connect()
        except RuntimeError:
            return "runtime-error"
        finally:
            await session.close()
        return "no-error"

    assert _run(scenario()) == "runtime-error"


def test_streaming_service_factory_creates_sessions(monkeypatch) -> None:
    svc = ve.VolcengineStreamingTTSService(
        api_key="k",
        voice="zh_female_cancan_uranus_bigtts",
        sample_rate=24000,
    )
    session_a = svc.create_session()
    session_b = svc.create_session()
    assert session_a is not session_b
    assert isinstance(session_a, ve.VolcengineStreamingTTSSession)
    assert isinstance(session_b, ve.VolcengineStreamingTTSSession)

    # synthesize_stream 便捷方法：完整走一遍协议并产出音频事件；
    # done/error 由便捷方法内部消费（与 Bailian synthesize_stream 行为一致），
    # async for 正常收尾。
    fake = FakeWebSocket(
        [
            _server_frame(ve.Event.CONNECTION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.SESSION_STARTED, "s", b"{}"),
            _server_frame(ve.Event.TTS_RESPONSE, "s", b"pcm-1", serialization=0b0000),
            _server_frame(ve.Event.SESSION_FINISHED, "s", b"{}"),
        ]
    )
    _install_fake_ws(monkeypatch, fake)

    async def scenario():
        chunks: list[bytes] = []
        async for event in svc.synthesize_stream("你好"):
            if event.type == "audio_chunk":
                chunks.append(event.data)
        return chunks

    chunks = _run(scenario())
    assert chunks == [b"pcm-1"]
