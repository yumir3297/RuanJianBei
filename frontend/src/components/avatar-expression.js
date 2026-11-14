const EXPRESSION_TARGETS = Object.freeze({
  idle: Object.freeze({ relaxed: 0.045, headPitch: 0 }),
  listening: Object.freeze({ relaxed: 0.07, surprised: 0.018, headPitch: -0.005 }),
  thinking: Object.freeze({ relaxed: 0.065, surprised: 0.04, headPitch: 0.012 }),
  speaking: Object.freeze({ relaxed: 0.03, happy: 0.025, headPitch: 0 }),
  happy: Object.freeze({ happy: 0.36, relaxed: 0.06, headPitch: -0.012 }),
  apology: Object.freeze({ sad: 0.24, relaxed: 0.025, headPitch: 0.052 }),
  guide: Object.freeze({ happy: 0.1, relaxed: 0.06, headPitch: -0.006 }),
  angry: Object.freeze({ angry: 0.28, sad: 0.025, headPitch: -0.01 }),
  sad: Object.freeze({ sad: 0.27, relaxed: 0.018, headPitch: 0.045 }),
  surprised: Object.freeze({ surprised: 0.32, headPitch: -0.016 }),
  relaxed: Object.freeze({ relaxed: 0.22, headPitch: 0.008 }),
  neutral: Object.freeze({ relaxed: 0.025, headPitch: 0 }),
});

const DEFAULT_PROFILE = Object.freeze({
  expressionScale: 0.9,
  speakingScale: 0.78,
  actionScale: 0.94,
  transitionSpeed: 4.8,
  actionResponse: 6.2,
  headResponse: 4.8,
});

const AVATAR_EXPRESSION_PROFILES = Object.freeze({
  monk: Object.freeze({ ...DEFAULT_PROFILE, expressionScale: 0.86, speakingScale: 0.76, actionScale: 0.9 }),
  hanfu: Object.freeze({ ...DEFAULT_PROFILE, expressionScale: 0.8, speakingScale: 0.74, actionScale: 0.88, transitionSpeed: 4.5 }),
  modern: Object.freeze({ ...DEFAULT_PROFILE, expressionScale: 0.96, speakingScale: 0.8, actionScale: 0.98, actionResponse: 6.6 }),
});

const FACE_EXPRESSIONS = Object.freeze([
  "happy", "angry", "sad", "relaxed", "surprised", "neutral",
]);

function frame(t, influence, expressions) {
  return Object.freeze({ t, influence, ...expressions });
}

function timeline(expressions, attack = 0.18, release = 0.78) {
  return Object.freeze([
    frame(0, 0, expressions),
    frame(attack, 1, expressions),
    frame(release, 1, expressions),
    frame(1, 0, expressions),
  ]);
}

