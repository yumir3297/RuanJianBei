/**
 * 数字人离散动作目录。
 *
 * 触发分为两层：
 * 1. stateTrigger：由 listening / thinking / speaking 等页面状态自动触发；
 * 2. explicit：由具体业务场景通过 action 字段触发，优先级高于自动动作。
 *
 * cooldownMs 用来防止连续回答时反复做同一个动作；priority 用来解决动作冲突。
 */
const KEYFRAME_ACTIONS = {
  lean_in: {
    label: "侧耳倾听",
    kind: "keyframes",
    durationMs: 3200,
    blendInMs: 520,
    blendOutMs: 740,
    priority: 30,
    cooldownMs: 6500,
    keyframes: [
      { t: 0.0, head_x: 0, head_y: 0, head_z: 0, neck_z: 0, chest_x: 0, chest_z: 0, spine_z: 0, rs_z: 0, ls_z: 0 },
      { t: 0.1, head_x: 0.014, head_y: 0.004, head_z: -0.008, neck_z: -0.005, chest_x: 0.007, chest_z: -0.002, spine_z: -0.003, rs_z: -0.01, ls_z: 0.008 },
      { t: 0.26, head_x: -0.045, head_y: 0.02, head_z: 0.095, neck_z: 0.048, chest_x: -0.02, chest_z: 0.008, spine_z: 0.013, rs_z: 0.031, ls_z: -0.021 },
      { t: 0.38, head_x: -0.07, head_y: 0.03, head_z: 0.158, neck_z: 0.062, chest_x: -0.03, chest_z: 0.013, spine_z: 0.018, rs_z: 0.042, ls_z: -0.029 },
      { t: 0.48, head_x: -0.055, head_y: 0.025, head_z: 0.14, neck_z: 0.055, chest_x: -0.025, chest_z: 0.011, spine_z: 0.015, rs_z: 0.037, ls_z: -0.025 },
      { t: 0.58, head_x: -0.072, head_y: 0.032, head_z: 0.16, neck_z: 0.063, chest_x: -0.031, chest_z: 0.0135, spine_z: 0.0185, rs_z: 0.043, ls_z: -0.03 },
      { t: 0.7, head_x: -0.042, head_y: 0.019, head_z: 0.1, neck_z: 0.04, chest_x: -0.016, chest_z: 0.007, spine_z: 0.01, rs_z: 0.025, ls_z: -0.017 },
      { t: 0.82, head_x: -0.02, head_y: 0.009, head_z: 0.045, neck_z: 0.018, chest_x: -0.007, chest_z: 0.003, spine_z: 0.004, rs_z: 0.012, ls_z: -0.008 },
      { t: 0.92, head_x: -0.005, head_y: 0.002, head_z: 0.01, neck_z: 0.004, chest_x: -0.002, chest_z: 0.001, spine_z: 0.001, rs_z: 0.003, ls_z: -0.002 },
      { t: 1.0, head_x: 0, head_y: 0, head_z: 0, neck_z: 0, chest_x: 0, chest_z: 0, spine_z: 0, rs_z: 0, ls_z: 0 },
    ],
  },
  guide_narrate: {
    label: "导览讲解",
    kind: "keyframes",
    durationMs: 3400,
    blendInMs: 520,
    blendOutMs: 740,
    priority: 35,
    cooldownMs: 12000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 0.9, rla_y: 0, rla_z: 0, rh_z: 0, head_y: 0, chest_y: 0, spine_y: 0, rs_z: 0 },
      { t: 0.1, rua_y: 0.03, rua_z: 0.88, rla_y: 0.01, rla_z: 0.01, rh_z: 0.005, head_y: 0.004, chest_y: 0.003, spine_y: 0.001, rs_z: 0.008 },
      { t: 0.28, rua_y: 0.32, rua_z: 0.66, rla_y: 0.12, rla_z: 0.03, rh_z: -0.04, head_y: 0.04, chest_y: 0.022, spine_y: 0.009, rs_z: 0.04 },
      { t: 0.42, rua_y: 0.45, rua_z: 0.56, rla_y: 0.3, rla_z: -0.02, rh_z: -0.1, head_y: 0.07, chest_y: 0.04, spine_y: 0.018, rs_z: 0.068 },
      { t: 0.54, rua_y: 0.41, rua_z: 0.6, rla_y: 0.33, rla_z: -0.07, rh_z: -0.14, head_y: 0.058, chest_y: 0.036, spine_y: 0.016, rs_z: 0.062 },
      { t: 0.66, rua_y: 0.43, rua_z: 0.58, rla_y: 0.29, rla_z: -0.04, rh_z: -0.09, head_y: 0.053, chest_y: 0.034, spine_y: 0.015, rs_z: 0.06 },
      { t: 0.8, rua_y: 0.18, rua_z: 0.78, rla_y: 0.1, rla_z: 0.02, rh_z: -0.025, head_y: 0.024, chest_y: 0.014, spine_y: 0.006, rs_z: 0.025 },
      { t: 0.9, rua_y: 0.04, rua_z: 0.87, rla_y: 0.02, rla_z: 0.008, rh_z: 0.004, head_y: 0.008, chest_y: 0.004, spine_y: 0.002, rs_z: 0.008 },
      { t: 1.0, rua_y: 0, rua_z: 0.9, rla_y: 0, rla_z: 0, rh_z: 0, head_y: 0, chest_y: 0, spine_y: 0, rs_z: 0 },
    ],
  },
  welcome_invite: {
    label: "侧身请进",
    kind: "keyframes",
    durationMs: 3600,
    blendInMs: 540,
    blendOutMs: 780,
    priority: 82,
    cooldownMs: 20000,
    keyframes: [
      { t: 0.0, head_x: 0, head_y: 0, head_z: 0, neck_y: 0, chest_y: 0, chest_z: 0, spine_y: 0, rua_y: 0, rua_z: 0.8, rla_y: 0, rla_z: 0, rh_z: 0, rs_z: 0, lua_y: 0, lua_z: -0.8, ls_z: 0, group_y: 0 },
      { t: 0.1, head_x: 0.01, head_y: 0.008, head_z: -0.004, chest_y: -0.004, rua_y: 0.025, rua_z: 0.78, rla_y: 0.008, lua_y: 0, lua_z: -0.78, group_y: 0.003 },
      { t: 0.26, head_x: -0.014, head_y: -0.03, head_z: -0.008, neck_y: -0.012, chest_y: -0.016, chest_z: 0.005, spine_y: -0.006, rua_y: -0.1, rua_z: 0.68, rla_y: -0.08, rla_z: -0.01, rh_z: -0.025, rs_z: 0.04, lua_y: 0.015, lua_z: -0.66, ls_z: -0.022, group_y: -0.02 },
      { t: 0.44, head_x: -0.028, head_y: -0.055, head_z: -0.014, neck_y: -0.018, chest_y: -0.026, chest_z: 0.009, spine_y: -0.011, rua_y: -0.2, rua_z: 0.56, rla_y: -0.175, rla_z: -0.018, rh_z: -0.05, rs_z: 0.06, lua_y: 0.025, lua_z: -0.56, ls_z: -0.035, group_y: -0.032 },
      { t: 0.58, head_x: -0.022, head_y: -0.052, head_z: -0.012, neck_y: -0.016, chest_y: -0.024, chest_z: 0.008, spine_y: -0.01, rua_y: -0.195, rua_z: 0.58, rla_y: -0.17, rla_z: -0.016, rh_z: -0.047, rs_z: 0.058, lua_y: 0.023, lua_z: -0.57, ls_z: -0.033, group_y: -0.031 },
      { t: 0.7, head_x: -0.018, head_y: -0.045, head_z: -0.01, neck_y: -0.013, chest_y: -0.021, chest_z: 0.007, spine_y: -0.008, rua_y: -0.18, rua_z: 0.6, rla_y: -0.16, rla_z: -0.012, rh_z: -0.04, rs_z: 0.052, lua_y: 0.021, lua_z: -0.6, ls_z: -0.03, group_y: -0.028 },
      { t: 0.82, head_x: -0.008, head_y: -0.026, head_z: -0.005, neck_y: -0.007, chest_y: -0.012, chest_z: 0.004, spine_y: -0.004, rua_y: -0.09, rua_z: 0.7, rla_y: -0.08, rla_z: 0, rh_z: -0.018, rs_z: 0.028, lua_y: 0.012, lua_z: -0.7, ls_z: -0.017, group_y: -0.015 },
      { t: 0.92, head_x: -0.002, head_y: -0.008, head_z: -0.001, neck_y: -0.002, chest_y: -0.003, chest_z: 0.001, spine_y: -0.001, rua_y: -0.02, rua_z: 0.78, rla_y: -0.018, rh_z: -0.004, rs_z: 0.008, lua_y: 0.003, lua_z: -0.78, ls_z: -0.004, group_y: -0.004 },
      { t: 1.0, head_x: 0, head_y: 0, head_z: 0, neck_y: 0, chest_y: 0, chest_z: 0, spine_y: 0, rua_y: 0, rua_z: 0.8, rla_y: 0, rla_z: 0, rh_z: 0, rs_z: 0, lua_y: 0, lua_z: -0.8, ls_z: 0, group_y: 0 },
    ],
  },
  departure_pose: {
    label: "准备出发",
    kind: "keyframes",
    durationMs: 3400,
    blendInMs: 520,
    blendOutMs: 780,
    priority: 85,
    cooldownMs: 10000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 0.9, rla_x: 0, rla_y: 0, rh_z: 0, lua_y: 0, lua_z: -0.9, lla_x: 0, head_x: 0, head_y: 0, chest_y: 0, spine_y: 0, rs_z: 0, group_y: 0 },
      { t: 0.12, rua_y: -0.05, rua_z: 0.86, rla_x: 0.08, rla_y: 0.02, rh_z: 0.01, lua_y: 0, lua_z: -0.86, lla_x: 0.04, head_x: 0.01, head_y: -0.008, chest_y: -0.005, spine_y: -0.002, rs_z: -0.008, group_y: 0.004 },
      { t: 0.3, rua_y: 0.55, rua_z: 0.68, rla_x: -0.45, rla_y: 0.1, rh_z: -0.05, lua_y: 0.015, lua_z: -0.72, lla_x: -0.4, head_x: -0.03, head_y: 0.03, chest_y: 0.015, spine_y: 0.008, rs_z: 0.05, group_y: -0.01 },
      { t: 0.46, rua_y: 0.9, rua_z: 0.58, rla_x: -1.1, rla_y: 0.2, rh_z: -0.1, lua_y: 0.025, lua_z: -0.62, lla_x: -0.9, head_x: -0.05, head_y: 0.045, chest_y: 0.03, spine_y: 0.015, rs_z: 0.08, group_y: -0.02 },
      { t: 0.58, rua_y: 1.0, rua_z: 0.54, rla_x: -1.42, rla_y: 0.24, rh_z: -0.13, lua_y: 0.03, lua_z: -0.58, lla_x: -1.02, head_x: -0.06, head_y: 0.05, chest_y: 0.035, spine_y: 0.018, rs_z: 0.09, group_y: -0.024 },
      { t: 0.68, rua_y: 0.96, rua_z: 0.56, rla_x: -1.35, rla_y: 0.22, rh_z: -0.11, lua_y: 0.028, lua_z: -0.6, lla_x: -0.98, head_x: -0.055, head_y: 0.046, chest_y: 0.032, spine_y: 0.017, rs_z: 0.085, group_y: -0.022 },
      { t: 0.8, rua_y: 0.6, rua_z: 0.7, rla_x: -0.7, rla_y: 0.13, rh_z: -0.06, lua_y: 0.018, lua_z: -0.72, lla_x: -0.52, head_x: -0.032, head_y: 0.026, chest_y: 0.017, spine_y: 0.009, rs_z: 0.052, group_y: -0.012 },
      { t: 0.9, rua_y: 0.2, rua_z: 0.85, rla_x: -0.2, rla_y: 0.04, rh_z: -0.015, lua_y: 0.006, lua_z: -0.85, lla_x: -0.15, head_x: -0.01, head_y: 0.008, chest_y: 0.005, spine_y: 0.003, rs_z: 0.018, group_y: -0.004 },
      { t: 1.0, rua_y: 0, rua_z: 0.9, rla_x: 0, rla_y: 0, rh_z: 0, lua_y: 0, lua_z: -0.9, lla_x: 0, head_x: 0, head_y: 0, chest_y: 0, spine_y: 0, rs_z: 0, group_y: 0 },
    ],
  },
  narrate_open: {
    label: "讲解·展开",
    kind: "keyframes",
    durationMs: 3400,
    blendInMs: 540,
    blendOutMs: 780,
    priority: 38,
    cooldownMs: 14000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, lua_y: 0, lua_z: -1.18, lla_y: 0, lla_z: 0, chest_x: 0, chest_y: 0, head_x: 0, head_y: 0, rs_z: 0, ls_z: 0, group_y: 0 },
      { t: 0.14, rua_y: -0.02, rua_z: 1.12, rla_y: 0.02, lua_y: 0.02, lua_z: -1.12, lla_y: 0.02, chest_y: -0.006, head_x: 0.008, head_y: 0.004, group_y: 0.003 },
      { t: 0.34, rua_y: 0.12, rua_z: 0.84, rla_y: 0.16, rla_z: 0.04, rh_z: -0.03, lua_y: -0.12, lua_z: -0.84, lla_y: 0.16, lla_z: -0.03, chest_x: -0.004, chest_y: 0.018, head_x: -0.012, head_y: 0.025, rs_z: 0.03, ls_z: -0.03, group_y: -0.008 },
      { t: 0.48, rua_y: 0.18, rua_z: 0.76, rla_y: 0.26, rla_z: 0.02, rh_z: -0.05, lua_y: -0.18, lua_z: -0.76, lla_y: 0.26, lla_z: -0.02, chest_x: -0.006, chest_y: 0.028, head_x: -0.016, head_y: 0.04, rs_z: 0.045, ls_z: -0.045, group_y: -0.012 },
      { t: 0.62, rua_y: 0.175, rua_z: 0.78, rla_y: 0.25, rla_z: 0.02, rh_z: -0.045, lua_y: -0.175, lua_z: -0.78, lla_y: 0.25, lla_z: -0.02, chest_x: -0.005, chest_y: 0.026, head_x: -0.014, head_y: 0.038, rs_z: 0.042, ls_z: -0.042, group_y: -0.011 },
      { t: 0.76, rua_y: 0.1, rua_z: 0.92, rla_y: 0.14, rla_z: 0.01, rh_z: -0.02, lua_y: -0.1, lua_z: -0.92, lla_y: 0.14, lla_z: -0.01, chest_x: -0.002, chest_y: 0.014, head_x: -0.006, head_y: 0.02, rs_z: 0.02, ls_z: -0.02, group_y: -0.005 },
      { t: 0.9, rua_y: 0.03, rua_z: 1.08, rla_y: 0.04, rh_z: -0.005, lua_y: -0.03, lua_z: -1.08, lla_y: 0.04, chest_y: 0.004, head_x: -0.001, head_y: 0.006, group_y: -0.001 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, lua_y: 0, lua_z: -1.18, lla_y: 0, lla_z: 0, chest_x: 0, chest_y: 0, head_x: 0, head_y: 0, rs_z: 0, ls_z: 0, group_y: 0 },
    ],
  },
  narrate_present: {
    label: "讲解·引导",
    kind: "keyframes",
    durationMs: 3200,
    blendInMs: 520,
    blendOutMs: 760,
    priority: 37,
    cooldownMs: 11000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, chest_y: 0, head_x: 0, head_y: 0, rs_z: 0, group_y: 0 },
      { t: 0.1, rua_y: -0.02, rua_z: 1.1, rla_y: 0.02, rla_z: 0, rh_z: 0.005, chest_y: -0.004, head_x: 0.008, head_y: 0.004, rs_z: -0.008, group_y: 0.002 },
      { t: 0.3, rua_y: 0.15, rua_z: 0.6, rla_y: 0.4, rla_z: 0.1, rh_z: -0.05, chest_y: 0.02, head_x: -0.01, head_y: 0.045, rs_z: 0.04, group_y: -0.006 },
      { t: 0.45, rua_y: 0.22, rua_z: 0.52, rla_y: 0.55, rla_z: 0.06, rh_z: -0.08, chest_y: 0.03, head_x: -0.014, head_y: 0.065, rs_z: 0.06, group_y: -0.009 },
      { t: 0.58, rua_y: 0.2, rua_z: 0.55, rla_y: 0.52, rla_z: 0.07, rh_z: -0.07, chest_y: 0.028, head_x: -0.012, head_y: 0.06, rs_z: 0.055, group_y: -0.008 },
      { t: 0.72, rua_y: 0.12, rua_z: 0.78, rla_y: 0.3, rla_z: 0.04, rh_z: -0.03, chest_y: 0.015, head_x: -0.005, head_y: 0.03, rs_z: 0.03, group_y: -0.004 },
      { t: 0.86, rua_y: 0.04, rua_z: 1.02, rla_y: 0.1, rla_z: 0.01, rh_z: -0.005, chest_y: 0.005, head_x: -0.001, head_y: 0.01, rs_z: 0.008, group_y: -0.001 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, chest_y: 0, head_x: 0, head_y: 0, rs_z: 0, group_y: 0 },
    ],
  },
  narrate_emphasis: {
    label: "讲解·强调",
    kind: "keyframes",
    durationMs: 3000,
    blendInMs: 500,
    blendOutMs: 740,
    priority: 36,
    cooldownMs: 10000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, chest_x: 0, head_x: 0, head_y: 0, rs_z: 0, group_y: 0 },
      { t: 0.18, rua_y: 0.22, rua_z: 0.9, rla_y: 0.45, rla_z: 0, rh_z: -0.08, chest_x: -0.004, head_x: 0.006, head_y: 0.01, rs_z: 0.02, group_y: -0.003 },
      { t: 0.34, rua_y: 0.28, rua_z: 0.85, rla_y: 0.6, rla_z: 0, rh_z: -0.12, chest_x: -0.012, head_x: -0.022, head_y: 0.018, rs_z: 0.035, group_y: -0.006 },
      { t: 0.46, rua_y: 0.26, rua_z: 0.88, rla_y: 0.44, rla_z: 0, rh_z: -0.08, chest_x: -0.006, head_x: -0.008, head_y: 0.014, rs_z: 0.025, group_y: -0.004 },
      { t: 0.58, rua_y: 0.28, rua_z: 0.85, rla_y: 0.6, rla_z: 0, rh_z: -0.12, chest_x: -0.012, head_x: -0.024, head_y: 0.018, rs_z: 0.035, group_y: -0.006 },
      { t: 0.72, rua_y: 0.2, rua_z: 0.98, rla_y: 0.35, rla_z: 0, rh_z: -0.05, chest_x: -0.004, head_x: -0.006, head_y: 0.01, rs_z: 0.018, group_y: -0.003 },
      { t: 0.86, rua_y: 0.08, rua_z: 1.1, rla_y: 0.12, rla_z: 0, rh_z: -0.01, chest_x: -0.001, head_x: -0.002, head_y: 0.004, rs_z: 0.006, group_y: -0.001 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, chest_x: 0, head_x: 0, head_y: 0, rs_z: 0, group_y: 0 },
    ],
  },
  narrate_count: {
    label: "讲解·列举",
    kind: "keyframes",
    durationMs: 3200,
    blendInMs: 520,
    blendOutMs: 760,
    priority: 36,
    cooldownMs: 12000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, chest_x: 0, head_x: 0, head_y: 0, rs_z: 0, group_y: 0 },
      { t: 0.16, rua_y: 0.28, rua_z: 0.86, rla_y: 0.48, rla_z: 0, rh_z: -0.04, chest_x: -0.004, head_x: -0.006, head_y: 0.012, rs_z: 0.022, group_y: -0.003 },
      { t: 0.3, rua_y: 0.34, rua_z: 0.82, rla_y: 0.62, rla_z: 0, rh_z: -0.08, chest_x: -0.01, head_x: -0.02, head_y: 0.02, rs_z: 0.034, group_y: -0.006 },
      { t: 0.42, rua_y: 0.3, rua_z: 0.85, rla_y: 0.5, rla_z: 0, rh_z: -0.02, chest_x: -0.005, head_x: -0.006, head_y: 0.016, rs_z: 0.024, group_y: -0.004 },
      { t: 0.54, rua_y: 0.35, rua_z: 0.81, rla_y: 0.63, rla_z: 0, rh_z: -0.1, chest_x: -0.01, head_x: -0.022, head_y: 0.02, rs_z: 0.035, group_y: -0.006 },
      { t: 0.68, rua_y: 0.28, rua_z: 0.9, rla_y: 0.45, rla_z: 0, rh_z: -0.03, chest_x: -0.004, head_x: -0.008, head_y: 0.014, rs_z: 0.022, group_y: -0.003 },
      { t: 0.82, rua_y: 0.12, rua_z: 1.05, rla_y: 0.2, rla_z: 0, rh_z: 0, chest_x: -0.001, head_x: -0.002, head_y: 0.006, rs_z: 0.008, group_y: -0.001 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, chest_x: 0, head_x: 0, head_y: 0, rs_z: 0, group_y: 0 },
    ],
  },

  greet_wave_soft: {
    label: "轻挥手",
    kind: "keyframes",
    durationMs: 3000,
    blendInMs: 500,
    blendOutMs: 720,
    priority: 40,
    cooldownMs: 6000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, head_x: 0, head_y: 0, head_z: 0, chest_y: 0, rs_z: 0 },
      { t: 0.1, rua_y: 0.01, rua_z: 1.1, rla_y: 0.04, rh_z: 0.02, head_x: 0.005, head_y: 0.004, chest_y: 0.002, rs_z: 0.006 },
      { t: 0.3, rua_y: 0.08, rua_z: 0.5, rla_y: 0.7, rla_z: 0.05, rh_z: 0.1, head_x: -0.004, head_y: 0.03, head_z: 0.01, chest_y: 0.01, rs_z: 0.04 },
      { t: 0.42, rua_y: 0.09, rua_z: 0.42, rla_y: 0.85, rla_z: 0.06, rh_z: 0.18, head_x: -0.006, head_y: 0.035, head_z: 0.012, chest_y: 0.012, rs_z: 0.05 },
      { t: 0.5, rua_y: 0.09, rua_z: 0.43, rla_y: 0.8, rla_z: 0.06, rh_z: -0.12, head_x: -0.005, head_y: 0.032, head_z: -0.008, chest_y: 0.011, rs_z: 0.048 },
      { t: 0.58, rua_y: 0.09, rua_z: 0.42, rla_y: 0.85, rla_z: 0.06, rh_z: 0.16, head_x: -0.006, head_y: 0.035, head_z: 0.012, chest_y: 0.012, rs_z: 0.05 },
      { t: 0.66, rua_y: 0.08, rua_z: 0.44, rla_y: 0.8, rla_z: 0.06, rh_z: -0.1, head_x: -0.004, head_y: 0.03, head_z: -0.006, chest_y: 0.01, rs_z: 0.045 },
      { t: 0.74, rua_y: 0.06, rua_z: 0.62, rla_y: 0.5, rla_z: 0.03, rh_z: 0.04, head_x: -0.002, head_y: 0.02, head_z: 0.002, chest_y: 0.006, rs_z: 0.03 },
      { t: 0.86, rua_y: 0.02, rua_z: 1.0, rla_y: 0.12, rla_z: 0.01, rh_z: 0.008, head_y: 0.006, chest_y: 0.002, rs_z: 0.008 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, head_x: 0, head_y: 0, head_z: 0, chest_y: 0, rs_z: 0 },
    ],
  },
  greet_palm: {
    label: "抬手致意",
    kind: "keyframes",
    durationMs: 2800,
    blendInMs: 480,
    blendOutMs: 700,
    priority: 39,
    cooldownMs: 8000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, head_x: 0, head_y: 0, chest_y: 0, rs_z: 0 },
      { t: 0.16, rua_y: 0.04, rua_z: 1.05, rla_y: 0.08, rh_z: 0.01, head_x: 0.004, head_y: 0.005, chest_y: 0.002, rs_z: 0.008 },
      { t: 0.34, rua_y: 0.2, rua_z: 0.55, rla_y: 0.55, rla_z: 0.1, rh_z: -0.1, head_x: -0.01, head_y: 0.03, chest_y: 0.012, rs_z: 0.045 },
      { t: 0.5, rua_y: 0.2, rua_z: 0.55, rla_y: 0.55, rla_z: 0.1, rh_z: -0.1, head_x: -0.01, head_y: 0.03, chest_y: 0.012, rs_z: 0.045 },
      { t: 0.66, rua_y: 0.18, rua_z: 0.6, rla_y: 0.5, rla_z: 0.09, rh_z: -0.08, head_x: -0.008, head_y: 0.026, chest_y: 0.01, rs_z: 0.04 },
      { t: 0.82, rua_y: 0.08, rua_z: 0.9, rla_y: 0.2, rla_z: 0.03, rh_z: -0.02, head_x: -0.002, head_y: 0.01, chest_y: 0.003, rs_z: 0.015 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rh_z: 0, head_x: 0, head_y: 0, chest_y: 0, rs_z: 0 },
    ],
  },
  greet_bow: {
    label: "点头微鞠躬",
    kind: "keyframes",
    durationMs: 2600,
    blendInMs: 480,
    blendOutMs: 700,
    priority: 42,
    cooldownMs: 8000,
    keyframes: [
      { t: 0.0, chest_x: 0, spine_x: 0, head_x: 0, head_y: 0, group_y: 0 },
      { t: 0.14, chest_x: -0.012, spine_x: -0.005, head_x: -0.012, head_y: 0, group_y: 0.002 },
      { t: 0.34, chest_x: 0.1, spine_x: 0.04, head_x: 0.1, head_y: 0, group_y: -0.004 },
      { t: 0.52, chest_x: 0.11, spine_x: 0.045, head_x: 0.11, head_y: 0, group_y: -0.004 },
      { t: 0.7, chest_x: 0.05, spine_x: 0.02, head_x: 0.05, head_y: 0, group_y: -0.002 },
      { t: 0.85, chest_x: 0.012, spine_x: 0.005, head_x: 0.012, head_y: 0, group_y: 0 },
      { t: 1.0, chest_x: 0, spine_x: 0, head_x: 0, head_y: 0, group_y: 0 },
    ],
  },
  greet_both_low: {
    label: "双手低位欢迎",
    kind: "keyframes",
    durationMs: 3200,
    blendInMs: 520,
    blendOutMs: 760,
    priority: 41,
    cooldownMs: 12000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, lua_y: 0, lua_z: -1.18, lla_y: 0, chest_x: 0, chest_y: 0, head_x: 0, head_y: 0, rs_z: 0, ls_z: 0, group_y: 0 },
      { t: 0.16, rua_y: -0.02, rua_z: 1.1, rla_y: 0.02, lua_y: 0.02, lua_z: -1.1, lla_y: 0.02, chest_y: -0.004, head_x: 0.006, group_y: 0.002 },
      { t: 0.36, rua_y: 0.12, rua_z: 0.85, rla_y: 0.15, lua_y: -0.12, lua_z: -0.85, lla_y: 0.15, chest_x: 0.03, chest_y: 0.018, head_x: 0.03, head_y: 0.02, rs_z: 0.03, ls_z: -0.03, group_y: -0.006 },
      { t: 0.52, rua_y: 0.16, rua_z: 0.8, rla_y: 0.22, lua_y: -0.16, lua_z: -0.8, lla_y: 0.22, chest_x: 0.04, chest_y: 0.025, head_x: 0.04, head_y: 0.03, rs_z: 0.04, ls_z: -0.04, group_y: -0.008 },
      { t: 0.66, rua_y: 0.15, rua_z: 0.82, rla_y: 0.21, lua_y: -0.15, lua_z: -0.82, lla_y: 0.21, chest_x: 0.035, chest_y: 0.022, head_x: 0.035, head_y: 0.026, rs_z: 0.036, ls_z: -0.036, group_y: -0.007 },
      { t: 0.8, rua_y: 0.08, rua_z: 0.98, rla_y: 0.1, lua_y: -0.08, lua_z: -0.98, lla_y: 0.1, chest_x: 0.012, chest_y: 0.008, head_x: 0.012, head_y: 0.01, rs_z: 0.012, ls_z: -0.012, group_y: -0.002 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, lua_y: 0, lua_z: -1.18, lla_y: 0, chest_x: 0, chest_y: 0, head_x: 0, head_y: 0, rs_z: 0, ls_z: 0, group_y: 0 },
    ],
  },
  greet_nod: {
    label: "微笑点头",
    kind: "keyframes",
    durationMs: 2200,
    blendInMs: 420,
    blendOutMs: 620,
    priority: 38,
    cooldownMs: 5000,
    keyframes: [
      { t: 0.0, head_x: 0, head_y: 0, chest_x: 0, chest_y: 0 },
      { t: 0.18, head_x: 0.02, head_y: 0, chest_x: 0.004, chest_y: 0 },
      { t: 0.34, head_x: 0.095, head_y: 0.01, chest_x: 0.015, chest_y: 0.004 },
      { t: 0.48, head_x: 0.03, head_y: 0.004, chest_x: 0.005, chest_y: 0.001 },
      { t: 0.62, head_x: 0.075, head_y: 0.008, chest_x: 0.012, chest_y: 0.003 },
      { t: 0.78, head_x: 0.02, head_y: 0.002, chest_x: 0.004, chest_y: 0.001 },
      { t: 1.0, head_x: 0, head_y: 0, chest_x: 0, chest_y: 0 },
    ],
  },
  greet_hands_together: {
    label: "拱手礼（宽袖版）",
    kind: "keyframes",
    durationMs: 3400,
    blendInMs: 560,
    blendOutMs: 800,
    clampOvershoot: true,
    priority: 43,
    cooldownMs: 15000,
    keyframes: [
      { t: 0.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rs_z: 0, lua_y: 0, lua_z: -1.18, lla_y: 0, lla_z: 0, ls_x: 0, ls_y: 0, ls_z: 0, chest_x: 0, head_x: 0, group_y: 0 },
      { t: 0.14, rua_y: 0.1, rua_z: 1.05, rla_y: 0.08, rs_z: 0.01, lua_y: -0.1, lua_z: -1.05, lla_y: 0.08, ls_x: 0, ls_y: 0.2, ls_z: -0.01, chest_x: -0.005, head_x: -0.005, group_y: 0.002 },
      { t: 0.34, rua_y: 0.45, rua_z: 0.75, rla_y: 0.9, rla_z: 0, rs_z: 0.03, lua_y: -0.6, lua_z: -0.9, lla_y: 0.2, lla_z: 0, ls_x: -0.1, ls_y: 0.6, ls_z: -0.03, chest_x: 0.02, head_x: 0.02, group_y: -0.003 },
      { t: 0.55, rua_y: 0.55, rua_z: 0.65, rla_y: 1.2, rla_z: 0, rs_z: 0.045, lua_y: -1.449, lua_z: -0.707, lla_y: -0.606, lla_z: 0.288, ls_x: -0.365, ls_y: 1.117, ls_z: -0.255, chest_x: 0.07, head_x: 0.07, group_y: -0.006 },
      { t: 0.7, rua_y: 0.54, rua_z: 0.66, rla_y: 1.18, rla_z: 0, rs_z: 0.043, lua_y: -1.43, lua_z: -0.72, lla_y: -0.6, lla_z: 0.28, ls_x: -0.35, ls_y: 1.09, ls_z: -0.25, chest_x: 0.065, head_x: 0.065, group_y: -0.005 },
      { t: 0.84, rua_y: 0.3, rua_z: 0.9, rla_y: 0.6, rla_z: 0, rs_z: 0.02, lua_y: -0.7, lua_z: -0.95, lla_y: 0.1, lla_z: 0, ls_x: -0.15, ls_y: 0.6, ls_z: -0.03, chest_x: 0.025, head_x: 0.025, group_y: -0.002 },
      { t: 1.0, rua_y: 0, rua_z: 1.18, rla_y: 0, rla_z: 0, rs_z: 0, lua_y: 0, lua_z: -1.18, lla_y: 0, lla_z: 0, ls_x: 0, ls_y: 0, ls_z: 0, chest_x: 0, head_x: 0, group_y: 0 },
    ],
  },

};

