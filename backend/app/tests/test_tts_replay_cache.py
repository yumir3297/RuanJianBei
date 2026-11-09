from app.services.tts.base import TTSAudio
from app.services.tts.replay_cache import ReplayAudioCache


def test_replay_audio_cache_expires_entries_after_ttl():
    now = [10.0]
    cache = ReplayAudioCache(ttl_seconds=5, clock=lambda: now[0])
    audio = TTSAudio("encoded", 1000, "test")
    cache.put("key", audio)

    now[0] = 14.9
    assert cache.get("key") is audio
    now[0] = 15.0
    assert cache.get("key") is None


def test_replay_audio_cache_evicts_least_recently_used_entries_at_capacity():
    cache = ReplayAudioCache(max_entries=2, max_bytes=100, ttl_seconds=60, clock=lambda: 1.0)
    first = TTSAudio("a" * 10, 100, "test")
    second = TTSAudio("b" * 10, 100, "test")
    third = TTSAudio("c" * 10, 100, "test")
    cache.put("first", first)
    cache.put("second", second)
    assert cache.get("first") is first
    cache.put("third", third)

    assert cache.get("first") is first
    assert cache.get("second") is None
    assert cache.get("third") is third


def test_replay_audio_cache_enforces_byte_limit_and_skips_empty_audio():
    cache = ReplayAudioCache(max_entries=5, max_bytes=10, ttl_seconds=60, clock=lambda: 1.0)
    cache.put("too-large", TTSAudio("x" * 11, 100, "test"))
    cache.put("empty", TTSAudio("", 100, "test"))

    assert cache.get("too-large") is None
    assert cache.get("empty") is None
    assert cache.size == 0


def test_replay_audio_cache_replacement_updates_total_bytes():
    cache = ReplayAudioCache(max_entries=5, max_bytes=10, ttl_seconds=60, clock=lambda: 1.0)
    cache.put("key", TTSAudio("12345", 100, "test"))
    cache.put("key", TTSAudio("12345678", 100, "test"))

    assert cache.size == 1
    assert cache.total_bytes == 8


def test_replay_audio_cache_evicts_old_entries_to_stay_under_byte_limit():
    cache = ReplayAudioCache(max_entries=5, max_bytes=15, ttl_seconds=60, clock=lambda: 1.0)
    cache.put("first", TTSAudio("a" * 10, 100, "test"))
    cache.put("second", TTSAudio("b" * 10, 100, "test"))

    assert cache.get("first") is None
    assert cache.get("second") is not None
    assert cache.total_bytes == 10
