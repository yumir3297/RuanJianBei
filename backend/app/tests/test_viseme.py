from app.services.avatar.viseme import _merge_similar_frames, build_viseme_timeline


def fake_pinyin(char: str, heteronym: bool = False, style=None):
    finals = {
        "山": [["an"]],
        "区": [["v"]],
    }
    normals = {
        "山": [["shan"]],
        "区": [["qu"]],
    }
    if style == 5:
        return finals.get(char, [["a"]])
    return normals.get(char, [[char]])


def test_build_viseme_timeline_includes_roundness_and_full_duration() -> None:
    timeline = build_viseme_timeline("山区", 1000, pinyin_fn=fake_pinyin)

    assert timeline
    assert timeline[0]["start"] == 0
    assert timeline[-1]["end"] == 1000
    assert all("form" in frame for frame in timeline)
    assert max(frame["form"] for frame in timeline) >= 0.78
    assert min(frame["value"] for frame in timeline) >= 0


def test_merge_similar_frames_uses_correct_weighted_average() -> None:
    frames = [
        {"start": 0, "end": 100, "value": 0.2, "form": 0.1},
        {"start": 100, "end": 300, "value": 0.24, "form": 0.12},
    ]

    merged = _merge_similar_frames(frames)

    assert len(merged) == 1
    assert merged[0]["start"] == 0
    assert merged[0]["end"] == 300
    assert merged[0]["value"] == 0.227
    assert merged[0]["form"] == 0.113
