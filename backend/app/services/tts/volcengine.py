"""火山引擎豆包 TTS 服务 —— v3 双向流式协议实现。

接口契约与百炼实现完全对齐（BaseTTSService / StreamingTTSSession 模式），
pipeline 与前端无需感知 provider 切换：

- VolcengineTTSService.synthesize(text) -> TTSAudio
  成功 provider="volcengine"；失败/不可用降级 provider="volcengine_unavailable"
- VolcengineStreamingTTSSession: connect / send_text / finish / try_receive / receive / close
- 事件复用 StreamingTTSEvent：audio_chunk | word_timestamps | sentence_begin | task_started | done | error
- word_timestamps.data = {words, sentence_index, original_text, characters}
  characters 为【累计】已确认字符数（pipeline 用 max() 消费做降级重合成定位）
- words 元素键: {"text": str, "begin_time": int ms, "end_time": int ms}
  （pipeline._words_to_viseme_timeline 读取 word["text"]）

火山 v3 双向流式协议（wss://openspeech.bytedance.com/api/v3/tts/bidirection）：
- 二进制帧（大端）：header(4B) + event(4B) + [session_id(4B len + bytes)] + payload_len(4B) + payload
- header: version|header_size / message_type<<4|flags / serialization<<4|compression / reserved
- flags=0b0100 表示携带 event number
- TTSSubtitle(364) 的 startTime/endTime 为【秒】(float)，需 ×1000 转 int ms
- 1.0 模型（enable_timestamp）的字级时间戳内嵌于 TTSSentenceEnd.words
- 鉴权双模：新版 X-Api-Key / 旧版 X-Api-App-Key(APP ID) + X-Api-Access-Key
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import json
import logging
import struct
import uuid

import websockets

from app.services.tts.base import BaseTTSService, TTSAudio
from app.services.tts.streaming import StreamingTTSEvent

logger = logging.getLogger(__name__)

BIDIRECTIONAL_WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
DEFAULT_RESOURCE_ID = "seed-tts-2.0"
DEFAULT_VOICE = "zh_female_cancan_uranus_bigtts"

# ── 协议常量 ──
_MESSAGE_TYPE_FULL_CLIENT = 0b0001
_MESSAGE_TYPE_FULL_SERVER = 0b1001
_MESSAGE_TYPE_AUDIO_ONLY = 0b1011
_MESSAGE_TYPE_ERROR = 0b1111
_FLAG_HAS_EVENT_NUMBER = 0b0100
_SERIALIZATION_JSON = 0b0001
_COMPRESSION_NONE = 0b0000
_COMPRESSION_GZIP = 0b0001


class Event:
    """火山 v3 双向流式协议事件号（客户端 + 服务端）。"""

    START_CONNECTION = 1
    FINISH_CONNECTION = 2
    CONNECTION_STARTED = 50
    CONNECTION_FAILED = 51
    CONNECTION_FINISHED = 52
    START_SESSION = 100
    FINISH_SESSION = 102
    SESSION_STARTED = 150
    SESSION_FINISHED = 152
    SESSION_FAILED = 153
    USAGE_RESPONSE = 154
    TASK_REQUEST = 200
    TTS_SENTENCE_START = 350
    TTS_SENTENCE_END = 351
    TTS_RESPONSE = 352
    # 字幕独立事件（在 SentenceEnd 之后返回）；seed-tts-2.0 线上实测为 364
    TTS_SUBTITLE = 364


# ─────────────────────────────── 帧构造 ───────────────────────────────


def _build_frame(
    event: int,
    payload: bytes,
    session_id: str | None = None,
    message_type: int = _MESSAGE_TYPE_FULL_CLIENT,
) -> bytes:
    """构造客户端帧：header(4B) + event(4B) + [session_id] + payload_len(4B) + payload。"""
    frame = bytearray(
        [
            0b0001_0001,  # version=1 | header_size=4
            (message_type << 4) | _FLAG_HAS_EVENT_NUMBER,
            (_SERIALIZATION_JSON << 4) | _COMPRESSION_NONE,
            0x00,  # reserved
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


def create_start_connection_frame() -> bytes:
    return _build_frame(Event.START_CONNECTION, json.dumps({}).encode())


def create_finish_connection_frame() -> bytes:
    return _build_frame(Event.FINISH_CONNECTION, json.dumps({}).encode())


def create_start_session_frame(session_id: str, meta: dict) -> bytes:
    return _build_frame(
        Event.START_SESSION,
        json.dumps(meta, ensure_ascii=False).encode(),
        session_id=session_id,
    )


def create_task_request_frame(text: str, session_id: str) -> bytes:
    meta = {"event": Event.TASK_REQUEST, "req_params": {"text": text}}
    return _build_frame(
        Event.TASK_REQUEST,
        json.dumps(meta, ensure_ascii=False).encode(),
        session_id=session_id,
    )


def create_finish_session_frame(session_id: str) -> bytes:
    return _build_frame(
        Event.FINISH_SESSION,
        json.dumps({}).encode(),
        session_id=session_id,
    )


# ─────────────────────────────── 帧解析 ───────────────────────────────


def parse_frame(frame: bytes) -> dict:
    """解析一帧服务端响应；gzip JSON 自动解压；error 帧返回 error_message。"""
    if len(frame) < 4:
        raise ValueError("火山 TTS 帧过短")
    header = frame[:4]
    header_size = (header[0] & 0x0F) * 4
    message_type = header[1] >> 4
    flags = header[1] & 0x0F
    serialization = header[2] >> 4
    compression = header[2] & 0x0F

    # 错误帧：header + error_code(4B) + error_size(4B) + error_message(UTF8)
    if message_type == _MESSAGE_TYPE_ERROR:
        error_code = struct.unpack(">i", frame[4:8])[0]
        error_size = struct.unpack(">I", frame[8:12])[0]
        error_message = frame[12 : 12 + error_size].decode("utf-8", errors="replace")
        return {
            "event": error_code,
            "message_type": message_type,
            "serialization": serialization,
            "compression": compression,
            "session_id": None,
            "payload": b"",
            "error_code": error_code,
            "error_message": error_message,
        }

    event = struct.unpack(">i", frame[4:8])[0]
    payload_start = header_size
    if flags & _FLAG_HAS_EVENT_NUMBER:
        payload_start += 4

    # session_id 是否存在由事件类型决定：客户端 START/FINISH_CONNECTION 不携带，
    # 其余客户端帧与服务端响应帧（Full server / Audio-only）均携带。
    session_id: str | None = None
    carries_session = message_type in (
        _MESSAGE_TYPE_FULL_SERVER,
        _MESSAGE_TYPE_AUDIO_ONLY,
    ) or (
        message_type == _MESSAGE_TYPE_FULL_CLIENT
        and event not in (Event.START_CONNECTION, Event.FINISH_CONNECTION)
    )
    if carries_session:
        sid_len = struct.unpack(">I", frame[payload_start : payload_start + 4])[0]
        session_id = frame[payload_start + 4 : payload_start + 4 + sid_len].decode(
            "utf-8", errors="replace"
        )
        payload_start += 4 + sid_len

    payload_len = struct.unpack(">I", frame[payload_start : payload_start + 4])[0]
    payload = frame[payload_start + 4 : payload_start + 4 + payload_len]

    if compression == _COMPRESSION_GZIP:
        payload = gzip.decompress(payload)

    return {
        "event": event,
        "message_type": message_type,
        "serialization": serialization,
        "compression": compression,
        "session_id": session_id,
        "payload": payload,
    }


def _decode_json_payload(payload: bytes) -> dict:
    if not payload:
        return {}
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _pcm_duration_ms(
    num_bytes: int, sample_rate: int, bits_per_sample: int = 16, channels: int = 1
) -> int:
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    if byte_rate <= 0:
        return 0
    return num_bytes * 1000 // byte_rate


# ─────────────────────────────── 非流式合成 ───────────────────────────────


class VolcengineTTSService(BaseTTSService):
    """火山豆包 TTS 非流式合成（内部复用双向流式协议，一次请求收集全部音频）。"""

    def __init__(
        self,
        app_id: str | None = None,
        access_key: str | None = None,
        api_key: str | None = None,
        resource_id: str | None = None,
        voice: str = DEFAULT_VOICE,
        format: str = "pcm",
        sample_rate: int = 24000,
        enable_subtitle: bool = True,
    ) -> None:
        self._app_id = app_id
        self._access_key = access_key
        self._api_key = api_key
        self._resource_id = resource_id or DEFAULT_RESOURCE_ID
        self._voice = voice
        self._format = format
        self._sample_rate = sample_rate
        self._enable_subtitle = enable_subtitle

    def _build_auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"X-Api-Resource-Id": self._resource_id}
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        elif self._app_id and self._access_key:
            headers["X-Api-App-Key"] = self._app_id
            headers["X-Api-Access-Key"] = self._access_key
        return headers

    def _build_start_session_meta(self) -> dict:
        return {
            "event": Event.START_SESSION,
            "req_params": {
                "speaker": self._voice,
                "audio_params": {
                    "format": self._format,
                    "sample_rate": self._sample_rate,
                    "enable_subtitle": self._enable_subtitle,
                },
            },
        }

    async def synthesize(self, text: str) -> TTSAudio:
        """合成整段文本。空文本返回空音频（不建网络连接）；失败降级为空音频。"""
        if not text or not text.strip():
            return TTSAudio(base64_audio="", duration_ms=0, provider="volcengine")

        try:
            pcm = await self._synthesize_pcm(text)
        except Exception:
            logger.exception("火山 TTS 合成失败，降级为空音频")
            return TTSAudio(base64_audio="", duration_ms=0, provider="volcengine_unavailable")

        return TTSAudio(
            base64_audio=base64.b64encode(pcm).decode(),
            duration_ms=_pcm_duration_ms(len(pcm), self._sample_rate),
            provider="volcengine",
        )

    async def _synthesize_pcm(self, text: str) -> bytes:
        session_id = uuid.uuid4().hex
        ws = await websockets.connect(
            BIDIRECTIONAL_WS_URL,
            additional_headers=self._build_auth_headers(),
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        )
        pcm = bytearray()
        try:
            await ws.send(create_start_connection_frame())
            await ws.send(create_start_session_frame(session_id, self._build_start_session_meta()))
            await ws.send(create_task_request_frame(text, session_id))
            await ws.send(create_finish_session_frame(session_id))

            while True:
                try:
                    message = await ws.recv()
                except websockets.ConnectionClosed:
                    break
                if not isinstance(message, (bytes, bytearray)):
                    continue
                parsed = parse_frame(bytes(message))
                event = parsed["event"]

                if parsed.get("error_message"):
                    raise RuntimeError(
                        f"火山 TTS 错误 {event}: {parsed['error_message']}"
                    )
                if event == Event.TTS_RESPONSE:
                    pcm.extend(parsed["payload"])
                elif event == Event.SESSION_FINISHED:
                    break
                elif event in (Event.SESSION_FAILED, Event.CONNECTION_FAILED):
                    detail = _decode_json_payload(parsed["payload"]).get("message", "")
                    raise RuntimeError(f"火山 TTS 会话失败: {detail or parsed['payload']!r}")

            try:
                await ws.send(create_finish_connection_frame())
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

        if not pcm:
            raise RuntimeError("火山 TTS 未返回音频数据")
        return bytes(pcm)


# ─────────────────────────────── 流式会话 ───────────────────────────────


class VolcengineStreamingTTSSession:
    """火山豆包流式 TTS 会话，管理一次回答的 WebSocket 双向连接。

    用法与百炼 StreamingTTSSession 完全一致：
        session = VolcengineStreamingTTSSession(api_key, voice)
        await session.connect()
        await session.send_text("你好，")
        await session.send_text("欢迎来到灵山胜境。")
        await session.finish()
        # try_receive() / receive() 获取音频块和字时间戳
        await session.close()
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice: str = DEFAULT_VOICE,
        sample_rate: int = 24000,
        format: str = "pcm",
        app_id: str | None = None,
        access_key: str | None = None,
        resource_id: str | None = None,
        enable_subtitle: bool = True,
    ) -> None:
        self._api_key = api_key
        self._app_id = app_id
        self._access_key = access_key
        self._resource_id = resource_id or DEFAULT_RESOURCE_ID
        self._voice = voice
        self._sample_rate = sample_rate
        self._format = format
        self._enable_subtitle = enable_subtitle

        self._session_id = uuid.uuid4().hex
        self._ws = None
        self._queue: asyncio.Queue[StreamingTTSEvent] = asyncio.Queue()
        self._connected = False
        self._task_started = False
        self._loop_dead = False  # 服务端收尾后接收循环已退出（区别于用户 close）
        self._receive_task: asyncio.Task | None = None
        self._done_emitted = False
        self._timeline_end_ms = 0
        self._characters = 0
        self._current_sentence_text = ""

    # ── 公开 API ──

    async def connect(self) -> None:
        """建立 WebSocket 连接，握手并等待 SESSION_STARTED。"""
        if self._connected:
            return

        try:
            self._ws = await websockets.connect(
                BIDIRECTIONAL_WS_URL,
                additional_headers=self._build_auth_headers(),
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
        except Exception as exc:
            raise RuntimeError(f"火山 TTS 连接失败: {exc}") from exc

        self._connected = True
        self._receive_task = asyncio.ensure_future(self._receive_loop())

        try:
            await self._ws.send(create_start_connection_frame())
            await self._ws.send(
                create_start_session_frame(self._session_id, self._build_start_session_meta())
            )
        except Exception as exc:
            await self.close()
            raise RuntimeError(f"火山 TTS 会话握手失败: {exc}") from exc

        started = await self._wait_for_session_started(timeout=10)
        if not started:
            await self.close()
            raise RuntimeError("火山 TTS 会话启动超时或失败")

    async def send_text(self, text: str) -> None:
        """发送待合成文本片段。可多次调用。"""
        if not self._connected:
            raise RuntimeError("火山流式 TTS 会话尚未就绪")
        if not text:
            return
        await self._ws.send(create_task_request_frame(text, self._session_id))

    async def finish(self) -> None:
        """通知服务端文本发送完毕。"""
        if not self._connected:
            return
        try:
            await self._ws.send(create_finish_session_frame(self._session_id))
        except Exception:
            logger.exception("火山 TTS finish_session 发送失败")

    def try_receive(self) -> StreamingTTSEvent | None:
        """非阻塞获取下一个事件。没有事件时返回 None。"""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def receive(self, timeout: float | None = None) -> StreamingTTSEvent | None:
        """阻塞获取下一个事件。无更多事件时返回 None。"""
        if self._queue.empty() and (not self._connected or self._loop_dead):
            return None
        try:
            if timeout is None:
                return await self._queue.get()
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except (asyncio.QueueEmpty, asyncio.TimeoutError):
            return None

    async def close(self) -> None:
        """关闭 WebSocket 连接。"""
        self._connected = False
        self._task_started = False
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    # ── 内部实现 ──

    def _build_auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"X-Api-Resource-Id": self._resource_id}
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        elif self._app_id and self._access_key:
            headers["X-Api-App-Key"] = self._app_id
            headers["X-Api-Access-Key"] = self._access_key
        return headers

    def _build_start_session_meta(self) -> dict:
        return {
            "event": Event.START_SESSION,
            "req_params": {
                "speaker": self._voice,
                "audio_params": {
                    "format": self._format,
                    "sample_rate": self._sample_rate,
                    "enable_subtitle": self._enable_subtitle,
                },
            },
        }

    async def _wait_for_session_started(self, timeout: float = 10.0) -> bool:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if event.type == "task_started":
                self._task_started = True
                return True
            if event.type == "error":
                logger.error("火山 TTS 会话启动失败: %s", event.data)
                return False
        return False

    async def _receive_loop(self) -> None:
        try:
            while self._ws is not None:
                try:
                    message = await self._ws.recv()
                except websockets.ConnectionClosed:
                    break
                if not isinstance(message, (bytes, bytearray)):
                    continue
                self._handle_parsed_frame(parse_frame(bytes(message)))
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("火山 TTS 接收循环异常")
            self._queue.put_nowait(
                StreamingTTSEvent(type="error", data="火山 TTS 连接异常中断")
            )
        finally:
            # 不翻转 _connected：用户会话仍视为活跃，只有 close() 才结束会话。
            # 服务端收尾（FINISHED/FAILED/断连）通过 done/error 事件与 _loop_dead 呈现。
            self._task_started = False
            self._emit_done()
            self._loop_dead = True

    def _handle_parsed_frame(self, parsed: dict) -> None:
        event = parsed["event"]

        # 协议级错误帧
        if parsed.get("error_message"):
            logger.error("火山 TTS 协议错误 %s: %s", event, parsed["error_message"])
            self._queue.put_nowait(
                StreamingTTSEvent(type="error", data=parsed["error_message"])
            )
            self._task_started = False
            self._emit_done()
            return

        if event == Event.CONNECTION_STARTED:
            return

        if event == Event.CONNECTION_FAILED:
            detail = _decode_json_payload(parsed["payload"]).get("message", "")
            self._queue.put_nowait(
                StreamingTTSEvent(type="error", data=detail or "火山 TTS 连接被拒绝")
            )
            self._emit_done()
            return

        if event == Event.SESSION_STARTED:
            self._queue.put_nowait(StreamingTTSEvent(type="task_started"))
            return

        if event == Event.TTS_RESPONSE:
            self._queue.put_nowait(
                StreamingTTSEvent(type="audio_chunk", data=parsed["payload"])
            )
            return

        if event == Event.TTS_SENTENCE_START:
            payload = _decode_json_payload(parsed["payload"])
            self._current_sentence_text = payload.get("text", "")
            self._queue.put_nowait(
                StreamingTTSEvent(type="sentence_begin", data=self._current_sentence_text)
            )
            return

        if event == Event.TTS_SENTENCE_END:
            payload = _decode_json_payload(parsed["payload"])
            self._current_sentence_text = payload.get("text", self._current_sentence_text)
            words = payload.get("words") or []
            if words:
                # 1.0 模型（enable_timestamp）：字级时间戳内嵌在 SentenceEnd
                self._emit_word_timestamps(
                    raw_words=words,
                    sentence_index=payload.get("index", 0),
                    original_text=payload.get("text", self._current_sentence_text),
                )
            return

        if event == Event.TTS_SUBTITLE:
            payload = _decode_json_payload(parsed["payload"])
            raw_words = payload.get("words") or []
            if raw_words:
                # 2.0 模型（enable_subtitle）：独立字幕事件，words/text 在顶层
                # （与 SentenceEnd 同构，线上实测无 sentence 嵌套），秒级时间戳
                self._emit_word_timestamps(
                    raw_words=raw_words,
                    sentence_index=payload.get("index", 0),
                    original_text=payload.get("text") or self._current_sentence_text,
                )
            return

        if event == Event.SESSION_FINISHED:
            self._task_started = False
            self._emit_done()
            return

        if event == Event.SESSION_FAILED:
            payload = _decode_json_payload(parsed["payload"])
            detail = (
                payload.get("message")
                or (payload.get("resp_params") or {}).get("message")
                or json.dumps(payload, ensure_ascii=False)
                or "unknown"
            )
            logger.error("火山 TTS 会话失败: %s", detail)
            self._queue.put_nowait(StreamingTTSEvent(type="error", data=detail))
            self._task_started = False
            self._emit_done()
            return

    def _emit_word_timestamps(
        self, raw_words: list[dict], sentence_index: int, original_text: str
    ) -> None:
        """把火山秒级字时间戳转换为累计毫秒时间轴事件。"""
        converted: list[dict] = []
        for item in raw_words:
            text = item.get("word") or item.get("text") or ""
            begin = round(float(item.get("startTime") or item.get("begin_time") or 0) * 1000)
            end_raw = item.get("endTime") or item.get("end_time")
            end = round(float(end_raw) * 1000) if end_raw is not None else begin
            converted.append({"text": text, "begin_time": begin, "end_time": end})

        normalized = self._normalize_word_timestamps(converted)
        self._characters += sum(len(w["text"]) for w in converted)
        self._queue.put_nowait(
            StreamingTTSEvent(
                type="word_timestamps",
                data={
                    "words": normalized,
                    "sentence_index": sentence_index,
                    "original_text": original_text,
                    "characters": self._characters,
                },
            )
        )

    def _normalize_word_timestamps(self, words: list[dict]) -> list[dict]:
        """把可能按句重置的时间戳转换为整段回答的累计时间轴。"""
        if not words:
            return []
        starts = [int(item.get("begin_time", 0) or 0) for item in words]
        ends = [int(item.get("end_time", 0) or 0) for item in words]
        raw_start = min(starts, default=0)
        raw_end = max(ends, default=raw_start)

        # 后续句从 0 附近重新计时时追加偏移；服务端已返回累计时间则保留原值。
        offset = (
            self._timeline_end_ms
            if self._timeline_end_ms and raw_start < self._timeline_end_ms - 50
            else 0
        )
        normalized: list[dict] = []
        for item in words:
            word = dict(item)
            word["begin_time"] = int(word.get("begin_time", 0) or 0) + offset
            word["end_time"] = (
                int(word.get("end_time", word["begin_time"]) or word["begin_time"]) + offset
            )
            normalized.append(word)
        self._timeline_end_ms = max(self._timeline_end_ms, raw_end + offset)
        return normalized

    def _emit_done(self) -> None:
        if self._done_emitted:
            return
        self._done_emitted = True
        self._queue.put_nowait(StreamingTTSEvent(type="done"))


