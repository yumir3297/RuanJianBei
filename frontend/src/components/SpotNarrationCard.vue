<template>
  <div class="narration-card" role="status">
    <div class="nc-head">
      <span class="nc-emoji">{{ spot.emoji }}</span>
      <div class="nc-title">
        <strong>{{ spot.name }}</strong>
        <small>{{ subtitle }}</small>
      </div>
      <button type="button" class="nc-close" aria-label="关闭讲解" @click="$emit('close')">×</button>
    </div>
    <p class="nc-desc">{{ text || spot.desc }}</p>
    <div class="nc-track"><div class="nc-fill" :style="{ width: `${Math.round(progress * 100)}%` }"></div></div>
    <div class="nc-actions">
      <button type="button" class="nc-btn" :disabled="loading" @click="$emit('replay')">
        {{ loading ? "讲解生成中…" : "重听" }}
      </button>
      <button type="button" class="nc-btn ghost" :disabled="!playing" @click="$emit('stop')">停止</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  spot: { type: Object, required: true },
  text: { type: String, default: "" },
  progress: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
  degraded: { type: Boolean, default: false },
});
defineEmits(["close", "replay", "stop"]);

const subtitle = computed(() => (props.degraded ? "离线讲解 · 浏览器朗读" : "数字人语音讲解"));
</script>

<style scoped>
.narration-card { position: absolute; right: 8px; bottom: 28px; z-index: 500; width: 240px; padding: 10px 11px; border-radius: 10px; border: 1px solid rgba(45, 90, 75, 0.18); background: rgba(255, 255, 255, 0.97); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.14); }
.nc-head { display: flex; align-items: center; gap: 8px; }
.nc-emoji { font-size: 20px; line-height: 1; }
.nc-title { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.nc-title strong { font-size: 13px; color: #2c3a33; }
.nc-title small { font-size: 11px; color: #94a39c; }
.nc-close { border: 0; background: transparent; font-size: 16px; line-height: 1; color: #94a39c; cursor: pointer; }
.nc-desc { margin: 7px 0 8px; font-size: 12px; line-height: 1.6; color: #5a6b62; max-height: 54px; overflow: hidden; }
.nc-track { height: 4px; border-radius: 999px; background: #eaf0eb; overflow: hidden; margin-bottom: 8px; }
.nc-fill { height: 100%; background: linear-gradient(90deg, #4d7565, #2d5a4b); transition: width 0.2s linear; }
.nc-actions { display: flex; gap: 6px; }
.nc-btn { flex: 1; min-height: 28px; border-radius: 7px; border: 1px solid #2d5a4b; background: #2d5a4b; color: #f3f7f4; font-size: 12px; cursor: pointer; }
.nc-btn:disabled { opacity: 0.5; cursor: default; }
.nc-btn.ghost { background: transparent; color: #2d5a4b; }
</style>
