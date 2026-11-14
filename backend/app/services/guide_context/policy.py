from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


SAFETY_PRIORITY = {"sos": 100, "verified_critical_warning": 80, "verified_zone_warning": 70}
WEATHER_EVIDENCE_MAX_AGE_SECONDS = 15 * 60


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def active_verified_alerts(weather: dict[str, Any] | None, now: datetime) -> list[dict[str, Any]]:
    """Only accept source-backed alerts with an explicit, current validity window."""
    if not weather or weather.get("source") != "和风天气 QWeather":
        return []
    fetched_at = _time(weather.get("fetched_at"))
    if fetched_at is None or not (0 <= (now - fetched_at).total_seconds() <= WEATHER_EVIDENCE_MAX_AGE_SECONDS):
        return []
    alert = weather.get("alert") or {}
    active = []
    for item in alert.get("items", []):
        if not item.get("id"):
            continue
        start = _time(item.get("effectiveTime"))
        end = _time(item.get("expireTime"))
        if start is None or end is None or not (start <= now < end):
            continue
        if item.get("status") in {"cancelled", "expired", "撤销", "解除"}:
            continue
        active.append(item)
    return active


def decide_narration(remaining_minutes: int | None, *, playback_busy: bool = False, proactive_enabled: bool = True) -> dict[str, Any]:
    if not proactive_enabled:
        action, reason = "none", "proactive_disabled"
    elif playback_busy:
        action, reason = "defer_narration", "playback_busy"
    elif remaining_minutes is not None and remaining_minutes <= 30:
        action, reason = "short_narration", "limited_time"
    else:
        action, reason = "full_narration", "standard_context"
    return {"action": action, "reason_codes": [reason]}


def evaluate_safety(weather: dict[str, Any] | None, now: datetime) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for item in active_verified_alerts(weather, now):
        severity = str(item.get("severity", "")).lower()
        if severity in {"extreme", "severe"}:
            events.append({
                "event_id": f"qweather:{item.get('id')}",
                "type": "verified_critical_warning",
                "priority": SAFETY_PRIORITY["verified_critical_warning"],
                "source": "和风天气 QWeather",
                "headline": str(item.get("headline") or item.get("eventType") or "气象预警"),
                "instruction": str(item.get("instruction") or "请留意景区现场公告，并按工作人员指引行动。"),
                "expires_at": item.get("expireTime"),
            })
    return events


def adapt_narration_to_weather(weather: dict[str, Any] | None, now: datetime) -> dict[str, Any] | None:
    """Return a non-safety narration hint only for fresh, source-backed precipitation."""
    if not weather or weather.get("source") != "和风天气 QWeather" or weather.get("status") != "available":
        return None
    fetched_at = _time(weather.get("fetched_at"))
    if fetched_at is None or not (0 <= (now - fetched_at).total_seconds() <= WEATHER_EVIDENCE_MAX_AGE_SECONDS):
        return None
    current = weather.get("weather")
    if not isinstance(current, dict):
        return None
    observed_at = _time(current.get("obsTime"))
    if observed_at is None or not (0 <= (now - observed_at).total_seconds() <= WEATHER_EVIDENCE_MAX_AGE_SECONDS):
        return None
    try:
        icon_code = int(current.get("iconCode"))
    except (TypeError, ValueError):
        return None
    if not (300 <= icon_code <= 499):
        return None
    return {
        "kind": "precipitation",
        "condition": str(current.get("description") or "降水")[:32],
        "source": weather["source"],
        "scope": "scenic_area",
        "observed_at": observed_at.isoformat(),
    }


