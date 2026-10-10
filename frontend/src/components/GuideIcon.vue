<template>
  <svg class="guide-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path v-for="(path, index) in paths" :key="index" :d="path" />
  </svg>
</template>

<script setup>
import { computed } from "vue";
const props = defineProps({ name: { type: String, default: "landmark" } });
const icons = {
  landmark: ["M3 20h18M5 20V10h14v10M3 10h18L12 3 3 10Z", "M9 14v6m6-6v6"],
  map: ["m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2V5Z", "M9 3v16m6-14v16"],
  route: ["M7 6a2 2 0 1 0-4 0 2 2 0 0 0 4 0Zm14 12a2 2 0 1 0-4 0 2 2 0 0 0 4 0Z", "M5 8v5a3 3 0 0 0 3 3h5a3 3 0 0 0 0-6h-1m5-4h4m-2-2v4"],
  book: ["M12 5c-3-2-6-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Zm0 0v15"],
  keyboard: ["M3 6h18v12H3V6Z", "M6 9h.01M9 9h.01M12 9h.01M15 9h.01M18 9h.01M6 12h.01M9 12h.01M12 12h.01M15 12h.01M18 12h.01M8 15h8"],
  camera: ["M4 7h3l2-3h6l2 3h3a1 1 0 0 1 1 1v11H3V8a1 1 0 0 1 1-1Z", "M16 13a4 4 0 1 0-8 0 4 4 0 0 0 8 0Z"],
  mic: ["M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5Z", "M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-3 0h6"],
  send: ["m4 12 16-8-5 16-3-8-8 0Zm8 0 8-8"],
  chevron: ["m8 10 4 4 4-4"],
  close: ["m6 6 12 12M6 18 18 6"],
  settings: ["M4 7h16M4 17h16M8 4v6m8 4v6"],
  headphones: ["M4 14v-3a8 8 0 0 1 16 0v3M4 12H3v7h4v-7H4Zm16 0h1v7h-4v-7h3Z"],
  info: ["M21 12a9 9 0 1 0-18 0 9 9 0 0 0 18 0ZM12 11v6m0-10h.01"],
  back: ["M20 12H4m6-6-6 6 6 6"],
};
const paths = computed(() => icons[props.name] || icons.landmark);
</script>

<style scoped>
.guide-icon { width: 20px; height: 20px; flex: 0 0 auto; }
</style>
