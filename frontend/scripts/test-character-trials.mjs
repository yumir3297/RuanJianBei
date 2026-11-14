import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { AVATAR_ACTIONS, AVATAR_STATE_ACTIONS, GREETING_ACTIONS } from '../src/components/avatar-actions.js';
import { hasAvatarActionExpression } from '../src/components/avatar-expression.js';

const motions = fileURLToPath(new URL('../public/motions/', import.meta.url));
const suffixes = ['think_draft', 'narrate_emphasis_draft', 'greet_wave_soft_draft',
  'greet_bow_draft', 'clap_draft', 'cupped_greeting', 'wave_draft', 'farewell_wave_candidate',
  'exhibit_draft', 'remind_draft', 'salute_greeting', 'bow_farewell'];
const automatic = [...GREETING_ACTIONS, ...Object.values(AVATAR_STATE_ACTIONS)
  .flatMap(state => (state.actions || [state]).map(item => item.action))];
for (const prefix of ['qinglan', 'jingxing', 'ningling']) {
  for (const suffix of suffixes) {
    const name = `${prefix}_${suffix}`;
    const action = AVATAR_ACTIONS[name];
    const retained = prefix === 'qinglan'
      ? ['cupped_greeting', 'salute_greeting', 'bow_farewell', 'exhibit_draft']
      : prefix === 'jingxing' ? ['cupped_greeting', 'wave_draft', 'farewell_wave_candidate', 'exhibit_draft', 'remind_draft']
      : ['cupped_greeting', 'wave_draft', 'farewell_wave_candidate', 'exhibit_draft', 'remind_draft'];
    if (!retained.includes(suffix)) {
      assert.equal(action, undefined, `${name} removed from active trials`);
      continue;
    }
    assert.ok(action, `${name} registered`);
    assert.equal(action.name, name);
    assert.ok(hasAvatarActionExpression(name), `${name} facial timeline`);
    assert.ok(!automatic.includes(name), `${name} manual-only`);
    if (action.file) assert.ok(fs.existsSync(motions + action.file), `${name} asset`);
    if (action.kind === 'vrma') {
      const data = fs.readFileSync(motions + action.file);
      const jsonLength = data.readUInt32LE(12);
      const doc = JSON.parse(data.subarray(20, 20 + jsonLength).toString());
      assert.ok(doc.extensions?.VRMC_vrm_animation, `${name} VRMA extension`);
      const anim = doc.animations[0];
      const duration = Math.max(...anim.samplers.map(s => doc.accessors[s.input].max[0]));
      assert.ok(Math.abs(duration * 1000 - action.durationMs) < 45,
        `${name} duration ${duration}s versus ${action.durationMs}ms`);
    }
  }
}
for (const name of ['lean_in', 'cc0_idle', 'narrate_present', 'open_goodbye', 'qinglan_farewell', 'ningling_farewell']) {
  assert.equal(AVATAR_ACTIONS[name], undefined, `${name} remains archived`);
}
assert.deepEqual(Object.keys(AVATAR_ACTIONS).filter(name => name.startsWith('qinglan_')).sort(),
  ['qinglan_bow_farewell', 'qinglan_cupped_greeting', 'qinglan_exhibit_draft', 'qinglan_salute_greeting'],
  'Qinglan has four Hanfu gestures');
assert.deepEqual(Object.keys(AVATAR_ACTIONS).filter(name => name.startsWith('ningling_')).sort(),
  ['ningling_cupped_greeting', 'ningling_exhibit_draft', 'ningling_farewell_wave_candidate',
    'ningling_remind_draft', 'ningling_wave_draft'],
  'Ningling trials untouched');
assert.deepEqual(Object.keys(AVATAR_ACTIONS).filter(name => name.startsWith('jingxing_')).sort(),
  ['jingxing_cupped_greeting', 'jingxing_exhibit_draft', 'jingxing_farewell_wave_candidate', 'jingxing_remind_draft', 'jingxing_wave_draft'],
  'Jingxing duplicate trials removed');
for (const name of ['think', 'narrate_emphasis', 'greet_wave_soft', 'greet_bow', 'applaud_modern']) {
  assert.ok(AVATAR_ACTIONS[name], `${name} common gesture retained`);
}
assert.equal(AVATAR_ACTIONS.jingxing_farewell_wave_candidate.blendInMs, 450,
  'character draft must not be shadowed by legacy catalog');
console.log('PASS: removed duplicates stay inactive; utility trials manual-only; assets, timelines and durations valid.');
