// Convert the CC0 Standard library's T-pose-relative rotations to VRMA 1.0.
// Run from frontend: node scripts/convert-quaternius.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Quaternion, Vector3 } from 'three';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const source = path.join(root, 'motion-src/quaternius/Animation Library[Standard]/Godot/AnimationLibrary_Godot_Standard.glb');
const bytes = fs.readFileSync(source);
const jsonLength = bytes.readUInt32LE(12);
const gltf = JSON.parse(bytes.subarray(20, 20 + jsonLength));
const binary = bytes.subarray(28 + jsonLength);
function accessor(index) {
  const a = gltf.accessors[index], v = gltf.bufferViews[a.bufferView];
  if (a.componentType !== 5126 || a.sparse) throw Error('Expected dense float accessor');
  const size = { SCALAR: 1, VEC3: 3, VEC4: 4 }[a.type];
  return Array.from({ length: a.count }, (_, i) => Array.from({ length: size }, (_, k) =>
    binary.readFloatLE((v.byteOffset || 0) + (a.byteOffset || 0) + i * (v.byteStride || size * 4) + k * 4)));
}
const parents = new Map();
gltf.nodes.forEach((n, i) => n.children?.forEach(c => parents.set(c, i)));
const mapping = { 'DEF-hips': 'hips', 'DEF-spine.001': 'spine', 'DEF-spine.002': 'chest', 'DEF-spine.003': 'upperChest', 'DEF-neck': 'neck', 'DEF-head': 'head' };
for (const [suffix, side] of [['L', 'left'], ['R', 'right']]) {
  for (const [sourceName, targetName] of Object.entries({ shoulder: 'Shoulder', upper_arm: 'UpperArm', forearm: 'LowerArm', hand: 'Hand', thigh: 'UpperLeg', shin: 'LowerLeg', foot: 'Foot', toe: 'Toes' })) mapping[`DEF-${sourceName}.${suffix}`] = side + targetName;
  for (const finger of ['index', 'middle', 'ring', 'pinky', 'thumb']) {
    const names = finger === 'thumb' ? ['Metacarpal', 'Proximal', 'Distal'] : ['Proximal', 'Intermediate', 'Distal'];
    names.forEach((segment, i) => {
      const name = finger === 'pinky' ? 'Little' : finger[0].toUpperCase() + finger.slice(1);
      mapping[`DEF-${finger === 'thumb' ? '' : 'f_'}${finger}.0${i + 1}.${suffix}`] = side + name + segment;
    });
  }
}
const mapped = gltf.nodes.flatMap((n, i) => mapping[n.name] ? [i] : []);
const targets = new Map(mapped.map((i, k) => [i, k]));
function tracks(animation) {
  return animation.channels.map(c => {
    const s = animation.samplers[c.sampler];
    if (s.interpolation && s.interpolation !== 'LINEAR') throw Error('Unsupported interpolation');
    return { node: c.target.node, property: c.target.path, times: accessor(s.input).flat(), values: accessor(s.output) };
  });
}
function worldPose(channels, time) {
  const locals = gltf.nodes.map(n => ({ q: new Quaternion().fromArray(n.rotation || [0, 0, 0, 1]), p: new Vector3().fromArray(n.translation || [0, 0, 0]) }));
  for (const c of channels) {
    let b = c.times.findIndex(t => t >= time); if (b < 0) b = c.times.length - 1;
    const a = Math.max(0, b - 1), weight = b === a ? 0 : Math.min(1, Math.max(0, (time - c.times[a]) / (c.times[b] - c.times[a])));
    if (c.property === 'rotation') locals[c.node].q.fromArray(c.values[a]).slerp(new Quaternion().fromArray(c.values[b]), weight).normalize();
    if (c.property === 'translation') locals[c.node].p.fromArray(c.values[a]).lerp(new Vector3().fromArray(c.values[b]), weight);
    if (c.property === 'scale' && c.values.some(v => v.some(x => Math.abs(x - 1) > 1e-4))) throw Error('Non-unit animated scale');
  }
  const worlds = [];
  function visit(i) {
    if (worlds[i]) return worlds[i];
    const local = locals[i], parent = parents.has(i) ? visit(parents.get(i)) : null;
    return worlds[i] = parent ? { q: parent.q.clone().multiply(local.q), p: local.p.clone().applyQuaternion(parent.q).add(parent.p) } : local;
  }
  gltf.nodes.forEach((_, i) => visit(i)); return worlds;
}
const reference = worldPose(tracks(gltf.animations.find(a => a.name === 'A_TPose')), 0);
for (const [name, filename] of [['Idle_Loop', 'cc0_idle'], ['Idle_Talking_Loop', 'cc0_talking']]) {
  const channels = tracks(gltf.animations.find(a => a.name === name));
  const duration = Math.max(...channels.map(c => c.times.at(-1)));
  const frames = Math.ceil(duration * 30), times = Array.from({ length: frames + 1 }, (_, i) => i * duration / frames);
  const nodes = mapped.map(i => {
    const parent = parents.get(i), p = reference[i].p.clone();
    if (targets.has(parent)) p.sub(reference[parent].p);
    return { name: mapping[gltf.nodes[i].name], translation: p.toArray(), ...(gltf.nodes[i].children?.some(c => targets.has(c)) ? { children: gltf.nodes[i].children.filter(c => targets.has(c)).map(c => targets.get(c)) } : {}) };
  });
  const out = { asset: { version: '2.0', generator: 'Quaternius CC0 T-pose retargeter' }, extensionsUsed: ['VRMC_vrm_animation'], extensions: { VRMC_vrm_animation: { specVersion: '1.0', humanoid: { humanBones: Object.fromEntries(nodes.map((n, node) => [n.name, { node }])) } } }, scene: 0, scenes: [{ nodes: mapped.filter(i => !targets.has(parents.get(i))).map(i => targets.get(i)) }], nodes, animations: [{ name, channels: [], samplers: [] }], accessors: [], bufferViews: [], buffers: [] };
  const chunks = []; let length = 0;
  function add(values, type) {
    const flat = values.flat(), data = Buffer.alloc(flat.length * 4); flat.forEach((v, i) => data.writeFloatLE(v, i * 4));
    const bufferView = out.bufferViews.push({ buffer: 0, byteOffset: length, byteLength: data.length }) - 1; chunks.push(data); length += data.length;
    return out.accessors.push({ bufferView, componentType: 5126, count: values.length, type, ...(type === 'SCALAR' ? { min: [Math.min(...flat)], max: [Math.max(...flat)] } : {}) }) - 1;
  }
  const input = add(times, 'SCALAR');
  const poses = times.map(t => worldPose(channels, t));
  // Stationary guide gestures: omit pelvis/legs and translation to keep the runtime's planted stance.
  for (const i of mapped.filter(i => !/hips|Leg|Foot|Toes/.test(mapping[gltf.nodes[i].name]))) {
    const parent = parents.get(i);
    const values = poses.map(p => {
      const delta = p[i].q.clone().multiply(reference[i].q.clone().invert());
      const parentDelta = p[parent].q.clone().multiply(reference[parent].q.clone().invert());
      return parentDelta.invert().multiply(delta).normalize().toArray();
    });
    for (let k = 1; k < values.length; k++) if (values[k].reduce((s, v, j) => s + v * values[k - 1][j], 0) < 0) values[k] = values[k].map(v => -v);
    const sampler = out.animations[0].samplers.push({ input, output: add(values, 'VEC4'), interpolation: 'LINEAR' }) - 1;
    out.animations[0].channels.push({ sampler, target: { node: targets.get(i), path: 'rotation' } });
  }
  out.buffers.push({ byteLength: length });
  let text = Buffer.from(JSON.stringify(out)); text = Buffer.concat([text, Buffer.alloc((4 - text.length % 4) % 4, 32)]);
  const header = Buffer.alloc(20); header.write('glTF'); header.writeUInt32LE(2, 4); header.writeUInt32LE(28 + text.length + length, 8); header.writeUInt32LE(text.length, 12); header.write('JSON', 16);
  const binHeader = Buffer.alloc(8); binHeader.writeUInt32LE(length); binHeader.write('BIN\0', 4);
  fs.writeFileSync(path.join(root, `frontend/public/motions/${filename}.vrma`), Buffer.concat([header, text, binHeader, ...chunks]));
  console.log(filename, { duration, frames: times.length, channels: out.animations[0].channels.length });
}
