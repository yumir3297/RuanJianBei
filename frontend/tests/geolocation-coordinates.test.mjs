import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
let vite, useGeolocation, narrationPosition, demoNarrationPosition, canFinishNarration, correct, callback, errorCallback, savedNavigator;
before(async () => {
 savedNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
 Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { geolocation: {
 watchPosition(success, error) { callback = success; errorCallback = error; return 17; }, clearWatch() {},
 } } });
 vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-geo-coordinate-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
 ({ useGeolocation, narrationPosition, demoNarrationPosition, canFinishNarration } = await vite.ssrLoadModule('/src/composables/useGeolocation.js'));
 ({ wgs84ToGcj02: correct } = await vite.ssrLoadModule('/src/constants/narration.js'));
});
after(async () => {
 await vite?.close();
 if (savedNavigator) Object.defineProperty(globalThis, 'navigator', savedNavigator);
 else delete globalThis.navigator;
});
const good = { latitude: 31.4285, longitude: 120.0998, accuracy: 8 };
test('stopped or replaced browser watches cannot restore stale position or trigger fallback', () => {
 const geo = useGeolocation();
 geo.start();
 const oldSuccess = callback, oldError = errorCallback;
 geo.stop();
 oldSuccess({ coords: good, timestamp: 10 });
 oldError({ code: 1 });
 assert.equal(geo.position.value, null);
 assert.equal(geo.mode.value, 'idle');
 geo.start();
 callback({ coords: good, timestamp: 20 });
 oldSuccess({ coords: { ...good, latitude: 39 }, timestamp: 10 });
 oldError({ code: 1 });
 assert.equal(geo.mode.value, 'real');
 assert.equal(geo.position.value.observedAt, 20);
 geo.stop();
});
test('demo spot coordinates only trigger narration in simulation mode', () => {
 const position = { lat: 31, lng: 120 };
 assert.equal(demoNarrationPosition('real', position), null);
 assert.equal(demoNarrationPosition('sim', position), position);
});
test('automatic narration remains valid only while near the spot with usable location', () => {
 const spot = { lat: 31.42, lng: 120.10 };
 assert.equal(canFinishNarration('real', spot, spot), true);
 assert.equal(canFinishNarration('low_accuracy', spot, spot), false);
 assert.equal(canFinishNarration('real', { lat: 39, lng: 116 }, spot), false);
});
test('automatic narration accepts only valid real or simulated position modes', () => {
 const position = { lat: 31, lng: 120 };
 assert.equal(narrationPosition('real', position), position);
 assert.equal(narrationPosition('sim', position), position);
 for (const mode of ['low_accuracy', 'out_of_area', 'idle', 'denied']) assert.equal(narrationPosition(mode, position), null);
});
test('standard browser coordinates retain raw WGS84 and browser observation time', () => {
 const geo = useGeolocation(); geo.start();
 try {
 callback({ coords: good, timestamp: 123456 });
 const expected = correct(good.latitude, good.longitude);
 assert.equal(geo.mode.value, 'real');
 assert.equal(geo.position.value.lat, expected.lat);
 assert.equal(geo.position.value.lng, expected.lng);
 assert.equal(geo.position.value.accuracy, 8);
 assert.deepEqual(geo.position.value.wgs84, { lat: good.latitude, lng: good.longitude });
 assert.equal(geo.position.value.observedAt, 123456);
 } finally { geo.stop(); }
});
test('valid browser coordinates outside scenic area are not labelled real', () => {
 const geo = useGeolocation(); geo.start();
 try {
 callback({ coords: { latitude: 39.9, longitude: 116.4, accuracy: 8 } });
 assert.equal(geo.mode.value, 'out_of_area');
 assert.ok(Number.isFinite(geo.position.value.lat));
 assert.match(geo.error.value, /不在景区/);
  assert.doesNotMatch(geo.error.value, /已切换模拟/);
 } finally { geo.stop(); }
});
test('switching to simulation does not reuse a previous real position', () => {
 const geo = useGeolocation(); geo.start();
 try {
  callback({ coords: good });
  const real = { ...geo.position.value };
  geo.startSimulated();
  assert.equal(geo.mode.value, 'sim');
  assert.notDeepEqual({ lat: geo.position.value.lat, lng: geo.position.value.lng }, { lat: real.lat, lng: real.lng });
 } finally { geo.stop(); }
});
test('invalid coordinates or accuracy clear previous position and prevent real narration', () => {
 const invalid = [undefined, {}, { ...good, latitude: NaN }, { ...good, longitude: Infinity },
 { ...good, latitude: 91 }, { ...good, longitude: -181 }, { ...good, accuracy: -1 },
 { ...good, accuracy: NaN }, { ...good, latitude: '31' }];
 const geo = useGeolocation(); geo.start();
 try {
 for (const coords of invalid) {
 callback({ coords: good }); callback({ coords });
 assert.notEqual(geo.mode.value, 'real');
 assert.equal(geo.position.value, null);
 assert.equal(geo.accuracyPoor.value, true);
 assert.match(geo.error.value, /无效|不可用/);
 }
 } finally { geo.stop(); }
});