// Facial intent for every registered body action. Values are deliberately
// restrained; the envelope keeps the face synchronized with body attack/release.
const ACTION_EXPRESSION_TIMELINES = Object.freeze({
  lean_in: timeline({ relaxed: 0.12, surprised: 0.04 }, 0.22, 0.8),
  guide_narrate: timeline({ happy: 0.11, relaxed: 0.1 }),
  welcome_invite: timeline({ happy: 0.34, relaxed: 0.09 }, 0.2, 0.8),
  departure_pose: timeline({ happy: 0.23, surprised: 0.07 }, 0.24, 0.72),
  two_hand_wave: timeline({ happy: 0.42, relaxed: 0.06 }, 0.14, 0.82),
  wave: timeline({ happy: 0.36, relaxed: 0.06 }, 0.15, 0.8),
  farewell: Object.freeze([
    frame(0, 0, { happy: 0.3, sad: 0.02, relaxed: 0.04 }),
    frame(0.18, 1, { happy: 0.3, sad: 0.02, relaxed: 0.04 }),
    frame(0.62, 1, { happy: 0.25, sad: 0.05, relaxed: 0.04 }),
    frame(0.84, 0.9, { happy: 0.16, sad: 0.1, relaxed: 0.035 }),
    frame(1, 0, { happy: 0.14, sad: 0.1, relaxed: 0.03 }),
  ]),
  agree: timeline({ happy: 0.13, relaxed: 0.12 }, 0.2, 0.76),
  disagree: timeline({ sad: 0.13, surprised: 0.025, relaxed: 0.025 }, 0.18, 0.78),
  point_back: timeline({ happy: 0.08, surprised: 0.1, relaxed: 0.06 }),
  think: timeline({ relaxed: 0.14, surprised: 0.07 }, 0.25, 0.78),
  encourage: timeline({ happy: 0.28, relaxed: 0.06 }, 0.16, 0.82),
  praise: timeline({ happy: 0.38, relaxed: 0.05 }, 0.16, 0.82),
  applaud: timeline({ happy: 0.4, relaxed: 0.055 }, 0.14, 0.84),
  applaud_hanfu: timeline({ happy: 0.4, relaxed: 0.055 }, 0.14, 0.84),
  applaud_modern: timeline({ happy: 0.4, relaxed: 0.055 }, 0.14, 0.84),
  applaud_monk: timeline({ happy: 0.4, relaxed: 0.055 }, 0.14, 0.84),
  celebrate: timeline({ happy: 0.48, surprised: 0.1 }, 0.12, 0.86),
  look_around: timeline({ happy: 0.06, relaxed: 0.08, surprised: 0.1 }, 0.22, 0.82),
  think_observe: timeline({ relaxed: 0.12, surprised: 0.09 }, 0.24, 0.8),
  speaking_nod: timeline({ happy: 0.1, relaxed: 0.1 }, 0.2, 0.78),
  speaking_point: timeline({ happy: 0.07, relaxed: 0.06, surprised: 0.07 }, 0.18, 0.8),
  speaking_disagree: timeline({ sad: 0.11, relaxed: 0.05 }, 0.2, 0.78),
  speaking_observe: timeline({ happy: 0.05, relaxed: 0.08, surprised: 0.09 }, 0.22, 0.82),
  narrate_open: timeline({ happy: 0.12, relaxed: 0.09 }, 0.2, 0.8),
  narrate_present: timeline({ happy: 0.1, relaxed: 0.1 }, 0.2, 0.8),
  narrate_emphasis: timeline({ happy: 0.07, relaxed: 0.08 }, 0.18, 0.78),
  narrate_count: timeline({ happy: 0.09, relaxed: 0.09 }, 0.2, 0.8),
  greet_wave_soft: timeline({ happy: 0.3, relaxed: 0.07 }, 0.16, 0.8),
  greet_palm: timeline({ happy: 0.22, relaxed: 0.08 }, 0.18, 0.8),
  greet_bow: timeline({ happy: 0.18, relaxed: 0.06 }, 0.24, 0.78),
  greet_both_low: timeline({ happy: 0.26, relaxed: 0.08 }, 0.2, 0.8),
  greet_nod: timeline({ happy: 0.2, relaxed: 0.08 }, 0.18, 0.78),
  greet_hands_together: timeline({ happy: 0.16, relaxed: 0.06 }, 0.22, 0.8),
  open_goodbye: timeline({ happy: 0.25, sad: 0.03, relaxed: 0.05 }, 0.18, 0.82),
  ningling_farewell: timeline({ happy: 0.18, relaxed: 0.08 }, 0.18, 0.82),
  qinglan_farewell: timeline({ happy: 0.16, relaxed: 0.06 }, 0.18, 0.82),
  qinglan_farewell_wave_candidate: timeline({ happy: 0.18, relaxed: 0.05 }, 0.2, 0.8),
  ningling_farewell_wave_candidate: timeline({ happy: 0.18, relaxed: 0.05 }, 0.2, 0.8),
  ningling_wave_draft: timeline({ happy: 0.22, relaxed: 0.05 }, 0.2, 0.78),
  open_thinking: timeline({ relaxed: 0.1, surprised: 0.05 }, 0.24, 0.8),
  open_relax: timeline({ relaxed: 0.18 }, 0.24, 0.82),
  open_lookaround: timeline({ happy: 0.06, surprised: 0.08, relaxed: 0.08 }, 0.22, 0.82),
});

function smoothstep(value) {
  const t = Math.max(0, Math.min(1, value));
  return t * t * (3 - 2 * t);
}

function interpolateTimeline(keys, progress) {
  const t = Math.max(0, Math.min(1, Number(progress) || 0));
  let index = 0;
  while (index < keys.length - 2 && t > keys[index + 1].t) index += 1;
  const from = keys[index];
  const to = keys[Math.min(index + 1, keys.length - 1)];
  const local = smoothstep((t - from.t) / Math.max(to.t - from.t, 0.0001));
  const result = { influence: from.influence + (to.influence - from.influence) * local };
  FACE_EXPRESSIONS.forEach((name) => {
    result[name] = (from[name] || 0) + ((to[name] || 0) - (from[name] || 0)) * local;
  });
  return result;
}

export function getAvatarExpressionProfile(preset) {
  return AVATAR_EXPRESSION_PROFILES[preset] || DEFAULT_PROFILE;
}

export function getAvatarExpressionTargets(state) {
  return EXPRESSION_TARGETS[state] || EXPRESSION_TARGETS.neutral;
}

// Character drafts keep their own names, but share the facial intent of the
// corresponding gesture. This only selects face curves, never body motion.
function expressionTimelineForAction(actionName) {
  const direct = ACTION_EXPRESSION_TIMELINES[actionName];
  if (direct) return direct;
  const match = /^(qinglan|jingxing|ningling)_(.+)$/.exec(actionName || "");
  if (!match) return null;
  const aliases = {
    exhibit_draft: "narrate_emphasis", remind_draft: "speaking_nod",
    think_draft: "think", narrate_emphasis_draft: "narrate_emphasis",
    greet_wave_soft_draft: "greet_wave_soft", greet_bow_draft: "greet_bow",
    clap_draft: "applaud", cupped_greeting: "greet_hands_together",
    wave_draft: "ningling_wave_draft",
    farewell_wave_candidate: "ningling_farewell_wave_candidate",
    salute_greeting: "greet_bow",
    bow_farewell: "qinglan_farewell",
  };
  return ACTION_EXPRESSION_TIMELINES[aliases[match[2]]] || null;
}

export function getAvatarActionExpressionTargets(actionName, progress) {
  const keys = expressionTimelineForAction(actionName);
  return keys ? interpolateTimeline(keys, progress) : null;
}

export function hasAvatarActionExpression(actionName) {
  return Boolean(expressionTimelineForAction(actionName));
}
