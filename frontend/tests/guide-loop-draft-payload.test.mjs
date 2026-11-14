import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildGuideLoopDraftPayload } from '../src/api/guideLoopPayload.js';

test('guide loop draft payload nests evidence fields and omits their form-only copies', () => {
  const payload = buildGuideLoopDraftPayload({
    base_revision: '0',
    action: 'add_alias',
    poi_id: 'bathing',
    target_id: 'prince',
    alias: '莲花里是谁',
    answer: '莲花里有太子佛立像。',
    evidence_id: 'gazetteer-1',
    source_ref: '公开方志',
    effective_from: '2026-11-10T00:00:00+08:00',
  });

  assert.deepEqual(payload.evidence, { evidence_id: 'gazetteer-1', source_ref: '公开方志' });
  assert.equal(Object.hasOwn(payload, 'evidence_id'), false);
  assert.equal(Object.hasOwn(payload, 'source_ref'), false);
  assert.equal(payload.target_id, 'prince');
});

test('draft preserves both knowledge reference fields and leaves empty references null', () => {
  const bound = buildGuideLoopDraftPayload({ evidence_id: 'e', source_ref: 's', knowledge_entry_id: '7', knowledge_revision_id: 'rev-1' });
  assert.equal(bound.knowledge_entry_id, '7');
  assert.equal(bound.knowledge_revision_id, 'rev-1');
  const unbound = buildGuideLoopDraftPayload({ evidence_id: 'e', source_ref: 's', knowledge_entry_id: '', knowledge_revision_id: '' });
  assert.equal(unbound.knowledge_entry_id, null);
  assert.equal(unbound.knowledge_revision_id, null);
});