const GLB_ACTIONS = {
  two_hand_wave: { label: "双手挥手欢迎", file: "双手挥手欢迎.glb", priority: 88, cooldownMs: 1200 },
  wave: { label: "热烈挥手欢迎", file: "热烈挥手欢迎.glb", durationMs: 2600, priority: 80, cooldownMs: 15000 },
  farewell: { label: "挥手告别", file: "挥手告别.glb", priority: 80, cooldownMs: 12000 },
  agree: { label: "点头同意", file: "同意.glb", priority: 70, cooldownMs: 5000 },
  disagree: { label: "摇头否定", file: "摇头摆手不.glb", priority: 72, cooldownMs: 6000 },
  point_back: { label: "指向身后", file: "指向身后.glb", priority: 74, cooldownMs: 7000 },
  think: { label: "思考", file: "思考.glb", priority: 25, cooldownMs: 7000 },
  encourage: { label: "握拳加油", file: "握拳加油.glb", priority: 76, cooldownMs: 8000 },
  praise: { label: "大拇指称赞", file: "站在大拇指你真棒.glb", priority: 78, cooldownMs: 8000 },
  celebrate: { label: "庆祝", file: "庆祝.glb", priority: 86, cooldownMs: 15000 },
  look_around: { label: "抬手观察风景", file: "抬手挡光看（风景）.glb", priority: 75, cooldownMs: 9000 },
  // 自动状态动作使用独立别名，避免消耗拍照识景等显式业务动作的冷却时间。
  think_observe: {
    label: "思考时观察环境",
    file: "抬手挡光看（风景）.glb",
    durationMs: 5600,
    priority: 26,
    cooldownMs: 15000,
  },
  speaking_nod: {
    label: "讲解时轻点头",
    file: "同意.glb",
    durationMs: 3600,
    priority: 34,
    cooldownMs: 10000,
  },
  speaking_point: {
    label: "讲解时指引方向",
    file: "指向身后.glb",
    durationMs: 3800,
    priority: 36,
    cooldownMs: 12000,
  },
  speaking_disagree: {
    label: "讲解时提示否定",
    file: "摇头摆手不.glb",
    durationMs: 4200,
    priority: 36,
    cooldownMs: 12000,
  },
  speaking_observe: {
    label: "讲解时观察景点",
    file: "抬手挡光看（风景）.glb",
    durationMs: 5600,
    priority: 35,
    cooldownMs: 15000,
  },
};

