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
