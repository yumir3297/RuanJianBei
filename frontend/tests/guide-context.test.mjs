import test from "node:test";
import assert from "node:assert/strict";
import { buildAdaptiveNarrationRequest, buildGuideContext, buildItinerarySuggestionRequest, findNearbyPublishedSpot, isGuideDecisionExpired, isPublishedCoordinateUsable, nextPublishedTourStop } from "../src/guide/context.js";
import { wgs84ToGcj02 } from "../src/constants/narration.js";

test("fresh accurate real fixes can inform context and retain observation time", () => {
  const snapshot = buildGuideContext({
    position: { lat: 31, lng: 120, accuracy: 12, observedAt: 9_990 },
    mode: "real", nowMs: 10_000, preferences: { interests: ["history"], remainingMinutes: 20 },
  });
  assert.equal(snapshot.location.validForSafety, true);
  assert.equal(snapshot.location.accuracyM, 12);
  assert.equal(snapshot.location.observedAt, new Date(9_990).toISOString());
  assert.equal(snapshot.visitor.remainingMinutes, 20);
});

test("stale, invalid and simulated positions are never live safety evidence", () => {
  const stale = buildGuideContext({ position: { lat: 31, lng: 120, accuracy: 5, observedAt: 1 }, mode: "real", nowMs: 40_000 });
  const simulated = buildGuideContext({ position: { lat: 31, lng: 120, accuracy: 5, ts: 10_000 }, mode: "sim", nowMs: 10_001 });
  const invalid = buildGuideContext({ position: { lat: 91, lng: 120, accuracy: 5, ts: 10_000 }, mode: "real", nowMs: 10_001 });
  assert.equal(stale.location.validForSafety, false);
  assert.equal(simulated.location.validForSafety, false);
  assert.equal(simulated.location.accuracyM, null);
  assert.equal(invalid.location.validForSafety, false);
});

test("directory coordinates need coordinate system and evidence", () => {
  assert.equal(isPublishedCoordinateUsable({ latitude: 31, longitude: 120, coordinate_system: "GCJ-02", coordinate_evidence_id: "survey-1" }), true);
  assert.equal(isPublishedCoordinateUsable({ latitude: 31, longitude: 120, coordinate_evidence_id: "survey-1" }), false);
  assert.equal(isPublishedCoordinateUsable({ latitude: 31, longitude: 120, coordinate_system: "GCJ-02" }), false);
});

test("nearby context suggests only a fresh accurate real fix and verified GCJ-02 catalog point", () => {
  const transformed = wgs84ToGcj02(31.4328, 120.0996);
  const location = { lat: 31.4328, lng: 120.0996, coordinateSystem: "WGS84", mode: "real", accuracyM: 12, validForSafety: true };
  const catalog = [
    { spot_code: "tower", title: "古塔", latitude: transformed.lat, longitude: transformed.lng, coordinate_system: "GCJ-02", coordinate_evidence_id: "survey-1" },
    { spot_code: "unknown", title: "未核验点", latitude: transformed.lat, longitude: transformed.lng, coordinate_system: "GCJ-02" },
  ];
  assert.equal(findNearbyPublishedSpot(location, catalog)?.spot.spot_code, "tower");
  assert.equal(findNearbyPublishedSpot({ ...location, mode: "sim" }, catalog), null);
  assert.equal(findNearbyPublishedSpot({ ...location, accuracyM: 81 }, catalog), null);
  assert.equal(findNearbyPublishedSpot({ ...location, validForSafety: false }, catalog), null);
});

test("decision becomes an explicit, source-bounded narration request", () => {
  const request = buildAdaptiveNarrationRequest({
    decision: { action: "short_narration" }, spot: { title: "古塔" }, interests: ["architecture"], remainingMinutes: 20,
  });
  assert.match(request.query, /约 45 秒/);
  assert.match(request.query, /已发布的景点资料/);
  assert.match(request.query, /architecture/);
  assert.equal(buildAdaptiveNarrationRequest({ decision: { action: "none" }, spot: { title: "古塔" } }), null);
});

