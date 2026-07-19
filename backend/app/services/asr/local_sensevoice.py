from __future__ import annotations

import asyncio
import io
import json
import threading
import time
import wave
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.asr.base import ASRResult, BaseASRService


_EMOTION_MAP = {
    "HAPPY": "positive",
    "SAD": "anxious",
    "ANGRY": "dissatisfied",
    "NEUTRAL": "neutral",
}


class LocalSenseVoiceASRService(BaseASRService):
    """Local SenseVoice ONNX inference: ASR, speech emotion and audio event in one pass."""

    _recognizers: dict[tuple[str, str, int, str], Any] = {}
    _recognizer_lock = threading.Lock()
    _inference_lock = threading.Lock()

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def transcribe(self, content: bytes | str) -> ASRResult:
        started_at = time.perf_counter()
        if isinstance(content, str) or not content:
            return self._unavailable("本地 SenseVoice 需要 WAV 音频字节。", started_at)
        try:
            result = await asyncio.to_thread(self._transcribe_wav, content)
        except Exception as exc:
            return self._unavailable(
                f"本地 SenseVoice 识别失败：{str(exc)[:160]}",
                started_at,
            )

        text = str(result.get("text", "")).strip()
        raw_emotion = self._strip_tag(result.get("emotion", "NEUTRAL"))
        emotion = _EMOTION_MAP.get(raw_emotion, "neutral")
        audio_event = self._strip_tag(result.get("event", "Speech")).lower() or "speech"
        return ASRResult(
            text=text,
            confidence=0.86 if text else 0.0,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            provider="local_sensevoice",
            confidence_source="heuristic" if text else "unavailable",
            error_message="" if text else "SenseVoice 未识别到有效语音。",
            emotion=emotion,
            emotion_confidence=0.72 if raw_emotion != "NEUTRAL" else 0.62,
            emotion_source="sensevoice",
            audio_event=audio_event,
        )

    def _transcribe_wav(self, content: bytes) -> dict[str, Any]:
        samples, sample_rate = self._decode_wav(content)
        recognizer = self._get_recognizer()
        with self._inference_lock:
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples)
            recognizer.decode_stream(stream)
            payload = stream.result
        if isinstance(payload, str):
            parsed = json.loads(payload)
            return self._unwrap_result(parsed)
        if isinstance(payload, dict):
            return self._unwrap_result(payload)
        # sherpa_onnx >= 1.10 returns OfflineRecognitionResult objects with
        # attribute access (.text, .emotion, .event, .lang, .tokens etc.)
        if hasattr(payload, "text"):
            return {
                "text": str(getattr(payload, "text", "") or ""),
                "emotion": str(getattr(payload, "emotion", "NEUTRAL") or "NEUTRAL"),
                "event": str(getattr(payload, "event", "Speech") or "Speech"),
                "lang": str(getattr(payload, "lang", "") or ""),
            }
        return {"text": str(payload or "")}

    @staticmethod
    def _unwrap_result(parsed: Any) -> dict[str, Any]:
        """Unwrap the nested JSON returned by some sherpa-onnx builds."""
        if not isinstance(parsed, dict):
            return {"text": str(parsed)}

        nested = parsed.get("text")
        if isinstance(nested, str) and nested.lstrip().startswith("{"):
            try:
                nested_parsed = json.loads(nested)
            except json.JSONDecodeError:
                return parsed
            if isinstance(nested_parsed, dict) and "text" in nested_parsed:
                return nested_parsed
        return parsed

    def _get_recognizer(self):
        model_dir = Path(self.settings.asr_local_model_dir).expanduser().resolve()
        model_path = model_dir / "model.int8.onnx"
        tokens_path = model_dir / "tokens.txt"
        if not model_path.is_file() or not tokens_path.is_file():
            raise FileNotFoundError(f"SenseVoice 模型不完整：{model_dir}")
        key = (
            str(model_path),
            str(tokens_path),
            self.settings.asr_local_num_threads,
            self.settings.asr_local_language,
        )
        with self._recognizer_lock:
            recognizer = self._recognizers.get(key)
            if recognizer is None:
                import sherpa_onnx

                recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                    model=str(model_path),
                    tokens=str(tokens_path),
                    num_threads=self.settings.asr_local_num_threads,
                    language=self.settings.asr_local_language,
                    use_itn=True,
                )
                self._recognizers[key] = recognizer
            return recognizer

    @staticmethod
    def _decode_wav(content: bytes):
        import numpy as np

        if not content.startswith(b"RIFF"):
            raise ValueError("当前本地识别器只接收 PCM WAV；WebM 需在前端转为 WAV 后上传。")
        with wave.open(io.BytesIO(content), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())

        if sample_width == 1:
            samples = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sample_width == 2:
            samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
        elif sample_width == 4:
            samples = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"不支持 {sample_width * 8} bit WAV。")

        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        target_rate = 16000
        if sample_rate != target_rate and samples.size:
            target_length = max(int(samples.size * target_rate / sample_rate), 1)
            old_positions = np.linspace(0.0, 1.0, num=samples.size, endpoint=False)
            new_positions = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
            samples = np.interp(new_positions, old_positions, samples).astype(np.float32)
            sample_rate = target_rate
        return samples.astype(np.float32, copy=False), sample_rate

    @staticmethod
    def _strip_tag(value: Any) -> str:
        return str(value or "").replace("<|", "").replace("|>", "").strip().upper()

    @staticmethod
    def _unavailable(message: str, started_at: float) -> ASRResult:
        return ASRResult(
            text="",
            confidence=0.0,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            provider="local_sensevoice_unavailable",
            confidence_source="unavailable",
            error_message=message,
            emotion="neutral",
            emotion_confidence=0.0,
            emotion_source="unavailable",
            audio_event="unknown",
        )
