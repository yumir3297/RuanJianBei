<template>
  <el-alert
    v-if="job"
    :type="job.state === 'succeeded' ? 'success' : job.state === 'failed' ? 'error' : 'info'"
    :title="statusTitle"
    :closable="false"
    show-icon
  >
    <template #default>
      <div class="publication-status">
        <span v-if="job.error">{{ job.error }}</span>
        <el-button v-if="job.state === 'failed'" link type="primary" :loading="retrying" @click="$emit('retry')">重试发布</el-button>
      </div>
    </template>
  </el-alert>
</template>

<script setup>
import { computed } from "vue";
const props = defineProps({ job: { type: Object, default: null }, retrying: Boolean });
defineEmits(["retry"]);
const statusTitle = computed(() => ({ queued: "发布任务已排队", preparing: "正在准备并校验发布内容", succeeded: "发布完成", failed: "发布失败" }[props.job?.state] || "发布状态"));
</script>

<style scoped>
.publication-status { display:flex; align-items:center; justify-content:space-between; gap:12px; }
</style>
