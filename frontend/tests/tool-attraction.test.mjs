import test from 'node:test';
import assert from 'node:assert/strict';
import { findPublishedAttraction } from '../src/utils/toolAttraction.js';

test('named attraction requires an unambiguous published match', () => {
  assert.equal(findPublishedAttraction('梵宫', []), null);
  assert.equal(findPublishedAttraction('梵宫', [{ id: 7, title: '梵宫' }]), 7);
  assert.equal(findPublishedAttraction('梵宫', [{ id: 7, title: '梵宫' }, { id: 8, title: '梵宫' }]), null);
});