// .vrma 标准动作：VRM Animation 生态格式（VRMC_vrm_animation 1.0 规范）。
// 与 Mixamo 路径不同：官方加载器直接按 VRM 骨骼名组织轨道，无需重定向表。
// 之后从 VRoid Hub / BOOTH 下载任意 .vrma 放入 public/motions 即可按此方式接入。
const VRMA_ACTIONS = {
  qinglan_farewell_wave_candidate: {
    label: "清岚告别（袖口待修）",
    file: "qinglan_farewell_wave_candidate.vrma",
    durationMs: 3000,
    blendInMs: 400,
    blendOutMs: 550,
    priority: 82,
    cooldownMs: 8000,
  },
  ningling_farewell_wave_candidate: {
    label: "宁灵告别",
    file: "ningling_farewell_wave_candidate.vrma",
    durationMs: 3000,
    blendInMs: 400,
    blendOutMs: 550,
    priority: 82,
    cooldownMs: 8000,
  },
  qinglan_farewell: {
    label: "清岚·点头告别",
    file: "qinglan_farewell.vrma",
    durationMs: 2400,
    blendInMs: 400,
    blendOutMs: 550,
    priority: 82,
    cooldownMs: 12000,
  },
  ningling_wave_draft: {
    label: "宁灵问候",
    file: "ningling_wave_draft.vrma",
    durationMs: 3000,
    blendInMs: 400,
    blendOutMs: 550,
    priority: 80,
    cooldownMs: 8000,
  },
  ningling_farewell: {
    label: "宁灵·单手告别",
    file: "ningling_farewell.vrma",
    durationMs: 3958,
    blendInMs: 450,
    blendOutMs: 650,
    priority: 82,
    cooldownMs: 12000,
  },
  ningling_cupped_greeting: {
    label: "宁灵拱手",
    file: "ningling_cupped_greeting.vrma",
    durationMs: 3667,
    blendInMs: 450,
    blendOutMs: 650,
    priority: 80,
    cooldownMs: 8000,
  },
  cc0_idle: {
    label: "自然待机（CC0·预览）",
    file: "cc0_idle.vrma",
    durationMs: 2500,
    blendInMs: 500,
    blendOutMs: 650,
    priority: 30,
    cooldownMs: 5000,
  },
  cc0_talking: {
    label: "自然讲解（CC0·预览）",
    file: "cc0_talking.vrma",
    durationMs: 2933,
    blendInMs: 500,
    blendOutMs: 650,
    priority: 38,
    cooldownMs: 7000,
  },
  vrma_standard_greet: {
    label: "标准问候（VRMA）",
    file: "标准问候.vrma",
    priority: 84,
    cooldownMs: 2500,
  },
  applaud_hanfu: {
    label: "热烈鼓掌（清岚）",
    file: "applaud_qinglan_adjusted.vrma",
    durationMs: 3958,
    blendInMs: 560,
    blendOutMs: 800,
    priority: 84,
    cooldownMs: 12000,
  },
  applaud_modern: {
    label: "热烈鼓掌（景行）",
    file: "applaud_modern.vrma",
    durationMs: 3933,
    blendInMs: 300,
    blendOutMs: 420,
    priority: 84,
    cooldownMs: 12000,
  },
  applaud_monk: {
    label: "热烈鼓掌（宁灵）",
    file: "applaud_monk_adjusted.vrma",
    durationMs: 3958,
    blendInMs: 300,
    blendOutMs: 420,
    priority: 84,
    cooldownMs: 12000,
  },
  open_clapping: {
    label: "开源鼓掌（MIT）",
    file: "open_clapping.vrma",
    durationMs: 3933,
    blendInMs: 300,
    blendOutMs: 420,
    priority: 84,
    cooldownMs: 12000,
  },
  open_goodbye: {
    label: "开源挥手告别（MIT）",
    file: "open_goodbye.vrma",
    durationMs: 3933,
    blendInMs: 300,
    blendOutMs: 420,
    priority: 82,
    cooldownMs: 12000,
  },
  open_thinking: {
    label: "开源思考（MIT）",
    file: "open_thinking.vrma",
    durationMs: 3933,
    blendInMs: 300,
    blendOutMs: 420,
    priority: 30,
    cooldownMs: 9000,
  },
  open_relax: {
    label: "开源放松（MIT）",
    file: "open_relax.vrma",
    durationMs: 3933,
    blendInMs: 300,
    blendOutMs: 420,
    priority: 20,
    cooldownMs: 12000,
  },
  open_lookaround: {
    label: "开源环顾（MIT）",
    file: "open_lookaround.vrma",
    durationMs: 3933,
    blendInMs: 300,
    blendOutMs: 420,
    priority: 35,
    cooldownMs: 10000,
  },
};

