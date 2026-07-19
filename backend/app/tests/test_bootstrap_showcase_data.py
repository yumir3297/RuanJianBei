from datetime import datetime, timezone

from app.db.bootstrap_showcase_data import (
    DAILY_COUNTS,
    SHOWCASE_FAQ_PREFIX,
    SHOWCASE_SESSION_PREFIX,
    build_showcase_dataset,
    summarize_showcase_dataset,
)


FIXED_NOW = datetime(2026, 7, 19, 18, 30, tzinfo=timezone.utc)


def test_showcase_dataset_is_deterministic_and_covers_thirty_days() -> None:
    first = build_showcase_dataset(FIXED_NOW)
    second = build_showcase_dataset(FIXED_NOW)

    assert first == second
    assert len(first.chats) == sum(DAILY_COUNTS) == 495
    assert len({record.created_at.date() for record in first.chats}) == 30
    assert max(record.created_at for record in first.chats) < FIXED_NOW
    assert len(first.visitors) == 40
    assert all(record.session_id.startswith(SHOWCASE_SESSION_PREFIX) for record in first.chats)
    assert all(record.session_id.startswith(SHOWCASE_SESSION_PREFIX) for record in first.visitors)


def test_showcase_dataset_exercises_real_admin_metrics() -> None:
    dataset = build_showcase_dataset(FIXED_NOW)
    summary = summarize_showcase_dataset(dataset)

    assert set(summary["hit_distribution"]) == {
        "faq_exact",
        "faq_fuzzy",
        "faq_semantic",
        "cache",
        "rag",
        "rag_insufficient",
    }
    assert set(summary["emotion_distribution"]) == {
        "positive",
        "neutral",
        "confused",
        "dissatisfied",
        "anxious",
        "urgent",
    }
    assert summary["input_modes"]["voice"] > 150
    assert summary["multimodal_emotion_count"] == summary["input_modes"]["voice"]
    assert summary["emotion_conflict_count"] > 0
    assert summary["average_latency_ms"] < 650
    assert summary["showcase_satisfaction_rate"] < 100
    assert summary["showcase_satisfaction_rate"] >= 80


def test_showcase_dataset_keeps_live_unknowns_out_of_evidence_answers() -> None:
    dataset = build_showcase_dataset(FIXED_NOW)
    insufficient = [record for record in dataset.chats if record.hit_level == "rag_insufficient"]

    assert insufficient
    assert all(record.sources == () for record in insufficient)
    assert all("不" in record.answer or "没有" in record.answer for record in insufficient)
    assert {record.status for record in dataset.blind_spots} == {"open", "resolved"}
    assert all(record.id.startswith(SHOWCASE_FAQ_PREFIX) for record in dataset.faqs)
    assert all(record.resolved_faq_id for record in dataset.blind_spots if record.status == "resolved")
