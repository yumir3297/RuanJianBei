import { ref } from "vue";
import { haversineMeters, findNearestSpot, TRIGGER_RADIUS_M, EXIT_RADIUS_M, COOLDOWN_MS, PENDING_MAX_WAIT_MS } from "../constants/narration";

/**
 * 触发状态机：进入 TRIGGER_RADIUS_M 触发，离开 EXIT_RADIUS_M 后才可重听。
 * 忙时不打断，记入 pendingSpot；空闲后补播前会重测距离，走远则丢弃。
 * 若排队等待超过 PENDING_MAX_WAIT_MS（当前播放卡住或过长），中断后补播，避免功能被永久阻塞。
 */
export function useNarration({ getPosition, getSpots, isBusy, onTrigger, onInterrupt, maxPendingWaitMs = PENDING_MAX_WAIT_MS }) {
  const activeSpot = ref(null);
  const completed = ref([]);
  const status = ref("idle");
  const lastTriggeredAt = ref(0);

  let pendingSpot = null;
  let pendingSince = 0;
  let insideNames = new Set();

  function update() {
    const position = getPosition();
    const spots = getSpots() || [];
    if (!position) return;

    const nearest = findNearestSpot(position, spots);
    const nearestDistance = nearest ? nearest.distance : Infinity;

    // 更新 inside 集合（滞回：进入用 TRIGGER，退出用 EXIT）
    // 走出 EXIT 半径时同时清除「已触发」标记，使再次进入可重听
    for (const spot of spots) {
      const d = haversineMeters(position, spot);
      if (d <= TRIGGER_RADIUS_M) {
        insideNames.add(spot.name);
      } else if (d > EXIT_RADIUS_M) {
        insideNames.delete(spot.name);
        insideNames.delete(`${spot.name}__done`);
      }
    }

    if (activeSpot.value && insideNames.has(activeSpot.value.name)) {
      return; // 仍在当前景点范围内，保持
    }
    if (activeSpot.value && !insideNames.has(activeSpot.value.name)) {
      activeSpot.value = null;
      if (status.value === "playing") status.value = "idle";
    }

    if (!nearest || nearestDistance > TRIGGER_RADIUS_M) return;
    const spot = nearest.spot;
    if (insideNames.has(`${spot.name}__done`)) return; // 已在本轮区间内触发过

    const now = Date.now();
    if (now - lastTriggeredAt.value < COOLDOWN_MS) return;

    trigger(spot);
  }

  function trigger(spot) {
    insideNames.add(`${spot.name}__done`);
    lastTriggeredAt.value = Date.now();
    if (isBusy && isBusy()) {
      pendingSpot = spot;
      pendingSince = Date.now();
      status.value = "pending";
      return;
    }
    fire(spot);
  }

  function fire(spot) {
    activeSpot.value = spot;
    if (!completed.value.includes(spot.name)) completed.value = [...completed.value, spot.name];
    status.value = "playing";
    Promise.resolve(onTrigger && onTrigger(spot)).finally(() => {
      if (status.value === "playing") status.value = "idle";
    });
  }

  /** 由外部在「忙 -> 空闲」时驱动。 */
  function drainPending() {
    if (!pendingSpot) return;
    if (isBusy && isBusy()) {
      // 排队过久说明当前播放卡住或过长，中断后补播，避免功能被永久阻塞
      if (Date.now() - pendingSince < maxPendingWaitMs) return;
      if (onInterrupt) onInterrupt();
    }
    const spot = pendingSpot;
    const position = getPosition();
    pendingSpot = null;
    pendingSince = 0;
    status.value = "idle";
    if (!position) return;
    if (haversineMeters(position, spot) > EXIT_RADIUS_M) return; // 已走远，丢弃
    fire(spot);
  }

  function reset() {
    activeSpot.value = null;
    completed.value = [];
    status.value = "idle";
    pendingSpot = null;
    pendingSince = 0;
    insideNames = new Set();
    lastTriggeredAt.value = 0;
  }

  return { activeSpot, completed, status, update, drainPending, reset, fire, trigger };
}