// Character-owned drafts: keep source actions intact and never automatically
// substitute experimental retargets for approved common gestures.
const CHARACTER_DRAFT_ACTIONS = {};
for (const [prefix, label, scale] of [["qinglan", "清岚", 0.72], ["jingxing", "景行", 0.9]]) {
  for (const sourceName of ["narrate_emphasis", "greet_wave_soft", "greet_bow"]) {
    const source = KEYFRAME_ACTIONS[sourceName];
    CHARACTER_DRAFT_ACTIONS[`${prefix}_${sourceName}_draft`] = {
      ...source, label: `${label}·${source.label}`,
      keyframes: source.keyframes.map((frame) => Object.fromEntries(
        Object.entries(frame).map(([key, value]) => [key,
          key === "t" || key === "rua_z" || key === "lua_z" ? value : value * scale]),
      )),
    };
  }
  CHARACTER_DRAFT_ACTIONS[`${prefix}_think_draft`] = {
    ...GLB_ACTIONS.think, kind: "mixamo", label: `${label}·思考`,
    blendInMs: 550, blendOutMs: 700,
  };
  for (const [suffix, durationMs] of [["cupped_greeting", 3667], ["wave_draft", 3000],
    ["farewell_wave_candidate", 3000], ["clap_draft", 3958]]) {
    const gesture = {
      cupped_greeting: "拱手", wave_draft: "问候",
      farewell_wave_candidate: "告别", clap_draft: "鼓掌",
    }[suffix];
    CHARACTER_DRAFT_ACTIONS[`${prefix}_${suffix}`] = {
      kind: "vrma", file: `${prefix}_${suffix}.vrma`, label: `${label}·${gesture}`,
      durationMs, blendInMs: 450, blendOutMs: 650, priority: 80, cooldownMs: 8000,
    };
  }
}

