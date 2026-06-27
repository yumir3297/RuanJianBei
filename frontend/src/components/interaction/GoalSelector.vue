<template>
  <section class="guide-selector" aria-labelledby="guide-selector-title">
    <div class="selector-heading">
      <div>
        <h2 id="guide-selector-title">今天想怎样游灵山？</h2>
        <p>选一个游览方向，小灵会顺着您的兴趣来讲解。</p>
      </div>
      <el-button v-if="interactionStore.mode !== 'free_chat'" text @click="clearGuidedContext">
        清除选择
      </el-button>
    </div>

    <div class="selection-breadcrumb" aria-label="当前选择">
      <span class="breadcrumb-label">当前</span>
      <template v-for="(item, index) in interactionStore.breadcrumbs" :key="`${item}-${index}`">
        <span v-if="index" class="breadcrumb-separator">/</span>
        <strong>{{ item }}</strong>
      </template>
    </div>

    <el-alert
      v-if="interactionStore.error"
      class="selector-alert"
      type="warning"
      :closable="false"
      show-icon
      title="主动选择数据暂时不可用，仍可直接输入文字提问。"
    >
      <template #default>
        <el-button size="small" @click="interactionStore.loadBootstrap">重新加载</el-button>
      </template>
    </el-alert>

    <div class="goal-grid">
      <button
        v-for="goal in goals"
        :key="goal.mode"
        type="button"
        :class="['goal-card', { active: interactionStore.mode === goal.mode }]"
        :aria-pressed="interactionStore.mode === goal.mode"
        @click="selectGoal(goal.mode)"
      >
        <span class="goal-index">{{ goal.index }}</span>
        <span>
          <strong>{{ goal.label }}</strong>
          <small>{{ goal.description }}</small>
        </span>
      </button>
    </div>

    <div v-if="interactionStore.loading" class="selector-loading">
      <el-skeleton :rows="2" animated />
    </div>

    <div v-else-if="interactionStore.loaded" class="selector-details">
      <div v-if="interactionStore.mode === 'attraction'" class="detail-section attraction-section">
        <div class="detail-heading">
          <span>01</span>
          <div>
            <h3>选择景点</h3>
            <p>景点来自当前官方资料知识库。</p>
          </div>
        </div>
        <el-select
          v-model="selectedAttractionId"
          class="attraction-select"
          clearable
          filterable
          placeholder="搜索或选择景点"
          no-data-text="当前没有可选景点"
        >
          <el-option
            v-for="attraction in interactionStore.bootstrap.attractions"
            :key="attraction.id"
            :label="attraction.title"
            :value="attraction.id"
          >
            <div class="attraction-option">
              <span>{{ attraction.title }}</span>
              <small>{{ attraction.scenic_area || attraction.attraction_code || "官方资料" }}</small>
            </div>
          </el-option>
        </el-select>

        <div class="topic-block">
          <span class="field-label">可选一个关注话题</span>
          <div class="topic-grid">
            <button
              v-for="topic in interactionStore.bootstrap.topics"
              :key="topic.key"
              type="button"
              :class="['topic-chip', { active: interactionStore.topicKey === topic.key }]"
              @click="toggleTopic(topic.key)"
            >
              {{ topic.label }}
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="interactionStore.mode === 'topic'" class="detail-section">
        <div class="detail-heading">
          <span>01</span>
          <div>
            <h3>选择话题</h3>
            <p>不指定景点，先从感兴趣的方向开始。</p>
          </div>
        </div>
        <div v-if="interactionStore.bootstrap.topics.length" class="topic-grid wide">
          <button
            v-for="topic in interactionStore.bootstrap.topics"
            :key="topic.key"
            type="button"
            :class="['topic-chip', { active: interactionStore.topicKey === topic.key }]"
            @click="interactionStore.selectTopic(topic.key)"
          >
            {{ topic.label }}
          </button>
        </div>
        <el-empty v-else description="当前没有可选话题" />
      </div>

      <div v-else-if="interactionStore.mode === 'route'" class="detail-section">
        <div class="detail-heading">
          <span>01</span>
          <div>
            <h3>选择路线</h3>
            <p>路线来自官方资料中的结构化推荐方案。</p>
          </div>
        </div>
        <div v-if="interactionStore.bootstrap.routes.length" class="route-grid">
          <button
            v-for="route in interactionStore.bootstrap.routes"
            :key="route.id"
            type="button"
            :class="['route-card', { active: interactionStore.routeId === route.id }]"
            @click="interactionStore.selectRoute(route.id)"
          >
            <span class="route-duration">{{ route.duration_label }}</span>
            <strong>{{ route.title }}</strong>
            <small>{{ route.tags.join(" · ") || "综合导览" }}</small>
          </button>
        </div>
        <el-empty v-else description="当前没有可选路线" />
      </div>

      <div v-else class="free-chat-note">
        <span class="free-chat-mark">灵</span>
        <div>
          <strong>直接问你关心的问题</strong>
          <p>例如景点特色、历史文化、开放信息或游览建议。</p>
        </div>
      </div>
    </div>

  </section>
