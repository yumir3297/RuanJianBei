import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_SPEECH_RATE,
  SPEECH_RATE_OPTIONS,
  SPEECH_RATE_STORAGE_KEY,
  normalizeSpeechRate,
  readSpeechRate,
  writeSpeechRate,
} from '../src/utils/speechRatePreference.js';

function createStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, String(value)); },
    values,
  };
}

test('speech rate options include the default and supported visitor choices', () => {
  assert.equal(DEFAULT_SPEECH_RATE, 1);
  assert.deepEqual(SPEECH_RATE_OPTIONS, [0.8, 1, 1.2, 1.5]);
});

test('speech rate normalization accepts supported values and defaults invalid values', () => {
  assert.equal(normalizeSpeechRate(1.2), 1.2);
  assert.equal(normalizeSpeechRate('0.8'), 0.8);
  for (const value of [undefined, null, NaN, 0.7, 1.1, 1.6, 'fast']) {
    assert.equal(normalizeSpeechRate(value), DEFAULT_SPEECH_RATE);
  }
});

test('speech rate preference reads and writes only the visitor preference key', () => {
  const storage = createStorage({ 'a5-avatar-config-v1': '{"speechRate":1.5}' });
  assert.equal(readSpeechRate(storage), DEFAULT_SPEECH_RATE);
  assert.equal(writeSpeechRate(1.2, storage), 1.2);
  assert.equal(storage.values.get(SPEECH_RATE_STORAGE_KEY), '1.2');
  assert.equal(storage.values.get('a5-avatar-config-v1'), '{"speechRate":1.5}');
  assert.equal(readSpeechRate(storage), 1.2);
});

test('invalid stored values and unavailable storage fall back safely', () => {
  assert.equal(readSpeechRate(createStorage({ [SPEECH_RATE_STORAGE_KEY]: 'not json' })), DEFAULT_SPEECH_RATE);
  assert.equal(readSpeechRate({ getItem() { throw new Error('blocked'); } }), DEFAULT_SPEECH_RATE);
  assert.equal(writeSpeechRate(1.5, { setItem() { throw new Error('blocked'); } }), 1.5);
});

test('a browser that throws while exposing localStorage still falls back safely', () => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    get() { throw new Error('storage access denied'); },
  });
  try {
    assert.equal(readSpeechRate(), DEFAULT_SPEECH_RATE);
    assert.equal(writeSpeechRate(1.5), 1.5);
  } finally {
    if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor);
    else delete globalThis.localStorage;
  }
});