// Qinglan keeps the cupped greeting plus three low-arm Hanfu gestures. The old
// wave/farewell retargets stay archived: their cuffs folded on raised arms.
for (const name of Object.keys(CHARACTER_DRAFT_ACTIONS)) {
  if (name.startsWith("qinglan_") && ![
    "qinglan_cupped_greeting", "qinglan_salute_greeting",
    "qinglan_bow_farewell", "qinglan_exhibit_draft",
  ].includes(name)) {
    delete CHARACTER_DRAFT_ACTIONS[name];
  }
  // Keep the original common gestures rather than exposing duplicate trials.
  if (name.startsWith("jingxing_") && ![
    "jingxing_cupped_greeting", "jingxing_wave_draft", "jingxing_farewell_wave_candidate",
  ].includes(name)) {
    delete CHARACTER_DRAFT_ACTIONS[name];
  }
}

// Utility gestures are new manual previews, not replacements for removed trials.
for (const [prefix, label] of [["jingxing", "景行"], ["ningling", "宁灵"]]) {
  for (const [suffix, gesture] of [["exhibit_draft", "单手引景"], ["remind_draft", "温和提醒"]]) {
    CHARACTER_DRAFT_ACTIONS[`${prefix}_${suffix}`] = {
      kind: "vrma", file: `${prefix}_${suffix}.vrma`, label: `${label}·${gesture}`,
      durationMs: 3000, blendInMs: 450, blendOutMs: 650, priority: 75, cooldownMs: 8000,
    };
  }
}
// Qinglan gets only the low exhibit gesture; her wide cuffs stay below the chest.
CHARACTER_DRAFT_ACTIONS.qinglan_exhibit_draft = {
  kind: "vrma", file: "qinglan_exhibit_draft.vrma", label: "清岚·单手引景",
  durationMs: 3000, blendInMs: 450, blendOutMs: 650, priority: 75, cooldownMs: 8000,
};

