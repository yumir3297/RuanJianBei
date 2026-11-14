import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { getAvatarExpressionTargets } from '../src/components/avatar-expression.js';

const source = readFileSync(new URL('../src/components/ThreeAvatar.vue', import.meta.url), 'utf8');
const motionResolver = source.match(/function resolveMotionState\(\) \{[\s\S]*?\n\}/)?.[0];
const faceResolver = source.match(/function resolveExpressionState\(\) \{[\s\S]*?\n\}/)?.[0];
assert.ok(motionResolver && faceResolver, 'State resolvers must exist');
const props = { emotion: 'neutral', avatarState: 'idle', isSpeaking: false };
const context = vm.createContext({ props });
vm.runInContext(`${motionResolver}\n${faceResolver}`, context);
for (const body of ['idle', 'listening', 'thinking', 'happy', 'apology', 'guide']) {
  props.avatarState = body;
  for (const face of ['happy', 'relaxed', 'apology', 'angry', 'sad', 'surprised', 'neutral']) {
    props.emotion = face;
    assert.equal(vm.runInContext('resolveMotionState()', context), body);
    if (face !== 'neutral') assert.equal(vm.runInContext('resolveExpressionState()', context), face);
  }
}
props.isSpeaking = true;
props.avatarState = 'idle';
for (const face of ['happy', 'apology', 'neutral']) {
  props.emotion = face;
  assert.equal(vm.runInContext('resolveMotionState()', context), 'speaking');
}
// Exercise the actual head-posture block: facial choices must not change its target.
const headBlock = source.match(/    const bodyTargets =[^\n]+\n    const targetPitch =[^\n]+\n    head\.rotation\.x =[^\n]+/)?.[0];
assert.ok(headBlock, 'Head posture must resolve from the body state');
Object.assign(context, {
  getAvatarExpressionTargets,
  headBase: { x: 0 }, head: { rotation: { x: 0 } },
  profile: { expressionScale: 0.86, headResponse: 4.8 },
  deltaSeconds: 1 / 60,
  dampValue: (_current, target) => target,
});
props.isSpeaking = false;
props.avatarState = 'idle';
for (const face of ['happy', 'relaxed', 'apology']) {
  props.emotion = face;
  vm.runInContext(`{${headBlock}}`, context);
  assert.equal(context.head.rotation.x, 0);
}
console.log('Passed: facial selections preserve body state and head posture; explicit body reactions remain available.');
