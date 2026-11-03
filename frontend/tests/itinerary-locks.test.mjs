import test from 'node:test';
import assert from 'node:assert/strict';
import { canDeleteStop, canEditDuration, canMoveStop } from '../src/utils/itineraryLocks.js';

const stop = (id, locks = []) => ({ stop_id: id, locked_fields: locks });

test('saved locks remain effective until an unlock is saved', () => {
  const saved = [stop('a', ['stop'])];
  const draft = [stop('a')];
  assert.equal(canEditDuration(draft[0], saved), false);
  assert.equal(canDeleteStop(draft, 0, saved), false);
  assert.equal(canEditDuration(draft[0], draft), true);
});

test('deletion and movement cannot shift another saved position lock', () => {
  const saved = [stop('a'), stop('b', ['position']), stop('c')];
  assert.equal(canDeleteStop(saved, 0, saved), false);
  assert.equal(canDeleteStop(saved, 1, saved), false);
  assert.equal(canDeleteStop(saved, 2, saved), true);
  assert.equal(canMoveStop(saved, 0, 1, saved), false);
  assert.equal(canMoveStop(saved, 2, -1, saved), false);
});

test('a duration lock blocks editing and deletion but allows reordering', () => {
  const saved = [stop('a', ['duration']), stop('b')];
  assert.equal(canEditDuration(saved[0], saved), false);
  assert.equal(canDeleteStop(saved, 0, saved), false);
  assert.equal(canMoveStop(saved, 0, 1, saved), true);
});
