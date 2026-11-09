import asyncio
from pathlib import Path

from app.services.audio_duration import AudioProbeError, AudioProbeUnavailable, probe_audio_duration


class _Process:
    def __init__(self, stdout=b'{"format":{"duration":"2.5"},"streams":[{"codec_type":"audio"}]}', returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.killed = False

    async def communicate(self, input=None):
        assert input is None
        return self.stdout, b""

    def kill(self):
        self.killed = True

    async def wait(self):
        return self.returncode


def test_probe_parses_duration_from_audio_stream(monkeypatch):
    process = _Process()
    paths = []

    async def spawn(*args, **kwargs):
        media_path = Path(args[-1])
        paths.append(media_path)
        assert media_path.read_bytes() == b"ID3encoded-audio"
        assert kwargs["stdin"] is not None
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
    assert asyncio.run(probe_audio_duration(b"ID3encoded-audio", executable="ffprobe", timeout_seconds=1)) == 2.5
    assert not paths[0].exists()


def test_probe_rejects_missing_or_invalid_audio_stream(monkeypatch):
    process = _Process(stdout=b'{"format":{"duration":"2.5"},"streams":[]}')

    async def spawn(*args, **kwargs):
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
    try:
        asyncio.run(probe_audio_duration(b"ID3encoded-audio", executable="ffprobe", timeout_seconds=1))
    except AudioProbeError:
        return
    raise AssertionError("probe without audio stream should fail")


def test_probe_rejects_malformed_json_output(monkeypatch):
    process = _Process(stdout=b"not-json")

    async def spawn(*args, **kwargs):
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
    try:
        asyncio.run(probe_audio_duration(b"ID3encoded-audio", executable="ffprobe", timeout_seconds=1))
    except AudioProbeError:
        return
    raise AssertionError("invalid probe output should fail")


def test_probe_does_not_run_on_unknown_container(monkeypatch):
    async def unexpected(*args, **kwargs):
        raise AssertionError("unknown container must not reach ffprobe")

    monkeypatch.setattr("asyncio.create_subprocess_exec", unexpected)
    try:
        asyncio.run(probe_audio_duration(b"#EXTM3U\nfile:///etc/passwd", executable="ffprobe", timeout_seconds=1))
    except AudioProbeError:
        return
    raise AssertionError("unknown container should be rejected")


def test_probe_reports_missing_executable(monkeypatch):
    paths = []

    async def spawn(*args, **kwargs):
        paths.append(Path(args[-1]))
        raise FileNotFoundError

    monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
    try:
        asyncio.run(probe_audio_duration(b"ID3encoded-audio", executable="ffprobe", timeout_seconds=1))
    except AudioProbeUnavailable:
        assert not paths[0].exists()
        return
    raise AssertionError("missing ffprobe should be explicit")


def test_probe_kills_timed_out_process(monkeypatch):
    process = _Process()
    paths = []

    async def stalled(input=None):
        await asyncio.sleep(1)

    process.communicate = stalled

    async def spawn(*args, **kwargs):
        paths.append(Path(args[-1]))
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
    try:
        asyncio.run(probe_audio_duration(b"ID3encoded-audio", executable="ffprobe", timeout_seconds=0.01))
    except AudioProbeError:
        assert process.killed
        assert not paths[0].exists()
        return
    raise AssertionError("probe timeout should fail")
