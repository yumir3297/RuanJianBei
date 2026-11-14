import { test } from 'node:test';
import assert from 'node:assert/strict';
import { applyKnowledgeSelection, isCurrentKnowledgeSelection, publishedKnowledgeOptions } from '../src/api/guideLoopKnowledge.js';

test('only active published knowledge can be selected and draft title is not presented as published', () => {
  const options = publishedKnowledgeOptions([
    { id: 1, title: '草稿标题', draft_revision_id: 'draft', published_revision_id: 'published', withdrawn_at: null },
    { id: 2, published_revision_id: null },
    { id: 3, published_revision_id: 'old', withdrawn_at: '2026-11-13' },
  ]);
  assert.deepEqual(options, [{ entryId: 1, revisionId: 'published', label: '条目 1 · 版本 published · 存在草稿' }]);
  assert.throws(() => publishedKnowledgeOptions(null));
});

test('selection binds the pair and flags a replaced or withdrawn version', () => {
  const form = {};
  const options = publishedKnowledgeOptions([{ id: 1, published_revision_id: 'v1' }]);
  applyKnowledgeSelection(form, options[0]);
  assert.deepEqual(form, { knowledge_entry_id: 1, knowledge_revision_id: 'v1' });
  assert.equal(isCurrentKnowledgeSelection(form, options), true);
  assert.equal(isCurrentKnowledgeSelection(form, publishedKnowledgeOptions([{ id: 1, published_revision_id: 'v2' }])), false);
  assert.equal(isCurrentKnowledgeSelection(form, []), false);
  applyKnowledgeSelection(form, undefined);
  assert.deepEqual(form, { knowledge_entry_id: '', knowledge_revision_id: '' });
});
