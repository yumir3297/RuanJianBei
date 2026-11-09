import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MAP_COORDINATE_AUDIT, MAP_ROUTE_STOPS } from '../src/constants/mapCoordinateAudit.js';
import { wgs84ToGcj02 } from '../src/constants/narration.js';
import { layoutMapLabels } from '../src/utils/mapMarkers.js';

test('every map reference has traceable source and source coordinate system', () => {
  const refs = Object.values(MAP_COORDINATE_AUDIT).filter(p=>p.coordinateStatus==='reference');
  assert.equal(refs.length,15);
  for (const p of refs) {
    assert.ok(p.sourceUrl.startsWith('https://'));
    assert.ok(p.sourceCoordinate.crs);
    const converted=p.sourceCoordinate.crs==='WGS84' ? wgs84ToGcj02(p.sourceCoordinate.lat,p.sourceCoordinate.lng) : p.sourceCoordinate;
    assert.equal(p.lat,converted.lat);assert.equal(p.lng,converted.lng);
  }
});
test('unlocated and other-scenic entries never masquerade as geographic points', () => {
  const entries=Object.values(MAP_COORDINATE_AUDIT);
  assert.equal(entries.filter(p=>p.coordinateStatus==='pending').length,1);
  assert.equal(entries.filter(p=>p.coordinateStatus==='other-scenic').length,6);
  for(const p of entries.filter(p=>p.coordinateStatus!=='reference')) {
    assert.equal(p.lat,undefined);assert.equal(p.lng,undefined);
  }
  assert.equal(MAP_COORDINATE_AUDIT['香月花街'].coordinateStatus,'other-scenic');
  assert.equal(MAP_COORDINATE_AUDIT['灵山大佛'].lng,120.096477);
});
test('labels give way to fixed controls and clusters instead of moving locations', () => {
  const groups=[[{name:'灵山大佛',x:100,y:150}],[{name:'被控件挡住',x:420,y:120}],[{name:'聚合甲',x:100,y:200},{name:'聚合乙',x:110,y:205}]];
  const labels=layoutMapLabels(groups,455,774);
  assert.ok(labels.has('灵山大佛'));
  assert.equal(labels.has('被控件挡住'),false);
  assert.equal(labels.has('聚合甲'),false);
});

test('route-only landmarks also carry exact source IDs and GCJ-02 references', () => {
  assert.equal(MAP_ROUTE_STOPS.length,5);
  for (const stop of MAP_ROUTE_STOPS) {
    assert.ok(stop.sourcePoiId);
    assert.equal(stop.sourceCoordinate.crs,'GCJ-02');
    assert.ok(stop.sourceUrl.endsWith(stop.sourcePoiId));
  }
});