// Hanfu-appropriate ceremonial gestures authored on Qinglan's own rig.
for (const [suffix, label, durationMs] of [
  ["salute_greeting", "清岚·问候", 3367],
  ["bow_farewell", "清岚·欠身告别", 3033],
]) {
  CHARACTER_DRAFT_ACTIONS[`qinglan_${suffix}`] = {
    kind: "vrma", file: `qinglan_${suffix}.vrma`, label,
    durationMs, blendInMs: 450, blendOutMs: 700, priority: 80, cooldownMs: 8000,
  };
}

// Archived definitions remain above for comparison; only this shortlist is active.
export const ACTIVE_AVATAR_ACTION_NAMES = Object.freeze([
  "think", "narrate_emphasis",
  "greet_wave_soft", "greet_bow",
  "applaud_hanfu", "applaud_modern", "applaud_monk",
  "ningling_cupped_greeting",
  "ningling_farewell_wave_candidate",
  "ningling_wave_draft",
  ...Object.keys(CHARACTER_DRAFT_ACTIONS),
]);
const ACTIVE_ACTION_SET = new Set(ACTIVE_AVATAR_ACTION_NAMES);
export const AVATAR_ACTIONS = Object.freeze(Object.fromEntries(Object.entries({
  ...Object.fromEntries(Object.entries(KEYFRAME_ACTIONS).map(([name, item]) => [name, Object.freeze({ name, ...item })])),
  ...Object.fromEntries(Object.entries(GLB_ACTIONS).map(([name, item]) => [name, Object.freeze({
    name,
    kind: "mixamo",
    blendInMs: 360,
    blendOutMs: 520,
    maxDurationMs: 6500,
    ...item,
  })])),
  ...Object.fromEntries(Object.entries(VRMA_ACTIONS).map(([name, item]) => [name, Object.freeze({
    name,
    kind: "vrma",
    blendInMs: 360,
    blendOutMs: 520,
    maxDurationMs: 6500,
    ...item,
  })])),
  ...Object.fromEntries(Object.entries(CHARACTER_DRAFT_ACTIONS).map(([name, item]) => [name, Object.freeze({ name, ...item })])),
}).filter(([name]) => ACTIVE_ACTION_SET.has(name))));

