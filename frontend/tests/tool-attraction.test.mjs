import test from 'node:test';
import assert from 'node:assert/strict';
import { findPublishedAttraction, resolvePublishedAttraction } from '../src/utils/toolAttraction.js';

test('named attraction requires an unambiguous published match', () => {
  assert.equal(findPublishedAttraction('梵宫', []), null);
  assert.equal(findPublishedAttraction('梵宫', [{ id: 7, title: '梵宫' }]), 7);
  assert.equal(findPublishedAttraction('梵宫', [{ id: 7, title: '梵宫' }, { id: 8, title: '梵宫' }]), null);
});

test('retry loads the published catalog after an earlier failure', async () => {
  const store = { loaded: false, loading: false, bootstrap: { attractions: [] },
    async loadBootstrap() { this.loaded = true; this.bootstrap.attractions = [{ id: 7, title: '梵宫' }]; } };
  assert.equal(await resolvePublishedAttraction('梵宫', store), 7);
});

test('a failed catalog refresh cannot reuse an old cached attraction', async () => {
  const store = { loaded: false, loading: false, bootstrap: { attractions: [{ id: 7, title: '梵宫' }] },
    async loadBootstrap() {} };
  assert.equal(await resolvePublishedAttraction('梵宫', store), null);
});
