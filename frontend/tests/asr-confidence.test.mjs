import { test } from 'node:test';
import assert from 'node:assert/strict';
import { displayableASRConfidence } from '../src/utils/asrConfidence.js';

test('only provider confidence is displayed as a percentage', () => {
  assert.equal(displayableASRConfidence({ confidence: 0.86, confidence_source: 'heuristic' }), -1);
  assert.equal(displayableASRConfidence({ confidence: 0.9, confidence_source: 'provider' }), 0.9);
  assert.equal(displayableASRConfidence({ confidence: NaN, confidence_source: 'provider' }), -1);
  assert.equal(displayableASRConfidence({ confidence: 1.2, confidence_source: 'provider' }), -1);
});
