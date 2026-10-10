<template>
  <div class="guide-tool-content">
    <p class="tool-description">从一段典故、一座建筑，读懂这座景区。</p>
    <div class="tool-chips" aria-label="问题分类"><button v-for="(item, key) in QUESTION_DATA" :key="key" type="button" :class="{ active: category === key }" :aria-pressed="category === key" @click="category = key; subCategory = ''">{{ item.label }}</button></div>
    <div class="tool-chips tool-chips--secondary" aria-label="问题主题"><button type="button" :class="{ active: !subCategory }" :aria-pressed="!subCategory" @click="subCategory = ''">全部主题</button><button v-for="(sub, key) in selectedCategory.subs" :key="key" type="button" :class="{ active: subCategory === key }" :aria-pressed="subCategory === key" @click="subCategory = key">{{ sub.label }}</button></div>
    <div class="question-grid"><button v-for="card in cards" :key="card.title" type="button" class="question-card" :disabled="busy" @click="$emit('ask', { query: card.query })"><span><strong>{{ card.title }}</strong><small>{{ card.desc }}</small></span><span class="question-arrow" aria-hidden="true">↗</span></button></div>
  </div>
</template>
<script setup>
import { computed, ref } from "vue";
import { QUESTION_DATA } from "../../constants/touristCatalog";
defineProps({ busy: { type: Boolean, default: false } });
defineEmits(["ask"]);
const category = ref("photo");
const subCategory = ref("");
const selectedCategory = computed(() => QUESTION_DATA[category.value]);
const cards = computed(() => Object.entries(selectedCategory.value.subs).filter(([key]) => !subCategory.value || key === subCategory.value).flatMap(([, sub]) => sub.cards));
</script>
