import test from 'node:test';
import assert from 'node:assert/strict';
import { routeDurationMinutes } from '../src/utils/routeDuration.js';

test('route duration keeps decimals and uses the upper end of a range', () => {
  assert.equal(routeDurationMinutes('3.5-4小时全景'), 240);
  assert.equal(routeDurationMinutes('2.5小时落日线'), 150);
  assert.equal(routeDurationMinutes('3小时精选'), 180);
  assert.equal(routeDurationMinutes('未知'), null);
});
