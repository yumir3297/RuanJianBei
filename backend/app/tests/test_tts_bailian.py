import asyncio
import base64

from app.services.tts.bailian import BailianTTSService


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, content: bytes = b"audio-bytes"):
        self.content = content
        self.requested_url = ""

    async def get(self, url: str):
        self.requested_url = url
        return FakeResponse(self.content)


def test_bailian_resolves_inline_audio_shapes() -> None:
    service = BailianTTSService(api_key="test")
    client = FakeClient()

    plain = asyncio.run(
        service._resolve_audio_data({"output": {"audio": "YWJj"}}, client)
    )
    nested = asyncio.run(
        service._resolve_audio_data(
            {"output": {"audio": {"data": "ZGVm"}}},
            client,
        )
    )
    data_uri = asyncio.run(
        service._resolve_audio_data(
            {"output": {"audio": "data:audio/mp3;base64,Z2hp"}},
            client,
        )
    )

    assert plain == "YWJj"
    assert nested == "ZGVm"
    assert data_uri == "Z2hp"


def test_bailian_downloads_audio_url() -> None:
    service = BailianTTSService(api_key="test")
    client = FakeClient(content=b"downloaded-audio")

    encoded = asyncio.run(
        service._resolve_audio_data(
            {"output": {"audio": {"url": "https://example.test/audio.mp3"}}},
            client,
        )
    )

    assert client.requested_url == "https://example.test/audio.mp3"
    assert base64.b64decode(encoded) == b"downloaded-audio"


def test_bailian_extracts_duration_when_available() -> None:
    assert BailianTTSService._extract_duration_ms(
        {"output": {"duration_ms": 1234}}
    ) == 1234
    assert BailianTTSService._extract_duration_ms(
        {"output": {"duration": 1.5}}
    ) == 1500


def test_bailian_uses_current_speech_synthesizer_endpoint() -> None:
    service = BailianTTSService(api_key="test")

    assert service.base_url.endswith("/services/audio/tts/SpeechSynthesizer")
    assert service.model == "cosyvoice-v3-flash"
    assert service.voice == "longwan_v3"
