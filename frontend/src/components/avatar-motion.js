const STATE_MOTIONS = Object.freeze({
  idle: Object.freeze({
    pitch: 0.012, yaw: 0.02, roll: 0.006, bodySpeed: 0.48,
    breath: 0.006, breathSpeed: 1.15, nod: 0,
    gazeX: 0.08, gazeY: 0.04, gazeOffsetX: 0, gazeOffsetY: 0, gazeSpeed: 0.24,
    blinkMin: 2.4, blinkMax: 4.8, blinkDuration: 0.18,
  }),
  listening: Object.freeze({
    pitch: 0.008, yaw: 0.012, roll: 0.004, bodySpeed: 0.38,
    breath: 0.005, breathSpeed: 1.05, nod: 0.008,
    gazeX: 0.035, gazeY: 0.025, gazeOffsetX: 0, gazeOffsetY: 0.015, gazeSpeed: 0.18,
    blinkMin: 2.0, blinkMax: 3.8, blinkDuration: 0.17,
  }),
  thinking: Object.freeze({
    pitch: 0.01, yaw: 0.014, roll: 0.012, bodySpeed: 0.32,
    breath: 0.005, breathSpeed: 0.95, nod: 0,
    gazeX: 0.06, gazeY: 0.035, gazeOffsetX: 0.24, gazeOffsetY: 0.1, gazeSpeed: 0.16,
    blinkMin: 3.0, blinkMax: 5.6, blinkDuration: 0.2,
  }),
  speaking: Object.freeze({
    pitch: 0.016, yaw: 0.022, roll: 0.006, bodySpeed: 0.72,
    breath: 0.008, breathSpeed: 1.35, nod: 0.025,
    gazeX: 0.055, gazeY: 0.035, gazeOffsetX: 0, gazeOffsetY: 0.02, gazeSpeed: 0.28,
    blinkMin: 2.2, blinkMax: 4.2, blinkDuration: 0.17,
  }),
  happy: Object.freeze({
    pitch: 0.018, yaw: 0.026, roll: 0.01, bodySpeed: 0.76,
    breath: 0.009, breathSpeed: 1.4, nod: 0.03,
    gazeX: 0.065, gazeY: 0.04, gazeOffsetX: 0, gazeOffsetY: 0.035, gazeSpeed: 0.3,
    blinkMin: 1.8, blinkMax: 3.4, blinkDuration: 0.16,
  }),
  apology: Object.freeze({
    pitch: 0.008, yaw: 0.01, roll: 0.005, bodySpeed: 0.34,
    breath: 0.005, breathSpeed: 0.9, nod: 0,
    gazeX: 0.025, gazeY: 0.02, gazeOffsetX: -0.06, gazeOffsetY: -0.08, gazeSpeed: 0.15,
    blinkMin: 2.8, blinkMax: 4.8, blinkDuration: 0.2,
  }),
  guide: Object.freeze({
    pitch: 0.014, yaw: 0.024, roll: 0.008, bodySpeed: 0.62,
    breath: 0.007, breathSpeed: 1.2, nod: 0.018,
    gazeX: 0.07, gazeY: 0.04, gazeOffsetX: 0.08, gazeOffsetY: 0.025, gazeSpeed: 0.25,
    blinkMin: 2.2, blinkMax: 4.3, blinkDuration: 0.18,
  }),
});

const DEFAULT_PROFILE = Object.freeze({
  motionScale: 0.9,
  gestureScale: 0.9,
  transitionSpeed: 5.5,
  waveSpeed: 5.8,
  armResponse: 7.5,
});

const AVATAR_MOTION_PROFILES = Object.freeze({
  monk: Object.freeze({ ...DEFAULT_PROFILE, motionScale: 0.82, gestureScale: 0.82, waveSpeed: 5.4 }),
  hanfu: Object.freeze({ ...DEFAULT_PROFILE, motionScale: 0.76, gestureScale: 0.78, transitionSpeed: 5.0 }),
  modern: Object.freeze({ ...DEFAULT_PROFILE, motionScale: 1.0, gestureScale: 1.0, transitionSpeed: 6.2, waveSpeed: 6.2 }),
});

export function getAvatarMotionProfile(preset) {
  return AVATAR_MOTION_PROFILES[preset] || DEFAULT_PROFILE;
}

export function getAvatarStateMotion(state) {
  return STATE_MOTIONS[state] || STATE_MOTIONS.idle;
}
