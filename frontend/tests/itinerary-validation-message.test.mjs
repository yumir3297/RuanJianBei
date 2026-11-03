import test from 'node:test';
import assert from 'node:assert/strict';
import { proposalValidationMessage, proposalValidationAllowsConfirmation } from '../src/utils/itineraryValidation.js';

test('a passed check identifies its scope and leaves accessibility unverified', () => {
  assert.match(proposalValidationMessage('pass'), /无障碍/);
  assert.equal(proposalValidationAllowsConfirmation('pass'), true);
});

test('unknown or conflicting validation cannot be mistaken for a pass', () => {
  for (const status of ['conflict', 'unknown', undefined]) {
    assert.doesNotMatch(proposalValidationMessage(status), /已通过/);
    assert.equal(proposalValidationAllowsConfirmation(status), false);
  }
  assert.equal(proposalValidationAllowsConfirmation('unverified'), true);
});
