from __future__ import annotations

import asyncio
import json
import math
import tempfile
from pathlib import Path
from asyncio.subprocess import DEVNULL, PIPE


class AudioProbeError(Exception):
    """The media could not be inspected as valid audio."""


class AudioProbeUnavailable(Exception):
    """The configured ffprobe executable could not be started."""


async def probe_audio_duration(content: bytes, *, executable: str, timeout_seconds: float) -> float:
    input_format = _input_format(content)
    if input_format is None:
        raise AudioProbeError("unsupported compressed audio format")
    create_file = asyncio.create_task(asyncio.to_thread(_write_probe_media, content))
    try:
        media_path = await asyncio.shield(create_file)
    except asyncio.CancelledError:
        media_path = await create_file
        await asyncio.to_thread(media_path.unlink, missing_ok=True)
        raise
    except OSError as exc:
        raise AudioProbeUnavailable from exc

    try:
        try:
            process = await asyncio.create_subprocess_exec(
                executable,
                "-v", "error",
                "-protocol_whitelist", "file",
                "-f", input_format,
                "-probesize", "5000000",
                "-analyzeduration", "3000000",
                "-max_alloc", "67108864",
                "-show_entries", "format=duration:stream=codec_type,duration",
                "-of", "json",
                str(media_path),
                stdin=DEVNULL,
                stdout=PIPE,
                stderr=DEVNULL,
            )
        except OSError as exc:
            raise AudioProbeUnavailable from exc

        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise AudioProbeError("audio probe timed out") from exc
        except BaseException:
            process.kill()
            await process.wait()
            raise

        if process.returncode != 0:
            raise AudioProbeError("ffprobe rejected media")
        try:
            payload = json.loads(stdout)
            streams = payload.get("streams", [])
            if not any(stream.get("codec_type") == "audio" for stream in streams):
                raise AudioProbeError("media has no audio stream")
            duration_value = next(
                (stream.get("duration") for stream in streams if stream.get("codec_type") == "audio" and stream.get("duration") not in (None, "N/A")),
                payload.get("format", {}).get("duration"),
            )
            duration = float(duration_value)
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AudioProbeError("ffprobe returned invalid duration") from exc
        if not math.isfinite(duration) or duration <= 0:
            raise AudioProbeError("ffprobe returned invalid duration")
        return duration
    finally:
        await asyncio.to_thread(media_path.unlink, missing_ok=True)


def _write_probe_media(content: bytes) -> Path:
    media_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="asr-probe-", suffix=".media", delete=False) as media_file:
            media_path = Path(media_file.name)
            media_file.write(content)
        return media_path
    except OSError:
        if media_path is not None:
            media_path.unlink(missing_ok=True)
        raise


def _input_format(content: bytes) -> str | None:
    if content.startswith(b"\x1a\x45\xdf\xa3"):
        return "matroska"
    if content.startswith(b"ID3") or (
        len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0
    ):
        return "mp3"
    if len(content) >= 8 and content[4:8] == b"ftyp":
        return "mov"
    if content.startswith(b"OggS"):
        return "ogg"
    if content.startswith(b"fLaC"):
        return "flac"
    if content.startswith(b"ADIF") or (len(content) >= 2 and content[0] == 0xFF and content[1] & 0xF6 == 0xF0):
        return "aac"
    return None