</template>

<script setup>
import { computed } from "vue";

import { useInteractionStore } from "../../stores/interaction";

const interactionStore = useInteractionStore();
const emit = defineEmits(["goal-select"]);

const goals = [
  { mode: "free_chat", index: "问", label: "自由提问", description: "直接输入你的问题" },
  { mode: "attraction", index: "景", label: "景点讲解", description: "锁定一个具体景点" },
  { mode: "topic", index: "趣", label: "话题探索", description: "从文化兴趣出发" },
  { mode: "route", index: "路", label: "路线规划", description: "选择现有游览方案" },
];

const selectedAttractionId = computed({
  get: () => interactionStore.attractionId,
  set: (value) => interactionStore.selectAttraction(value),
});

function toggleTopic(topicKey) {
  interactionStore.selectTopic(interactionStore.topicKey === topicKey ? null : topicKey);
}

function selectGoal(mode) {
  interactionStore.setMode(mode);
  emit("goal-select", mode);
}

function clearGuidedContext() {
  interactionStore.clearSelection();
}
</script>

<style scoped>
.guide-selector {
  margin: 0 16px 20px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.selector-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}

.selector-heading h2 {
  margin: 0 0 8px;
  font-size: var(--text-base);
  font-weight: 650;
  color: var(--text);
}

.selector-heading p,
.detail-heading p,
.free-chat-note p {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.selection-breadcrumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  margin: 14px 0;
  padding: 6px 10px;
  border-left: 3px solid var(--lingshan-gold);
  background: rgba(250, 241, 226, 0.78);
  color: #244b47;
  font-size: 13px;
}

.breadcrumb-label {
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.breadcrumb-separator {
  color: #9ca3af;
}

.selector-alert {
  margin-bottom: 14px;
}

.goal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.goal-card,
.topic-chip,
.route-card {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.goal-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
  text-align: left;
}

.goal-card:hover {
  border-color: var(--brand);
  background: var(--brand-bg);
}

.goal-card.active {
  border-color: var(--brand);
  background: var(--brand-bg);
}

.goal-index {
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.goal-card.active .goal-index {
  color: var(--brand);
}

.goal-card strong,
.goal-card small {
  display: block;
}

.goal-card strong {
  font-size: 14px;
}

.goal-card small {
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 12px;
}

.goal-card.active small {
  color: var(--text-secondary);
}

.selector-loading,
.selector-details {
  margin-top: 16px;
}

.selector-details {
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  background: var(--surface);
}

.detail-heading {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.detail-heading > span {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 50%;
  background: #fef3c7;
  color: #92400e;
  font-family: Georgia, serif;
  font-weight: 700;
}

.detail-heading h3 {
  margin: 0 0 4px;
  color: var(--lingshan-green-deep);
  font-size: 16px;
}

.attraction-select {
  width: min(100%, 520px);
}

.attraction-option {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.attraction-option small {
  color: #94a3b8;
}

.topic-block {
  margin-top: 14px;
}

.field-label {
  display: block;
  margin-bottom: 10px;
  color: #48635f;
  font-size: 13px;
  font-weight: 700;
}

.topic-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-grid.wide {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.topic-chip {
  padding: 9px 14px;
  border: 1px solid #cbdeda;
  border-radius: 999px;
  background: #fff;
  color: #355a55;
}

.topic-chip.active {
  border-color: var(--lingshan-gold);
  background: #fbf1e2;
  color: var(--lingshan-gold-deep);
  box-shadow: inset 0 0 0 1px rgba(184, 137, 79, 0.18);
}

.route-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.route-card {
  display: grid;
  gap: 6px;
  min-height: 112px;
  padding: 14px;
  border: 1px solid #d7e5e2;
  border-radius: 16px;
  background: #fff;
  color: #244b47;
  text-align: left;
}

.route-card.active {
  border-color: var(--lingshan-green);
  background: var(--lingshan-green-light);
  box-shadow: inset 0 0 0 1px rgba(54, 88, 71, 0.16);
}

.route-duration {
  width: fit-content;
  padding: 4px 8px;
  border-radius: 6px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
}

.route-card small {
  color: #6b827e;
}

.free-chat-note {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 62px;
}

.free-chat-mark {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 16px 4px 16px 4px;
  background: var(--lingshan-green-deep);
  color: #f3d7a7;
  font-family: Georgia, serif;
  font-weight: 700;
}

.free-chat-note strong {
  display: block;
  margin-bottom: 5px;
  color: #163f3b;
}

</style>
