import test from 'node:test';
import assert from 'node:assert/strict';
import { setManualStopDuration } from '../src/utils/itineraryDuration.js';

test('manual duration edits keep value and basis consistent', () => {
  const stop = { duration_minutes: null, duration_basis: 'unknown' };
  setManualStopDuration(stop, '25');
  assert.equal(stop.duration_minutes, 25);
  assert.equal(stop.duration_basis, 'user');
  setManualStopDuration(stop, '');
  assert.equal(stop.duration_minutes, null);
  assert.equal(stop.duration_basis, 'unknown');
});

test('unchanged duration preserves its existing provenance', () => {
  const stop = { duration_minutes: 30, duration_basis: 'source' };
  setManualStopDuration(stop, '30');
  assert.equal(stop.duration_basis, 'source');
  setManualStopDuration(stop, '35');
  assert.equal(stop.duration_basis, 'user');
});