test("next-stop hint uses confirmed progress and matching published revisions only", () => {
  const current = { stop_id: 'a', kind: 'visit', spot_code: 'a', source_revision_id: 'ra' };
  const next = { stop_id: 'b', kind: 'visit', spot_code: 'b', source_revision_id: 'rb' };
  const tour = { snapshot: { schema_version: 2, stops: [current, next] }, progress: { status: 'active', current_stop_id: 'a', status_by_stop: { a: 'current', b: 'pending' } } };
  const spot = { spot_code: 'a', title: '甲', published_revision_id: 'ra' };
  const catalog = [spot, { spot_code: 'b', title: '乙', published_revision_id: 'rb' }];
  assert.equal(nextPublishedTourStop(tour, spot, catalog).title, '乙');
  const query = buildAdaptiveNarrationRequest({ decision: { action: 'full_narration' }, spot, tour, catalog }).query;
  assert.match(query, /下一待游览景点是乙/);
  assert.match(query, /不要臆造/);
  assert.equal(nextPublishedTourStop(tour, { ...spot, published_revision_id: 'new' }, catalog), null);
  assert.equal(nextPublishedTourStop(tour, spot, [spot, { ...catalog[1], published_revision_id: 'new' }]), null);
  assert.equal(nextPublishedTourStop({ ...tour, progress: { ...tour.progress, status: 'finished' } }, spot, catalog), null);
  assert.equal(nextPublishedTourStop({ ...tour, snapshot: { schema_version: 2, stops: [current, { stop_id: 'rest', kind: 'break' }, next] }, progress: { ...tour.progress, status_by_stop: { a: 'current', rest: 'pending', b: 'pending' } } }, spot, catalog), null);
  assert.equal(nextPublishedTourStop(tour, spot, [...catalog, catalog[1]]), null);
});

test("verified precipitation adapts narration without claiming venue safety or indoor status", () => {
  const request = buildAdaptiveNarrationRequest({
    decision: { action: "full_narration" }, spot: { title: "古塔" }, interests: ["history"], remainingMinutes: 90,
    weatherAdaptation: { condition: "小雨", source: "和风天气 QWeather", kind: "precipitation" },
  });
  assert.match(request.query, /景区天气来源显示小雨/);
  assert.match(request.query, /不要推断.*室内.*开放.*安全/);
  assert.equal(buildAdaptiveNarrationRequest({
    decision: { action: "full_narration" }, spot: { title: "古塔" },
    weatherAdaptation: { condition: "小雨", source: "和风天气 QWeather", kind: "precipitation", simulated: true },
  }).query.includes("模拟天气"), true);
});

test("time pressure creates a reviewable itinerary request without silently changing budget", () => {
  const request = buildItinerarySuggestionRequest({ decision: { action: "short_narration" }, remainingMinutes: 20 });
  assert.match(request, /未完成景点/);
  assert.match(request, /不要修改.*剩余时间预算/);
  assert.equal(buildItinerarySuggestionRequest({ decision: { action: "full_narration" }, remainingMinutes: 90 }), null);
});

test("simulated crowd scenario is labeled and creates a reviewable avoidance proposal", () => {
  const request = buildItinerarySuggestionRequest({ decision: { action: "review_itinerary", reason_codes: ["demo_crowd_pressure"] }, remainingMinutes: 45, simulated: true });
  assert.match(request, /模拟数据/);
  assert.match(request, /避开拥挤/);
  assert.equal(buildItinerarySuggestionRequest({ decision: { action: "review_itinerary", reason_codes: ["crowd_pressure"] }, remainingMinutes: 45 }), null);
});

test("expired decision cannot be used for a new narration or proposal", () => {
  const decision = { expires_at: "2026-11-07T00:00:05Z" };
  assert.equal(isGuideDecisionExpired(decision, Date.parse("2026-11-07T00:00:04Z")), false);
  assert.equal(isGuideDecisionExpired(decision, Date.parse("2026-11-07T00:00:05Z")), true);
  assert.equal(isGuideDecisionExpired({}, Date.parse("2026-11-07T00:00:05Z")), false);
});
