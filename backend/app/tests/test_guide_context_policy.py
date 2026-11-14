from datetime import datetime, timezone
import unittest

from app.services.guide_context.policy import decide_narration, evaluate_safety, make_decision


class GuideContextPolicyTest(unittest.TestCase):
    def test_time_budget_switches_to_short_at_thirty_minutes(self):
        self.assertEqual(decide_narration(30)["action"], "short_narration")
        self.assertEqual(decide_narration(31)["action"], "full_narration")
        self.assertEqual(decide_narration(20, proactive_enabled=False)["action"], "none")

    def test_only_current_source_backed_critical_alerts_create_events(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        payload = {"source": "和风天气 QWeather", "fetched_at": "2026-11-07T01:55:00Z", "alert": {"items": [{
            "id": "a1", "severity": "Severe", "effectiveTime": "2026-11-07T01:00:00Z",
            "expireTime": "2026-11-07T03:00:00Z", "headline": "雷电预警",
        }]}}
        self.assertEqual(len(evaluate_safety(payload, now)), 1)
        self.assertEqual(len(evaluate_safety(payload, now)), 1)
        expired = {**payload, "alert": {"items": [{**payload["alert"]["items"][0], "expireTime": "2026-11-07T01:30:00Z"}]}}
        self.assertEqual(evaluate_safety(expired, now), [])
        missing_expiry = {**payload, "alert": {"items": [{k: v for k, v in payload["alert"]["items"][0].items() if k != "expireTime"}]}}
        self.assertEqual(evaluate_safety(missing_expiry, now), [])

    def test_weather_and_rain_alone_do_not_trigger_safety_event(self):
        now = datetime(2026, 11, 7, tzinfo=timezone.utc)
        self.assertEqual(evaluate_safety({"source": "和风天气 QWeather", "weather": {"description": "小雨"}}, now), [])

    def test_missing_or_stale_fetch_time_cannot_trigger_an_event(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        payload = {"source": "和风天气 QWeather", "alert": {"items": [{
            "id": "a1", "severity": "Severe", "effectiveTime": "2026-11-07T01:00:00Z",
            "expireTime": "2026-11-07T03:00:00Z",
        }]}}
        self.assertEqual(evaluate_safety(payload, now), [])
        stale = {**payload, "fetched_at": "2026-11-07T01:00:00Z"}
        self.assertEqual(evaluate_safety(stale, now), [])

    def test_decision_exposes_rule_evidence_and_reviewable_suggestion(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        result = make_decision({"preferences": {"remaining_minutes": 20, "interests": ["family"]}}, None, now)
        self.assertEqual(result["rule_ids"], ["TIME_BUDGET_SHORT"])
        self.assertEqual(result["data_mode"], "partial")
        self.assertEqual(result["suggestions"][0]["action"], "review_itinerary")
        self.assertIn("剩余时间", result["reasons"][0])

    def test_fresh_rain_weather_adds_a_non_safety_narration_adaptation(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        weather = {
            "source": "和风天气 QWeather", "fetched_at": "2026-11-07T01:59:00Z", "status": "available",
            "weather": {"iconCode": "305", "description": "小雨", "obsTime": "2026-11-07T01:59:00Z"}, "alert": {"items": []},
        }
        result = make_decision({"preferences": {"remaining_minutes": 90}}, weather, now)
        self.assertEqual(result["decision"]["action"], "full_narration")
        self.assertEqual(result["weather_adaptation"]["condition"], "小雨")
        self.assertEqual(result["weather_adaptation"]["kind"], "precipitation")
        self.assertEqual(result["safety_events"], [])
        self.assertIn("WEATHER_PRECIPITATION_NARRATION_ADAPTATION", result["rule_ids"])

    def test_stale_rain_weather_does_not_create_a_narration_adaptation(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        weather = {
            "source": "和风天气 QWeather", "fetched_at": "2026-11-07T01:00:00Z", "status": "available",
            "weather": {"iconCode": "305", "description": "小雨", "obsTime": "2026-11-07T01:00:00Z"},
        }
        self.assertIsNone(make_decision({}, weather, now)["weather_adaptation"])

    def test_recent_fetch_with_stale_weather_observation_does_not_adapt_narration(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        weather = {
            "source": "和风天气 QWeather", "fetched_at": "2026-11-07T01:59:00Z", "status": "available",
            "weather": {"iconCode": "305", "description": "小雨", "obsTime": "2026-11-07T01:00:00Z"},
        }
        self.assertIsNone(make_decision({}, weather, now)["weather_adaptation"])

    def test_stale_weather_is_not_claimed_as_live_evidence(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        result = make_decision({}, {"source": "和风天气 QWeather", "fetched_at": "2026-11-07T01:00:00Z", "weather": {"description": "晴", "obsTime": "2026-11-07T01:00:00Z"}}, now)
        self.assertEqual(result["data_mode"], "partial")
        self.assertEqual(result["evidence_refs"], [])

    def test_weather_without_observation_time_is_not_claimed_as_live(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        weather = {"source": "和风天气 QWeather", "fetched_at": "2026-11-07T01:59:00Z", "status": "available", "weather": {"description": "晴"}}
        result = make_decision({}, weather, now)
        self.assertEqual(result["data_mode"], "partial")
        self.assertIsNone(result["weather_adaptation"])
        self.assertEqual(result["evidence_refs"], [])

    def test_unconfigured_weather_source_is_not_claimed_as_live(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        weather = {"source": "和风天气 QWeather", "fetched_at": now.isoformat(), "status": "unknown", "weather": None}
        result = make_decision({}, weather, now)
        self.assertEqual(result["data_mode"], "partial")
        self.assertEqual(result["evidence_refs"], [])

    def test_decision_expiry_never_outlives_weather_evidence(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        weather = {"source": "和风天气 QWeather", "fetched_at": "2026-11-07T01:49:00Z", "status": "available", "weather": {"description": "晴", "obsTime": "2026-11-07T01:49:00Z"}}
        result = make_decision({}, weather, now)
        self.assertEqual(result["expires_at"], "2026-11-07T02:04:00+00:00")


if __name__ == "__main__":
    unittest.main()
