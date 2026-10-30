import { test } from 'node:test';
import assert from 'node:assert/strict';
import { visionConfirmation } from '../src/utils/visionConfirmation.js';
test('confirmation requires explicit selected published entry', () => {
  const catalog = { site_id:'site', items:[{spot_code:'A',published_revision_id:'r1',title:'A'}] };
  assert.equal(visionConfirmation(catalog, ''), null);
  assert.equal(visionConfirmation(catalog, 'B'), null);
  assert.deepEqual(visionConfirmation(catalog, 'A'), {site_id:'site',spot_code:'A',published_revision_id:'r1'});
  assert.equal(visionConfirmation({site_id:'site', items:[{spot_code:'A'}]}, 'A'), null);
});

test('late capture or catalog results are ignored after image change and close', async () => {
  const { createVisionAsyncGuard } = await import('../src/utils/visionConfirmation.js');
  const guard = createVisionAsyncGuard();
  let resolveCapture;
  const pending = guard.run(() => new Promise(resolve => { resolveCapture = resolve; }));
  guard.cancel();
  resolveCapture('old');
  assert.equal(await pending, undefined);
  assert.equal(await guard.run(async () => 'current'), 'current');
});
