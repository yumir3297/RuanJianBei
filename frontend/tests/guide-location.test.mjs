import test from 'node:test';
import assert from 'node:assert/strict';
import { createPinia, setActivePinia } from 'pinia';
import { useGuideLocationStore } from '../src/stores/guideLocation.js';

test('map and guide share current position only while the map is active', () => {
  setActivePinia(createPinia());
  const map = useGuideLocationStore();
  const guide = useGuideLocationStore();
  const position = { lat: 31, lng: 120 };
  map.update(position, 'real');
  assert.equal(guide.position, null);
  map.activate(position, 'real');
  position.lat = 0;
  assert.deepEqual(guide.position, { lat: 31, lng: 120 });
  assert.equal(guide.mapActive, true);
  map.update({ lat: 32, lng: 121 }, 'sim');
  assert.deepEqual(guide.position, { lat: 32, lng: 121 });
  assert.equal(guide.mode, 'sim');
  map.deactivate();
  map.update({ lat: 33, lng: 122 }, 'real');
  assert.equal(guide.mapActive, false);
  assert.equal(guide.position, null);
  assert.equal(guide.mode, 'unavailable');
  map.activate(null, 'denied');
  assert.equal(guide.position, null);
  assert.equal(guide.mode, 'denied');
});
