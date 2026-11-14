<template>
  <section class="cass-safety" role="alert" aria-live="assertive">
    <strong>{{ event?.type === "sos" ? "求助入口" : event?.simulated ? "安全提醒（演示数据）" : "安全提醒" }}</strong>
    <p>{{ event?.headline || "情境变化，普通讲解已暂停。请留意现场公告并联系景区工作人员。" }}</p>
    <p class="cass-safety__note">{{ event?.instruction || "未连接后台接警；请通过现场服务电话或工作人员求助。" }}</p>
    <button v-if="event?.type !== 'sos'" type="button" @click="$emit('clear')">我已了解</button>
    <button v-else type="button" @click="$emit('dismiss')">关闭提示</button>
  </section>
</template>

<script setup>
defineProps({ event: { type: Object, default: null } });
defineEmits(["clear", "dismiss"]);
</script>

<style scoped>
.cass-safety{padding:.75rem;border:1px solid #e5a23b;border-radius:12px;background:#fff6e5;color:#513600}.cass-safety p{margin:.45rem 0}.cass-safety__note{font-size:.82rem}.cass-safety button{border:0;border-radius:8px;padding:.45rem .7rem;background:#815400;color:white}
</style>
