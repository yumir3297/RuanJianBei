"""百炼 CosyVoice 流式 TTS 服务 —— 基于 WebSocket 协议。

相比 HTTP 模式的核心改进：
- WebSocket 长连接，避免每句话重复握手
- 文本分片发送，服务端自动分句，完整句子立即合成
- 返回字级别时间戳，可直接驱动数字人口型
- 音频逐块返回（PCM），首块延迟 < 200ms
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from dataclasses import dataclass

import websockets

logger = logging.getLogger(__name__)

# WS URL: 旧版通用域名仍然可用
STREAMING_WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"


@dataclass(slots=True)
class StreamingTTSEvent:
    """流式 TTS 返回的事件"""
    type: str  # "audio_chunk" | "word_timestamps" | "sentence_begin" | "done" | "error"
    data: bytes | list[dict] | dict | str | None = None


class StreamingTTSSession:
    """单个流式 TTS 会话，管理一次对话中的 WebSocket 连接。

    用法：
        session = StreamingTTSSession(api_key, model, voice)
        await session.connect()
        await session.send_text("你好，")
        await session.send_text("欢迎来到灵山。")
        await session.finish()
        # 通过 try_receive() 获取音频块和字时间戳
        session.close()
    """

    def __init__(
        self,
        api_key: str,
        model: str = "cosyvoice-v3-flash",
        voice: str = "longwan_v3",
        sample_rate: int = 24000,
        format: str = "pcm",
        enable_word_timestamp: bool = True,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._sample_rate = sample_rate
        self._format = format
        self._enable_word_timestamp = enable_word_timestamp
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._task_id = uuid.uuid4().hex
        self._queue: asyncio.Queue[StreamingTTSEvent] = asyncio.Queue()
        self._connected = False
        self._task_started = False
        self._receive_task: asyncio.Task | None = None
        self._done_emitted = False
        self._timeline_end_ms = 0

    # ── 公开 API ──

    async def connect(self) -> None:
        """建立 WebSocket 连接并发送 run-task。"""
        if self._connected:
            return

        headers = {"Authorization": f"Bearer {self._api_key}"}
        self._ws = await websockets.connect(
            STREAMING_WS_URL,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        )
        self._connected = True

        # 启动接收循环
        self._receive_task = asyncio.ensure_future(self._receive_loop())

        # 发送 run-task
        run_task_msg = {
            "header": {
                "action": "run-task",
                "task_id": self._task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "tts",
                "function": "SpeechSynthesizer",
                "model": self._model,
                "input": {},
                "parameters": {
                    "text_type": "PlainText",
                    "voice": self._voice,
                    "format": self._format,
                    "sample_rate": self._sample_rate,
                    "word_timestamp_enabled": self._enable_word_timestamp,
                },
            },
        }
        await self._ws.send(json.dumps(run_task_msg))

        # 等待 task-started
        started = await self._wait_for_task_started(timeout=10)
        if not started:
            await self.close()
            raise RuntimeError("流式 TTS 任务启动超时或失败")

    async def send_text(self, text: str) -> None:
        """发送待合成文本片段。可多次调用。"""
        if not self._connected or not self._task_started:
            raise RuntimeError("流式 TTS 会话尚未就绪")
        if not text:
            return
        msg = {
            "header": {
                "action": "continue-task",
                "task_id": self._task_id,
                "streaming": "duplex",
            },
            "payload": {
                "input": {
                    "text": text,
                },
            },
        }
        await self._ws.send(json.dumps(msg))

    async def finish(self) -> None:
        """通知服务端文本发送完毕。"""
        if not self._connected or not self._task_started:
            return
        msg = {
            "header": {
                "action": "finish-task",
                "task_id": self._task_id,
                "streaming": "duplex",
            },
            "payload": {"input": {}},
        }
        await self._ws.send(json.dumps(msg))

    def try_receive(self) -> StreamingTTSEvent | None:
        """非阻塞获取下一个事件。没有事件时返回 None。"""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def receive(self, timeout: float | None = None) -> StreamingTTSEvent | None:
        """阻塞获取下一个事件。连接关闭且队列空时返回 None。"""
        if not self._connected and self._queue.empty():
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
        # 排空队列，防止内存泄漏
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    # ── 内部实现 ──

    async def _wait_for_task_started(self, timeout: float = 10.0) -> bool:
        """等待 task-started 事件。"""
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
                logger.error("TTS task failed: %s", event.data)
                return False
        return False

    async def _receive_loop(self) -> None:
        """持续接收 WebSocket 消息并解析为事件。"""
        try:
            while self._ws:
                try:
                    message = await self._ws.recv()
                except websockets.ConnectionClosed:
                    break

                if isinstance(message, bytes):
                    # 二进制帧 = PCM 音频数据
                    self._queue.put_nowait(
                        StreamingTTSEvent(type="audio_chunk", data=message)
                    )
                elif isinstance(message, str):
                    try:
                        msg = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    self._handle_json_message(msg)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("TTS receive loop error")
            self._queue.put_nowait(StreamingTTSEvent(type="error", data="流式 TTS 连接异常中断"))
        finally:
            self._connected = False
            self._task_started = False
            self._emit_done()

    def _handle_json_message(self, msg: dict) -> None:
        """处理 JSON 消息。"""
        header = msg.get("header", {})
        event_type = header.get("event", "")
        payload = msg.get("payload", {})

        if event_type == "task-started":
            self._queue.put_nowait(StreamingTTSEvent(type="task_started"))

        elif event_type == "task-finished":
            # 服务端允许复用 WebSocket，因此任务结束后连接不一定关闭。
            # 必须在协议级结束事件到达时主动结束当前任务的消费循环。
            self._task_started = False
            self._emit_done()

        elif event_type == "task-failed":
            error_code = header.get("error_code", "unknown")
            error_msg = header.get("error_message", "unknown error")
            logger.error("TTS task failed: code=%s message=%s", error_code, error_msg)
            self._queue.put_nowait(
                StreamingTTSEvent(type="error", data=f"{error_code}: {error_msg}")
            )

        elif event_type == "result-generated":
            output = payload.get("output", {})
            sub_type = output.get("type", "")

            if sub_type == "sentence-begin":
                original_text = output.get("original_text", "")
                self._queue.put_nowait(
                    StreamingTTSEvent(
                        type="sentence_begin", data=original_text
                    )
                )

            elif sub_type == "sentence-end":
                sentence = output.get("sentence", {})
                words = sentence.get("words", [])
                if words:
                    normalized_words = self._normalize_word_timestamps(words)
                    self._queue.put_nowait(
                        StreamingTTSEvent(
                            type="word_timestamps",
                            data={
                                "words": normalized_words,
                                "sentence_index": sentence.get("index", 0),
                                "original_text": output.get("original_text", ""),
                                "characters": (payload.get("usage") or {}).get("characters", 0),
                            },
                        )
                    )

            # sentence-synthesis 不需要单独处理，音频通过 binary 帧传输

    def _emit_done(self) -> None:
        if self._done_emitted:
            return
        self._done_emitted = True
        self._queue.put_nowait(StreamingTTSEvent(type="done"))

    def _normalize_word_timestamps(self, words: list[dict]) -> list[dict]:
        """把可能按句重置的时间戳转换为整段回答的累计时间轴。"""
        if not words:
            return []
        starts = [int(item.get("begin_time", 0) or 0) for item in words]
        ends = [int(item.get("end_time", 0) or 0) for item in words]
        raw_start = min(starts, default=0)
        raw_end = max(ends, default=raw_start)

        # 后续句从 0 附近重新计时时追加偏移；如果服务端已返回累计时间则保留原值。
        offset = self._timeline_end_ms if self._timeline_end_ms and raw_start < self._timeline_end_ms - 50 else 0
        normalized: list[dict] = []
        for item in words:
            word = dict(item)
            word["begin_time"] = int(word.get("begin_time", 0) or 0) + offset
            word["end_time"] = int(word.get("end_time", word["begin_time"]) or word["begin_time"]) + offset
            normalized.append(word)
        self._timeline_end_ms = max(self._timeline_end_ms, raw_end + offset)
        return normalized


class StreamingTTSService:
    """流式 TTS 服务工厂，为每次对话创建独立的 StreamingTTSSession。"""

    def __init__(
        self,
        api_key: str,
        model: str = "cosyvoice-v3-flash",
        voice: str = "longwan_v3",
        sample_rate: int = 24000,
        enable_word_timestamp: bool = True,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._sample_rate = sample_rate
        self._enable_word_timestamp = enable_word_timestamp

    def create_session(self) -> StreamingTTSSession:
        """创建一个新的流式 TTS 会话。"""
        return StreamingTTSSession(
            api_key=self._api_key,
            model=self._model,
            voice=self._voice,
            sample_rate=self._sample_rate,
            enable_word_timestamp=self._enable_word_timestamp,
        )

    async def synthesize_stream(self, text: str):
        """便捷方法：对一段文本进行流式合成，返回事件迭代器。

        适用于不需要交互的场景（如 FAQ 回答）。
        """
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
                if event.type not in ("task_started",):
                    yield event
        finally:
            await session.close()
