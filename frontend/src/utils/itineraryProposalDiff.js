const constraintLabels = {
  companions: "同行人",
  available_minutes: "可用时间",
  interests: "兴趣",
  required_spots: "必去景点",
  excluded_spots: "排除景点",
  unresolved_required_names: "待核对必去地点",
  unresolved_excluded_names: "待核对排除地点",
  walking_preference: "步行偏好",
  rest_every_minutes: "休息间隔",
};

function stopLabel(stop) {
  return stop?.name || stop?.spot_code || "停留点";
}

function durationLabel(minutes) {
  return minutes == null ? "未核实" : `${minutes} 分钟`;
}

function constraintValue(key, value) {
  if (value == null || value === "") return "未设置";
  if (["available_minutes", "rest_every_minutes"].includes(key)) return `${value} 分钟`;
  if (Array.isArray(value)) return value.length ? value.join("、") : "无";
  return String(value);
}

function orderLabel(order, snapshots) {
  const names = new Map();
  for (const snapshot of snapshots) {
    for (const stop of snapshot?.stops || []) names.set(stop.stop_id, stopLabel(stop));
  }
  return (order || []).map(id => names.get(id) || "未知停留点").join("、") || "无停留点";
}

function legLabel(items, snapshots) {
  const names = new Map();
  for (const snapshot of snapshots) {
    for (const stop of snapshot?.stops || []) names.set(stop.stop_id, stopLabel(stop));
  }
  if (!items?.length) return "无已记录路段";
  return items.map(leg => {
    const from = names.get(leg.from_stop_id) || "未知停留点";
    const to = names.get(leg.to_stop_id) || "未知停留点";
    return `${from} → ${to}（${durationLabel(leg.duration_minutes)}）`;
  }).join("；");
}

export function itineraryProposalDiffText(change, { beforeSnapshot, candidateSnapshot } = {}) {
  if (change.kind === "added") return `增加：${stopLabel(change.after)}（停留时长 ${durationLabel(change.after?.duration_minutes)}）`;
  if (change.kind === "removed") return `移除：${stopLabel(change.before)}（原停留时长 ${durationLabel(change.before?.duration_minutes)}）`;
  if (change.kind === "changed") {
    const before = change.before || {};
    const after = change.after || {};
    const details = [];
    if (before.name !== after.name || before.spot_code !== after.spot_code) {
      details.push(`地点：${stopLabel(before)} → ${stopLabel(after)}`);
    }
    if (before.duration_minutes !== after.duration_minutes) {
      details.push(`停留时长 ${durationLabel(before.duration_minutes)} → ${durationLabel(after.duration_minutes)}`);
    }
    if (before.kind !== after.kind) details.push(`类型：${before.kind || "未知"} → ${after.kind || "未知"}`);
    if (!details.length) details.push("行程信息已更新");
    return `调整${stopLabel(before)}：${details.join("；")}`;
  }
  if (change.kind === "moved") {
    return `调整停留顺序：${orderLabel(change.before?.order, [beforeSnapshot])} → ${orderLabel(change.after?.order, [candidateSnapshot])}`;
  }
  if (change.kind === "constraints") {
    const before = change.before || {};
    const after = change.after || {};
    const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])];
    const details = keys.filter(key => JSON.stringify(before[key]) !== JSON.stringify(after[key]))
      .map(key => `${constraintLabels[key] || key} ${constraintValue(key, before[key])} → ${constraintValue(key, after[key])}`);
    return details.length ? `调整约束：${details.join("；")}` : "游览约束已更新";
  }
  if (change.kind === "legs") {
    return `路段变化：${legLabel(change.before?.items, [beforeSnapshot])} → ${legLabel(change.after?.items, [candidateSnapshot])}`;
  }
  if (change.kind === "source") return "路线来源信息已更新";
  return "更新行程信息";
}
