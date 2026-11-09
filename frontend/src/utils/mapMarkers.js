// Keep the representative at an existing point. Clustering must never rewrite
// geographic coordinates merely to make the map look less crowded.
export function groupMapPoints(points, distance = 44, selectedName = "") {
  const ordered = [...points].sort((a, b) =>
    Number(b.name === selectedName) - Number(a.name === selectedName)
    || b.heat - a.heat || a.name.localeCompare(b.name, "zh-CN"));
  const groups = [];
  for (const point of ordered) {
    const group = groups.find(items => Math.hypot(items[0].x - point.x, items[0].y - point.y) < distance);
    if (group) group.push(point);
    else groups.push([point]);
  }
  return groups;
}

// Labels are optional: preserve point positions and hide names that would
// collide with another label, a point, or the fixed map controls.
export function layoutMapLabels(groups, width, height, selectedName = "") {
  const selected = groups.find(group=>group[0].name === selectedName)?.[0];
  const labelWidth = selected ? selected.name.length * 12 + 16 : 0;
  const placed = selected ? [{x:selected.x-labelWidth/2,y:selected.y-46,w:labelWidth,h:26}] : [];
  const labels = new Map();
  const overlaps = (a,b) => a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y;
  const pointBoxes = groups.map(([p]) => ({x:p.x-18,y:p.y-18,w:36,h:36}));
  for (const group of groups) {
    const p = group[0];
    if (group.length > 1 || p.name === selectedName) continue;
    const w = p.name.length * 12 + 16;
    const candidates = [
      {x:p.x+19,y:p.y-12,w,h:24,side:'right'},
      {x:p.x-w-19,y:p.y-12,w,h:24,side:'left'},
      {x:p.x-w/2,y:p.y+21,w,h:24,side:'bottom'},
    ];
    const box = candidates.find(b => b.x>=8 && b.x+b.w<=width-8 && b.y>=100 && b.y+b.h<=height-145
      && !placed.some(other=>overlaps(b,other)) && !pointBoxes.some(other=>overlaps(b,other))
      && !(b.x+b.w>width-66 && b.y<230));
    if (box) { placed.push(box); labels.set(p.name,box.side); }
  }
  return labels;
}

export function markerSymbol(type, name = "") {
  const paths = name.includes("桥") ? ['M3 17h18M4 17V9m16 8V9M4 13c4-6 12-6 16 0M8 11v6m8-6v6']
    : name.includes("湖") || name === "九龙灌浴" ? ['M3 8c3-3 6 3 9 0s6 3 9 0M3 13c3-3 6 3 9 0s6 3 9 0M3 18c3-3 6 3 9 0s6 3 9 0']
    : type === "ziran" ? ['M19 4C8 3 3 8 5 15c6 5 15-1 14-11ZM5 20 16 9']
    : type === "simiao" ? ['M3 10h18L12 4 3 10ZM5 10v10h14V10M3 20h18M9 13v7m6-7v7']
    : type === "foxiang" ? ['M12 4c-5 5-5 9 0 13 5-4 5-8 0-13ZM12 17C6 18 3 14 3 10c4 0 7 2 9 7Zm0 0c6 1 9-3 9-7-4 0-7 2-9 7ZM6 21h12']
    : ['M5 4h14v16H5ZM8 8h8M8 12h8M8 16h5'];
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths.map(d => `<path d="${d}"/>`).join("")}</svg>`;
}