def make_decision(payload: dict[str, Any], weather: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    demo = bool(payload.get("demo_scenario_id"))
    remaining = (payload.get("preferences") or {}).get("remaining_minutes")
    safety_events = evaluate_safety(weather, now)
    weather_adaptation = adapt_narration_to_weather(weather, now)
    decision = decide_narration(
        remaining,
        playback_busy=bool(payload.get("playback_busy")),
        proactive_enabled=bool((payload.get("preferences") or {}).get("proactive_enabled", True)),
    )
    if safety_events:
        decision = {"action": "none", "reason_codes": ["safety_priority"]}
    reason_labels = {
        "limited_time": "游客选择的剩余时间较短，优先提供简短讲解。",
        "standard_context": "当前没有触发限时或安全规则，使用常规讲解。",
        "playback_busy": "当前有内容正在播放，暂缓新的讲解。",
        "proactive_disabled": "游客已关闭主动服务。",
        "safety_priority": "存在有效的严重天气预警，安全提醒优先于普通讲解。",
    }
    reason_code = decision["reason_codes"][0]
    rule_ids = {
        "limited_time": "TIME_BUDGET_SHORT",
        "standard_context": "DEFAULT_NARRATION",
        "playback_busy": "PLAYBACK_DEFER",
        "proactive_disabled": "PROACTIVE_DISABLED",
        "safety_priority": "SAFETY_ALERT_PRIORITY",
    }
    evidence_refs = []
    fetched_at = _time(weather.get("fetched_at")) if weather else None
    weather_observed_at = _time((weather.get("weather") or {}).get("obsTime")) if weather else None
    weather_observation_current = bool(
        weather_observed_at is not None
        and 0 <= (now - weather_observed_at).total_seconds() <= WEATHER_EVIDENCE_MAX_AGE_SECONDS
    )
    weather_current = bool(
        weather and weather.get("source") and fetched_at
        and 0 <= (now - fetched_at).total_seconds() <= WEATHER_EVIDENCE_MAX_AGE_SECONDS
        and weather.get("status") == "available"
        and (weather_observation_current or active_verified_alerts(weather, now))
    )
    if weather_current:
        evidence_refs.append({
            "type": "weather_snapshot", "source": weather["source"],
            "observed_at": (weather_observed_at.isoformat() if weather_observation_current else weather.get("fetched_at")),
        })
    decision_rule_ids = [rule_ids[reason_code]]
    if weather_adaptation:
        decision_rule_ids.append("WEATHER_PRECIPITATION_NARRATION_ADAPTATION")
    suggestions = []
    if decision["action"] == "short_narration":
        suggestions.append({"suggestion_id": "review_itinerary_for_time", "action": "review_itinerary", "requires_confirmation": True})
    elif safety_events:
        suggestions.append({"suggestion_id": "follow_official_guidance", "action": "follow_site_staff", "requires_confirmation": False})
    expires_at = now + timedelta(minutes=5)
    if weather_current and fetched_at is not None:
        expires_at = min(expires_at, fetched_at + timedelta(seconds=WEATHER_EVIDENCE_MAX_AGE_SECONDS))
    if weather_current and weather_observation_current and weather_observed_at is not None:
        expires_at = min(expires_at, weather_observed_at + timedelta(seconds=WEATHER_EVIDENCE_MAX_AGE_SECONDS))
    for item in active_verified_alerts(weather, now):
        alert_expires = _time(item.get("expireTime"))
        if alert_expires is not None:
            expires_at = min(expires_at, alert_expires)
    return {
        "available": True,
        "snapshot_id": payload.get("snapshot_id") or f"ctx:{int(now.timestamp())}",
        "decision": decision,
        "generated_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "rule_ids": decision_rule_ids,
        "reasons": [reason_labels[reason_code]],
        "evidence_refs": evidence_refs,
        "weather_adaptation": weather_adaptation,
        "suggestions": suggestions,
        "data_mode": "demo" if demo else ("live" if weather_current else "partial"),
        "safety_events": safety_events,
        "evidence_status": {
            "weather": "available" if weather_observation_current else "unknown",
            "alerts": "verified" if active_verified_alerts(weather, now) else "none_verified",
            "location": "demo_only" if demo else "client_hint_unverified",
        },
    }