export const AVATAR_STATE_ACTIONS = Object.freeze({
  thinking: Object.freeze({
    actions: Object.freeze([
      Object.freeze({ action: "think", weight: 100 }),
    ]),
    delayMs: 800,
  }),
});

// 精简为轻挥手、微鞠躬、传统拱手。
export const GREETING_ACTIONS = Object.freeze([
  "greet_wave_soft",
  "greet_bow",
]);
let greetingCursor = 0;
let greetingCursorLoaded = false;
const GREETING_CURSOR_KEY = "a5-greeting-cursor";

export function selectGreetingAction() {
  if (!greetingCursorLoaded) {
    greetingCursorLoaded = true;
    try {
      const saved = Number(window.localStorage.getItem(GREETING_CURSOR_KEY));
      if (Number.isFinite(saved) && saved >= 0) greetingCursor = saved;
    } catch {
      // localStorage unavailable (private mode / tests) — use in-memory cursor.
    }
  }
  const action = GREETING_ACTIONS[greetingCursor % GREETING_ACTIONS.length];
  greetingCursor += 1;
  try {
    window.localStorage.setItem(GREETING_CURSOR_KEY, String(greetingCursor));
  } catch {
    // ignore
  }
  return action;
}

const GREETING_TEXT_PATTERN = /^(你好|您好|嗨|哈喽|哈啰|hello|hi|hey|早上好|上午好|下午好|晚上好|早安|晚安)/i;
const FAREWELL_TEXT_PATTERN = /^(再见|拜拜|告辞|下次见|回头见|bye|goodbye|see you)/i;

