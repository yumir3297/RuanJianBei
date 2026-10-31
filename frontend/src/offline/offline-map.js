/**
 * 轻量静态地图查看器：单张 SVG/WebP，支持滚轮缩放、双指缩放、拖动与按钮缩放。
 * 不使用任何地图引擎、瓦片服务器或定位能力。
 */

const MIN_SCALE = 1;
const MAX_SCALE = 4;

export function createMapViewer(options) {
  const { viewport, image } = options;
  const state = { scale: MIN_SCALE, x: 0, y: 0 };
  const pointers = new Map();
  let pinchStart = null;

  function apply() {
    image.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
  }

  function clamp() {
    const viewportWidth = viewport.clientWidth;
    const viewportHeight = viewport.clientHeight;
    const contentWidth = image.offsetWidth * state.scale;
    const contentHeight = image.offsetHeight * state.scale;
    const maxX = Math.max(0, (contentWidth - viewportWidth) / 2);
    const maxY = Math.max(0, (contentHeight - viewportHeight) / 2);
    state.x = Math.min(maxX, Math.max(-maxX, state.x));
    state.y = Math.min(maxY, Math.max(-maxY, state.y));
  }

  function zoomTo(nextScale, anchorX = 0, anchorY = 0) {
    const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, nextScale));
    if (scale === state.scale) return;
    const ratio = scale / state.scale;
    state.x = anchorX - ratio * (anchorX - state.x);
    state.y = anchorY - ratio * (anchorY - state.y);
    state.scale = scale;
    if (state.scale === MIN_SCALE) {
      state.x = 0;
      state.y = 0;
    }
    clamp();
    apply();
  }

  function reset() {
    state.scale = MIN_SCALE;
    state.x = 0;
    state.y = 0;
    apply();
  }

  function pointerDistance() {
    const [a, b] = [...pointers.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function handlePointerDown(event) {
    if (event.button != null && event.button > 0) return;
    viewport.setPointerCapture?.(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 2) {
      pinchStart = { distance: pointerDistance(), scale: state.scale, x: state.x, y: state.y };
    }
    viewport.classList.add("is-dragging");
  }

  function handlePointerMove(event) {
    const previous = pointers.get(event.pointerId);
    if (!previous) return;
    const dx = event.clientX - previous.x;
    const dy = event.clientY - previous.y;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

    if (pointers.size === 2 && pinchStart) {
      const distance = pointerDistance();
      if (pinchStart.distance > 0) {
        zoomTo(pinchStart.scale * (distance / pinchStart.distance));
      }
      return;
    }
    if (state.scale <= MIN_SCALE) return;
    state.x += dx;
    state.y += dy;
    clamp();
    apply();
  }

  function handlePointerUp(event) {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinchStart = null;
    if (pointers.size === 0) viewport.classList.remove("is-dragging");
  }

  function handleWheel(event) {
    event.preventDefault();
    const rect = viewport.getBoundingClientRect();
    const anchorX = event.clientX - rect.left - rect.width / 2 - state.x;
    const anchorY = event.clientY - rect.top - rect.height / 2 - state.y;
    const factor = event.deltaY < 0 ? 1.15 : 1 / 1.15;
    zoomTo(state.scale * factor, anchorX, anchorY);
  }

  function handleKeyDown(event) {
    if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      zoomTo(state.scale * 1.2);
    } else if (event.key === "-" || event.key === "_") {
      event.preventDefault();
      zoomTo(state.scale / 1.2);
    } else if (event.key === "0") {
      event.preventDefault();
      reset();
    }
  }

  viewport.addEventListener("pointerdown", handlePointerDown);
  viewport.addEventListener("pointermove", handlePointerMove);
  viewport.addEventListener("pointerup", handlePointerUp);
  viewport.addEventListener("pointercancel", handlePointerUp);
  viewport.addEventListener("wheel", handleWheel, { passive: false });
  viewport.addEventListener("keydown", handleKeyDown);
  image.addEventListener("load", reset);
  image.addEventListener("dragstart", preventDrag);

  return {
    zoomIn: () => zoomTo(state.scale * 1.2),
    zoomOut: () => zoomTo(state.scale / 1.2),
    reset,
    destroy() {
      viewport.removeEventListener("pointerdown", handlePointerDown);
      viewport.removeEventListener("pointermove", handlePointerMove);
      viewport.removeEventListener("pointerup", handlePointerUp);
      viewport.removeEventListener("pointercancel", handlePointerUp);
      viewport.removeEventListener("wheel", handleWheel);
      viewport.removeEventListener("keydown", handleKeyDown);
      image.removeEventListener("load", reset);
      image.removeEventListener("dragstart", preventDrag);
    },
  };
}

function preventDrag(event) {
  event.preventDefault();
}
