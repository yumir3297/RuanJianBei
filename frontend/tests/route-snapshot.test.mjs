import test from 'node:test';
import assert from 'node:assert/strict';
import { routeSnapshot } from '../src/utils/routeSnapshot.js';

test('saving a route does not turn an estimated duration into a visitor budget', () => {
  const snapshot = routeSnapshot({ id: 'route-1', title: '路线', duration_label: '3.5-4小时', spots: ['景点'] });
  assert.equal(snapshot.constraints.available_minutes, null);
  assert.equal(snapshot.stops[0].name, '景点');
  assert.equal(snapshot.source_references[0].source_id, 'route-1');
});

test('updating a route preserves visitor supplied constraints', () => {
  const snapshot = routeSnapshot({ id: 'route-1', spots: [] }, { available_minutes: 90, interests: ['文化'] });
  assert.equal(snapshot.constraints.available_minutes, 90);
  assert.deepEqual(snapshot.constraints.interests, ['文化']);
});