class VolcengineStreamingTTSService:
    """火山流式 TTS 服务工厂，为每次对话创建独立的 VolcengineStreamingTTSSession。"""

    def __init__(
        self,
        api_key: str | None = None,
        voice: str = DEFAULT_VOICE,
        sample_rate: int = 24000,
        format: str = "pcm",
        app_id: str | None = None,
        access_key: str | None = None,
        resource_id: str | None = None,
        enable_subtitle: bool = True,
    ) -> None:
        self._api_key = api_key
        self._app_id = app_id
        self._access_key = access_key
        self._resource_id = resource_id or DEFAULT_RESOURCE_ID
        self._voice = voice
        self._sample_rate = sample_rate
        self._format = format
        self._enable_subtitle = enable_subtitle

    def create_session(self) -> VolcengineStreamingTTSSession:
        return VolcengineStreamingTTSSession(
            api_key=self._api_key,
            voice=self._voice,
            sample_rate=self._sample_rate,
            format=self._format,
            app_id=self._app_id,
            access_key=self._access_key,
            resource_id=self._resource_id,
            enable_subtitle=self._enable_subtitle,
        )

    async def synthesize_stream(self, text: str):
        """便捷方法：对一段文本进行流式合成，返回事件迭代器。"""
        session = self.create_session()
        try:
            await session.connect()
            await session.send_text(text)
            await session.finish()

            while True:
                event = await session.receive()
                if event is None or event.type in ("done", "error"):
                    if event and event.type == "error":
                        yield event
                    break
                if event.type != "task_started":
                    yield event
        finally:
            await session.close()


__all__ = [
    "BIDIRECTIONAL_WS_URL",
    "DEFAULT_RESOURCE_ID",
    "DEFAULT_VOICE",
    "Event",
    "VolcengineStreamingTTSService",
    "VolcengineStreamingTTSSession",
    "VolcengineTTSService",
    "create_finish_connection_frame",
    "create_finish_session_frame",
    "create_start_connection_frame",
    "create_start_session_frame",
    "create_task_request_frame",
    "parse_frame",
]
