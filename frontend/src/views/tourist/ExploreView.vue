<template>
  <div class="guide-tool-content">
    <p class="tool-description">找一处风景，让导游讲讲它的故事。</p>
    <div class="tool-filters">
      <input v-model="search" class="tool-search" type="search" placeholder="搜索景点" aria-label="搜索景点" />
      <select v-model="zone" aria-label="按区域筛选"><option value="">全部区域</option><option v-for="area in areaSubNav" :key="area.key" :value="area.key">{{ area.label }}</option></select>
      <select v-model="type" aria-label="按类型筛选"><option value="">全部类型</option><option v-for="item in typeSubNav" :key="item.key" :value="item.key">{{ item.label }}</option></select>
    </div>
    <div class="spot-grid">
      <button v-for="spot in filteredSpots" :key="spot.name" type="button" class="spot-card" :disabled="busy" @click="$emit('ask', { query: '请介绍' + spot.name + '的特色和游览建议', attraction: spot.name })">
        <div class="spot-image"><img v-if="!failedImages.has(spot.name)" :src="spot.image" :alt="spot.name" loading="lazy" @error="failedImages.add(spot.name)" /><GuideIcon v-else name="landmark" /></div>
        <div class="spot-copy"><strong>{{ spot.name }}</strong><span>{{ spot.desc }}</span><small>听导游讲解 <span aria-hidden="true">↗</span></small></div>
      </button>
    </div>
    <p v-if="!filteredSpots.length" class="tool-empty">没有找到相关景点，试试其他关键词或分类。</p>
  </div>
</template>
<script setup>
import { computed, ref } from "vue";
import GuideIcon from "../../components/GuideIcon.vue";
import { scenicSpots, areaSubNav, typeSubNav } from "../../constants/touristCatalog";
defineProps({ busy: { type: Boolean, default: false } });
defineEmits(["ask"]);
const search = ref("");
const zone = ref("");
const type = ref("");
const failedImages = ref(new Set());
const filteredSpots = computed(() => scenicSpots.filter(spot =>
  (!zone.value || spot.zone === zone.value) && (!type.value || spot.type === type.value)
  && (!search.value.trim() || (spot.name + spot.desc).includes(search.value.trim()))
));
</script>
