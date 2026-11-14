<template>
  <div
    v-if="bannerVisible"
    class="offline-entry-prompt"
    :class="`offline-entry-prompt--${bannerTone}`"
    role="status"
    aria-live="polite"
  >
    <div class="offline-entry-copy">
      <strong>{{ bannerTitle }}</strong>
      <span>{{ bannerDetail }}</span>
    </div>
    <div class="offline-entry-actions">
      <button
        v-if="state === 'DEGRADED' && packageReady"
        type="button"
        class="offline-entry-primary"
        @click="enterOffline"
      >
        进入离线伴游
      </button>
      <button
        v-else-if="state === 'DEGRADED' && packageState !== 'preparing'"
        type="button"
        class="offline-entry-secondary"
        @click="preparePackage"
      >
        {{ packageState === 'failed' ? '重新准备离线包' : '准备离线包' }}
      </button>
      <button type="button" class="offline-entry-dismiss" @click="dismiss">稍后</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { createConnectivityMonitor, normalizeReturnTarget } from "../offline/connectivity.js";
import { createOfflineStorage } from "../offline/offline-storage.js";
import { prepareOfflinePackage } from "../offline/offline-registration.js";

const APP_VERSION = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "dev";

// 只在生产构建里注册 Service Worker；开发模式如实显示为不可用。
const packageSupported = Boolean(import.meta.env.PROD) && "serviceWorker" in navigator;

const state = ref("UNKNOWN");
const packageState = ref(packageSupported ? "idle" : "unsupported");
const packageReady = ref(false);
const dismissed = ref(false);
let monitor = null;
let unsubscribe = null;
let preparing = null;

const bannerVisible = computed(() => {
  if (dismissed.value) return false;
  if (state.value === "DEGRADED") return true;
  return state.value === "SUSPECT" && packageState.value === "ready";
});

const bannerTone = computed(() => (state.value === "DEGRADED" ? "urgent" : "calm"));

const bannerTitle = computed(() =>
  state.value === "DEGRADED" ? "网络暂时不可达，可进入离线伴游" : "连接不稳定，正在重试",
);

const bannerDetail = computed(() => {
  if (state.value !== "DEGRADED") return "若持续不可达，会自动提示进入离线地图、求助与小游戏。";
  if (packageState.value === "preparing") return "正在准备离线包，请稍候…";
  if (packageState.value === "ready") return "离线地图、紧急求助与小游戏已缓存，可断网使用。";
  if (packageState.value === "unsupported") return "当前环境无法启动离线缓存，仍可尝试打开离线页。";
  return "离线包尚未准备完成，可先保持联网后重试。";
});

async function preparePackage() {
  if (!packageSupported) return;
  if (preparing) return preparing;
  packageState.value = "preparing";
  preparing = prepareOfflinePackage()
    .then((result) => {
      packageReady.value = Boolean(result.ready);
      packageState.value = result.ready ? "ready" : "failed";
      return result;
    })
    .catch(() => {
      packageReady.value = false;
      packageState.value = "failed";
      return null;
    })
    .finally(() => {
      preparing = null;
    });
  return preparing;
}

async function enterOffline() {
  const storage = createOfflineStorage({ appVersion: APP_VERSION });
  const target = normalizeReturnTarget(`${window.location.pathname}${window.location.search}`);
  await storage.save({ returnTarget: target }).catch(() => {});
  window.location.assign("/offline.html");
}

function dismiss() {
  dismissed.value = true;
}

onMounted(() => {
  monitor = createConnectivityMonitor({ intervalMs: 5000, hiddenIntervalMs: 30000 });
  unsubscribe = monitor.subscribe((next) => {
    state.value = next;
    if (next === "ONLINE") dismissed.value = false;
  });
  monitor.start();
  preparePackage();
});

onBeforeUnmount(() => {
  unsubscribe?.();
  monitor?.stop();
  monitor = null;
});
</script>

<style scoped>
.offline-entry-prompt {
  position: fixed;
  left: 50%;
  bottom: calc(14px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  width: min(640px, calc(100vw - 24px));
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  background: #fbf6ea;
  border: 1px solid rgba(36, 43, 38, 0.16);
  box-shadow: 0 2px 0 rgba(227, 215, 190, 0.95), 0 16px 34px rgba(58, 50, 36, 0.22);
}

.offline-entry-prompt--urgent {
  border-left: 4px solid #b4462f;
  color: #3a2f27;
}

.offline-entry-prompt--calm {
  border-left: 4px solid #6f8a72;
  color: #2c4a3b;
}

.offline-entry-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 180px;
  flex: 1;
}

.offline-entry-copy strong {
  font-family: "Songti SC", "Noto Serif SC", "STSong", serif;
  font-size: 15px;
  letter-spacing: 0.08em;
}

.offline-entry-copy span {
  color: #6f7d6d;
  font-size: 12px;
}

.offline-entry-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.offline-entry-actions button {
  min-height: 40px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.offline-entry-primary {
  background: #b4462f;
  border-color: #8e3323 !important;
  color: #fdf6ec;
  font-family: "Songti SC", "Noto Serif SC", "STSong", serif;
  letter-spacing: 0.1em;
  box-shadow: 0 2px 0 #8e3323;
}

.offline-entry-primary:active {
  transform: translateY(1px);
  box-shadow: none;
}

.offline-entry-secondary {
  background: #fbf6ea;
  border-color: rgba(36, 43, 38, 0.2) !important;
  color: #4c5a50;
}

.offline-entry-dismiss {
  background: transparent;
  color: #7a867a;
  font-size: 12px;
}

@media (max-width: 480px) {
  .offline-entry-prompt {
    align-items: flex-start;
    flex-direction: column;
  }

  .offline-entry-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