export function isGreetingText(text) {
  return GREETING_TEXT_PATTERN.test(String(text || "").trim());
}

export function isFarewellText(text) {
  return FAREWELL_TEXT_PATTERN.test(String(text || "").trim());
}

const NEGATIVE_SPEECH_PATTERN = /不能|不可以|禁止|不允许|无法|没有检索到|证据不足|暂不|请勿|不要|抱歉/;

// 只保留强调；已下架的引导手势不参与自动讲解。
const NARRATION_GESTURES = Object.freeze([
  "narrate_emphasis",
]);
let narrationGestureCursor = 0;

/**
 * 在句子开始时选择一次低频讲解手势。
 * 否定语义不做手势；普通讲解低频使用强调。
 */
export function selectSpeakingAction(text, randomValue = Math.random()) {
  const sentence = typeof text === "string" ? text.trim() : "";
  if (!sentence) return "";
  if (NEGATIVE_SPEECH_PATTERN.test(sentence)) return "";
  if (randomValue < 0.48) {
    const action = NARRATION_GESTURES[narrationGestureCursor % NARRATION_GESTURES.length];
    narrationGestureCursor += 1;
    return action;
  }
  return "";
}

export const ACTION_BONE_MAP = Object.freeze({
  rua_x: "rightUpperArm", rua_y: "rightUpperArm", rua_z: "rightUpperArm",
  lua_x: "leftUpperArm", lua_y: "leftUpperArm", lua_z: "leftUpperArm",
  rla_x: "rightLowerArm", rla_y: "rightLowerArm", rla_z: "rightLowerArm",
  lla_x: "leftLowerArm", lla_y: "leftLowerArm", lla_z: "leftLowerArm",
  rh_x: "rightHand", rh_y: "rightHand", rh_z: "rightHand",
  lh_x: "leftHand", lh_y: "leftHand", lh_z: "leftHand",
  head_x: "head", head_y: "head", head_z: "head",
  neck_x: "neck", neck_y: "neck", neck_z: "neck",
  chest_x: "chest", chest_y: "chest", chest_z: "chest",
  spine_x: "spine", spine_y: "spine", spine_z: "spine",
  rs_x: "rightShoulder", rs_y: "rightShoulder", rs_z: "rightShoulder",
  ls_x: "leftShoulder", ls_y: "leftShoulder", ls_z: "leftShoulder",
  group_y: "__group_y",
});

export const MIXAMO_TO_VRM_BONES = Object.freeze({
  Spine: "spine", Spine1: "chest", Spine2: "upperChest",
  LeftArm: "leftUpperArm", LeftForeArm: "leftLowerArm", LeftHand: "leftHand",
  RightArm: "rightUpperArm", RightForeArm: "rightLowerArm", RightHand: "rightHand",
  Head: "head", Neck: "neck", LeftShoulder: "leftShoulder", RightShoulder: "rightShoulder",
  LeftHandThumb1: "leftThumbMetacarpal", LeftHandThumb2: "leftThumbProximal", LeftHandThumb3: "leftThumbDistal",
  LeftHandIndex1: "leftIndexProximal", LeftHandIndex2: "leftIndexIntermediate", LeftHandIndex3: "leftIndexDistal",
  LeftHandMiddle1: "leftMiddleProximal", LeftHandMiddle2: "leftMiddleIntermediate", LeftHandMiddle3: "leftMiddleDistal",
  LeftHandRing1: "leftRingProximal", LeftHandRing2: "leftRingIntermediate", LeftHandRing3: "leftRingDistal",
  LeftHandPinky1: "leftLittleProximal", LeftHandPinky2: "leftLittleIntermediate", LeftHandPinky3: "leftLittleDistal",
  RightHandThumb1: "rightThumbMetacarpal", RightHandThumb2: "rightThumbProximal", RightHandThumb3: "rightThumbDistal",
  RightHandIndex1: "rightIndexProximal", RightHandIndex2: "rightIndexIntermediate", RightHandIndex3: "rightIndexDistal",
  RightHandMiddle1: "rightMiddleProximal", RightHandMiddle2: "rightMiddleIntermediate", RightHandMiddle3: "rightMiddleDistal",
  RightHandRing1: "rightRingProximal", RightHandRing2: "rightRingIntermediate", RightHandRing3: "rightRingDistal",
  RightHandPinky1: "rightLittleProximal", RightHandPinky2: "rightLittleIntermediate", RightHandPinky3: "rightLittleDistal",
});

export function getAvatarAction(name) {
  return AVATAR_ACTIONS[name] || null;
}

export function getStateAction(state) {
  return AVATAR_STATE_ACTIONS[state] || null;
}
