import {test} from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolveEvidence } from '../src/utils/messageSources.js';
test('unmatched evidence is not a verifiable citation', () => {
  assert.equal(resolveEvidence('2', [{evidence_id:'证据1',title:'A'}]), null);
  assert.equal(resolveEvidence('1', [{evidence_id:'证据1',title:'A'}]).title, 'A');
});
test('every answer with sources exposes its own source list without inline citation', () => {
  const ui=readFileSync(new URL('../src/views/tourist/ChatView.vue',import.meta.url),'utf8');
  assert.match(ui,/v-if="message\.sources\?\.length"[^>]*@click="showMessageSources\(message\)"/);
});
