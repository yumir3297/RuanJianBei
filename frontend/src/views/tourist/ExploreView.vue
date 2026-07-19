<template>
  <section class="tourist-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>
    <button type="button" class="back-btn" @click="handleBack">← 返回</button>
    <div class="top-right"><span class="top-brand">灵山智能导览系统</span>
    </div>
    <div class="tourist-stage">
      <div class="chat-center">
        <div class="top-caption">
          <span class="crowd-indicator" data-level="green"><span class="crowd-dot"></span>当前景区人数：舒适</span>
          <span class="caption-kicker">{{ avatarDisplaySubtitle }} · 景点探索</span>
          <span class="caption-weather" v-if="!weatherCaption">拍照识景 · 发现灵山</span>
          <span class="caption-weather caption-weather-live" v-else>{{ weatherCaption }}</span>
        </div>
        <div class="avatar-stage">
          <ThreeAvatar v-if="!avatarError" :preset="avatarConfig.modelKey" :emotion="avatar.currentEmotion.value" :is-speaking="avatarState==='speaking'||avatarState==='happy'" :speech-progress="speechProgress" :speech-elapsed-ms="speechElapsedMs" :speech-duration-ms="speechDurationMs" :speech-sync-active="activeAudioSegments>0" :viseme-timeline="visemeTimeline" :avatar-state="avatarState" :action="avatar.currentAction.value" :action-key="avatar.actionKey.value" @loaded="handleAvatarLoaded" @error="handleAvatarLoadError" />
          <AvatarDisplay v-else :state="avatarState" :emotion="avatar.currentEmotion.value" />
        </div>
      </div>
      <aside class="side-card" :class="{speaking:chatStore.streaming}">
        <div class="side-card-head"><div class="side-card-tabs">
          <button :class="['side-card-tab',{active:activeTab==='chat'}]" @click="activeTab='chat'">对话</button>
          <button :class="['side-card-tab',{active:activeTab==='source'}]" @click="activeTab='source'">来源</button>
        </div></div>
        <div :class="['side-card-body',{hidden:activeTab!=='chat'}]" ref="messageListRef">
          <article v-for="(m,i) in chatStore.messages" :key="`${m.role}-${i}`" :class="['msg-item',m.role,{collapsed:m.role==='user'&&i<chatStore.messages.length-1&&chatStore.messages[i+1]?.role==='assistant'}]">
            <div v-if="m.role==='assistant'" class="msg-bubble" v-html="renderAnswer(m.content,i===chatStore.messages.length-1)" @click="handleCitationClick"></div>
            <div v-else class="msg-bubble">{{ m.content }}</div>
            <div v-if="m.role === 'assistant' && m.content && !chatStore.streaming" class="answer-feedback" aria-label="回答评价">
              <span>这条讲解有帮助吗？</span>
              <button type="button" :class="{ active: m.feedbackRating === 'positive' }" :disabled="m.feedbackSubmitting" @click="chatStore.submitFeedback(m, 'positive')">👍 有帮助</button>
              <button type="button" :class="{ active: m.feedbackPendingRating === 'negative' || m.feedbackRating === 'negative' }" :disabled="m.feedbackSubmitting" @click="m.feedbackPendingRating = m.feedbackPendingRating === 'negative' ? null : 'negative'">👎 需改进</button>
              <div v-if="m.feedbackPendingRating === 'negative'" class="feedback-reasons">
                <span>请选择原因：</span>
                <button v-for="reason in feedbackReasons" :key="reason.value" type="button" :disabled="m.feedbackSubmitting" @click="chatStore.submitFeedback(m, 'negative', reason.value)">{{ reason.label }}</button>
              </div>
              <span v-if="m.feedbackError" class="feedback-error">{{ m.feedbackError }}</span>
            </div>
            <span v-if="m.role==='assistant'&&chatStore.streaming&&i===chatStore.messages.length-1&&m.content.length>0" class="typing-cursor">|</span>
          </article>
          <div v-if="chatStore.followups.length" class="followup-panel">
            <button v-for="(fu,i) in chatStore.followups" :key="i" class="followup-btn" @click="handleFollowup(fu)">{{ fu.query||fu.label||fu }}</button>
          </div>
          <div v-if="chatStore.userStopped&&!chatStore.streaming" class="stop-notice" role="status">已停止输出</div>
          <div v-if="chatStore.errorMessage&&!chatStore.streaming" class="error-notice" role="alert">{{ chatStore.errorMessage }}</div>
        </div>
        <div :class="['side-card-body',{hidden:activeTab!=='source'}]">
          <ul v-if="chatStore.sources.length" class="source-list">
            <li v-for="(s,i) in chatStore.sources" :key="i" :class="['source-item',{highlight:sourceHighlightIndex===i}]" :data-source-index="i">
              <h4><span class="source-num">{{ i+1 }}</span>{{ s.title }}</h4><p>{{ s.snippet }}</p><span class="source-meta">{{ s.source }}</span>
            </li>
          </ul>
          <div v-else class="source-empty">提问后这里会显示参考资料</div>
        </div>
      </aside>
      <aside class="right-card">
        <div class="right-card-head">
          <span v-if="navLevel==='level1'">探索工具</span>
          <span v-else-if="navLevel==='level2'">{{ navTitle }}</span>
          <span v-else>{{ navTitle }}</span>
          <span class="right-card-head-status">
            <span :class="['status-inline-dot', avatarReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">数字人</span>
            <span :class="['status-inline-dot', voiceReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">语音</span>
            <span :class="['status-inline-dot', replyStatusClass.replace('status-pill--','status-inline-dot--')]">回答</span>
          </span>
        </div>
        <div class="right-card-body">
          <div :class="['level1-view',{hidden:navLevel!=='level1'}]">
            <div class="service-grid">
              <button class="explore-card explore-card--scenic" @click="goLevel2('scenic')">
                <span class="explore-card-icon">🏯</span>
                <span class="explore-card-title">景点推荐</span>
                <span class="explore-card-desc">热门景点导览</span>
              </button>
              <button class="explore-card explore-card--area" @click="goLevel2('area')">
                <span class="explore-card-icon">🗺️</span>
                <span class="explore-card-title">按区域浏览</span>
                <span class="explore-card-desc">灵山景区分布</span>
              </button>
              <button class="explore-card explore-card--type" @click="goLevel2('type')">
                <span class="explore-card-icon">🏛️</span>
                <span class="explore-card-title">按类型浏览</span>
                <span class="explore-card-desc">分类发现景点</span>
              </button>
              <button class="explore-card explore-card--photo" @click="goLevel2('photo')">
                <span class="explore-card-icon">📸</span>
                <span class="explore-card-title">拍照识景</span>
                <span class="explore-card-desc">上传图片识别景点</span>
              </button>
            </div>
            <div class="hotline-section">
              <div class="hotline-section-title">景区服务</div>
              <div class="hotline-grid">
                <button
                  v-for="(h, key) in hotlineConfig"
                  :key="key"
                  class="hotline-card"
                  @click="handleHotline(key)"
                >
                  <span class="hotline-card-icon">{{ h.icon }}</span>
                  <span class="hotline-card-label">{{ h.label }}</span>
                </button>
              </div>
            </div>
          </div>

          <div :class="['level2-view',{open:navLevel==='level2'}]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="goLevel1"><span class="l2-back-arrow">←</span> 返回</button>
            </div>
            <div class="l2-scroll">
              <template v-if="navCategory==='area'">
                <div class="sub-nav-grid">
                  <button class="sub-nav-card" v-for="area in areaSubNav" :key="area.key" @click="goLevel3(area.key,area.label)">
                    <span class="sub-nav-card-icon">{{ area.icon }}</span>
                    <span class="sub-nav-card-title">{{ area.label }}</span>
                    <span class="sub-nav-card-count">{{ area.count }}个景点</span>
                  </button>
                </div>
              </template>
              <template v-else-if="navCategory==='type'">
                <div class="sub-nav-grid">
                  <button class="sub-nav-card" v-for="type in typeSubNav" :key="type.key" @click="goLevel3(type.key,type.label)">
                    <span class="sub-nav-card-icon">{{ type.icon }}</span>
                    <span class="sub-nav-card-title">{{ type.label }}</span>
                    <span class="sub-nav-card-count">{{ type.count }}个景点</span>
                  </button>
                </div>
              </template>
              <template v-else-if="navCategory==='photo'">
                <div class="photo-capture-area">
                  <button class="photo-capture-btn" @click="triggerPhotoInput">📷</button>
                  <span class="photo-capture-label">点击拍照或上传图片</span>
                </div>
                <input ref="photoInputRef" type="file" accept="image/jpeg,image/png,image/webp" class="file-hidden" @change="handlePhotoChange">
                <div v-if="photoPreview||photoError||visionResult||analyzingPhoto" class="photo-result-area">
                  <div v-if="photoPreview&&!visionResult" class="photo-preview-box">
                    <img :src="photoPreview" alt="preview">
                    <div class="photo-actions">
                      <button class="followup-btn" @click="sendPhoto" :disabled="analyzingPhoto">识别图片</button>
                      <button class="followup-btn" @click="resetPhoto">重选</button>
                    </div>
                  </div>
                  <p v-if="photoError" class="photo-error" role="alert">{{ photoError }}</p>
                  <p v-if="analyzingPhoto" class="photo-status">识别中…</p>
                  <div v-if="visionResult" class="vision-result-panel">
                    <p class="vision-summary">{{ visionResult.scene_summary || '暂未识别出明确场景。' }}</p>
                    <div class="photo-actions">
                      <button class="followup-btn" @click="askFromExploreImage" :disabled="!visionResult.retrieval_query||chatStore.streaming">向导游提问</button>
                      <button class="followup-btn" @click="resetPhoto">重新拍照</button>
                    </div>
                  </div>
                </div>
                <div class="photo-guide">
                  <div class="photo-guide-tip" v-for="tip in photoTips" :key="tip">
                    <span class="photo-guide-tip-icon">💡</span>{{ tip }}
                  </div>
                </div>
                <div class="share-section">
                  <div class="share-section-label">分享探索</div>
                  <div class="share-actions">
                    <button class="share-btn" @click="shareExplore"><span class="share-btn-icon">📋</span>复制链接</button>
                    <button class="share-btn" @click="shareExplore"><span class="share-btn-icon">💬</span>分享给朋友</button>
                  </div>
                </div>
              </template>
              <template v-else>
                <div v-for="section in currentLevel3Sections" :key="section.label">
                  <div class="scenic-section-divider">{{ section.label }}</div>
                  <button class="scenic-card" v-for="spot in section.spots" :key="spot.name" @click="askSpot(spot)">
                    <div class="scenic-card-img">
                      <img v-show="!failedImgNames.has(spot.name)" :src="spot.image" :alt="spot.name" @error="onImgError(spot.name)">
                      <span class="scenic-card-img-placeholder">{{ spot.emoji }}</span>
                    </div>
                    <div class="scenic-card-info">
                      <h4>{{ spot.name }}</h4>
                      <p>{{ spot.desc }}</p>
                    </div>
                    <div class="scenic-dot"></div>
                  </button>
                </div>
              </template>
            </div>
          </div>

          <div :class="['level3-view',{open:navLevel==='level3'}]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="goLevel2(navCategory)"><span class="l2-back-arrow">←</span> 返回{{ navCategory==='area'?'区域':navCategory==='type'?'类型':'上级' }}</button>
            </div>
            <div class="l2-scroll">
              <div v-for="section in currentLevel3Sections" :key="section.label">
                <div class="scenic-section-divider">{{ section.label }}</div>
                <button class="scenic-card" v-for="spot in section.spots" :key="spot.name" @click="askSpot(spot)">
                  <div class="scenic-card-img">
                    <img v-show="!failedImgNames.has(spot.name)" :src="spot.image" :alt="spot.name" @error="onImgError(spot.name)">
                    <span class="scenic-card-img-placeholder">{{ spot.emoji }}</span>
                  </div>
                  <div class="scenic-card-info">
                    <h4>{{ spot.name }}</h4>
                    <p>{{ spot.desc }}</p>
                  </div>
                  <div class="scenic-dot"></div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
    <div class="input-row">
      <button class="image-btn" @click="goToChatView">拍照识景</button>
      <input v-model="inputText" type="text" class="input-field" placeholder="输入问题，探索灵山景点…" :disabled="chatStore.streaming" @keydown.enter="handleSend" />
      <button class="voice-btn" @click="goToChatView">语音提问</button>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { useRouter } from "vue-router";
import { useChatStore } from "../../stores/chat";
import { useInteractionStore } from "../../stores/interaction";
import { GUIDE_PERSONA, useAvatar } from "../../composables/useAvatar";
import { renderMarkdown } from "../../composables/useMarkdown";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { analyzeImage } from "../../api/vision";
import { fetchAvatarConfig } from "../../api/admin";
import { normalizeAvatarPresetFromModelPath, DEFAULT_AVATAR_PRESET } from "../../utils/avatarConfig";
import { useScenicBackground } from "../../composables/useScenicBackground";
import { useWeather } from "../../composables/useWeather";
import ThreeAvatar from "../../components/ThreeAvatar.vue";
import AvatarDisplay from "../../components/AvatarDisplay.vue";

const router = useRouter();
const chatStore = useChatStore();
const interactionStore = useInteractionStore();
const avatar = useAvatar();
const audioPlayer = useAudioPlayer();
const { scenicBgUrl } = useScenicBackground();
const { displayText: weatherCaption, startPolling: startWeather, stopPolling: stopWeather } = useWeather();

const avatarConfig = ref({ modelKey: DEFAULT_AVATAR_PRESET, voiceType: "gentle-female" });
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

async function loadAvatarConfig() {
  try {
    const cfg = await fetchAvatarConfig();
    avatarConfig.value.modelKey = normalizeAvatarPresetFromModelPath(cfg?.model_path, DEFAULT_AVATAR_PRESET);
    avatarConfig.value.voiceType = cfg?.voice_type || "gentle-female";
  } catch { /* use defaults */ }
}

const ttsConfig = () => ({ voiceType: avatarConfig.value.voiceType, speechRate: 100, volume: 80 });
const sendOptions = {
  get base() {
    return {
      ttsConfig: ttsConfig(),
      onContext: (sel) => interactionStore.applyResolvedSelection(sel),
      onThinking: () => avatar.setState("thinking"),
      onAvatar: (p) => { try { avatar.handleAvatarEvent(p) } catch { avatarError.value = true } },
      onAudioStart: () => { activeAudioSegments.value++; avatar.setState("speaking") },
      onAudioEnded: () => { activeAudioSegments.value = Math.max(activeAudioSegments.value - 1, 0); if (activeAudioSegments.value === 0) { avatar.setState("idle"); speechProgress.value = 0; speechElapsedMs.value = 0; speechDurationMs.value = 0; visemeTimeline.value = null } },
      onSpeechProgress: (p, em, tl, ad) => { speechProgress.value = p; speechElapsedMs.value = em; speechDurationMs.value = ad; visemeTimeline.value = tl },
    };
  },
};

const activeTab = ref("chat");
const inputText = ref("");
const messageListRef = ref(null);
const sourceHighlightIndex = ref(-1);
const avatarState = avatar.currentState;
const avatarError = ref(false);
const speechProgress = ref(0);
const speechElapsedMs = ref(0);
const speechDurationMs = ref(0);
const activeAudioSegments = ref(0);
const visemeTimeline = ref(null);
const photoInputRef = ref(null);
const photoPreview = ref("");
const photoFile = ref(null);
const analyzingPhoto = ref(false);
const photoError = ref("");
const visionResult = ref(null);

const AVATAR_MODEL_MAP = {
  monk: { name: "宁灵", subtitle: "宁灵 · 佛学文化导游" },
  hanfu: { name: "清岚", subtitle: "清岚 · 文化叙事导游" },
  modern: { name: "景行", subtitle: "景行 · 智能导览导游" },
};
const avatarDisplaySubtitle = computed(() => AVATAR_MODEL_MAP[avatarConfig.value.modelKey]?.subtitle || "清岚 · 数字人导游");

const avatarReady = computed(() => !avatarError.value);
const voiceReady = computed(() => true);
const replyStatusClass = computed(() => {
  if (chatStore.streaming) return 'status-pill--live';
  if (avatarState.value === 'thinking') return 'status-pill--loading';
  return 'status-pill--ready';
});
const replyStatusText = computed(() => {
  if (chatStore.streaming) return '正在回答';
  if (avatarState.value === 'thinking') return '思考中';
  return '等待提问';
});

const feedbackReasons = [
  { value: "accurate", label: "回答准确" },
  { value: "insufficient", label: "信息不足" },
  { value: "slow", label: "回复太慢" },
  { value: "irrelevant", label: "答非所问" },
  { value: "other", label: "其他原因" },
];

const hotlineConfig = {
  broadcast: { label: '广播找人', icon: '📢', desc: '寻人广播·游客中心', number: '0510-85688631' },
  complaint: { label: '景区投诉', icon: '📋', desc: '服务投诉建议', number: '400-168-0303转5' },
  emergency: { label: '医疗急救', icon: '🩺', desc: '紧急医疗救助', number: '0510-85688120' },
};

function handleHotline(type) {
  if (chatStore.streaming) return;
  const h = hotlineConfig[type];
  if (!h) return;
  chatStore.messages.push({ role: 'assistant', content: `【${h.label}】请拨打景区服务热线：${h.number}` });
}

function handleAvatarLoaded() { avatarError.value = false; }
function handleAvatarLoadError() { avatarError.value = true; }

function askCard(query) { if (chatStore.streaming) return; chatStore.sendMessage(query, interactionStore.selectionPayload, sendOptions.base); }
function askRecommend() { goLevel2("scenic"); }
function askPhoto() { goLevel2("photo"); }
function askRoute() { goLevel2("area"); }
function askCulture() { goLevel2("type"); }

function handleSend() {
  const t = inputText.value.trim(); if (!t || chatStore.streaming) return;
  chatStore.sendMessage(t, interactionStore.selectionPayload, sendOptions.base);
  inputText.value = "";
}
function handleRetry() { chatStore.retryLastMessage(); }
function handleFollowup(fu) { chatStore.sendMessage(fu.query || fu.label || fu, interactionStore.selectionPayload, sendOptions.base); }

function handleCitationClick(e) {
  const cite = e.target?.closest(".citation");
  if (!cite) return;
  const evidenceId = cite.dataset.evidenceId;
  const index = chatStore.sources.findIndex(s => s.evidence_id === `证据${evidenceId}`);
  if (index >= 0) { activeTab.value = "source"; sourceHighlightIndex.value = index; nextTick(() => { document.querySelector(`[data-source-index="${index}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }); }); setTimeout(() => { sourceHighlightIndex.value = -1; }, 2000); }
}

function renderAnswer(content, isLastMessage) {
  return renderMarkdown(content, chatStore.sources, chatStore.streaming && isLastMessage);
}

function scrollToBottom() { nextTick(() => { if (messageListRef.value) messageListRef.value.scrollTop = messageListRef.value.scrollHeight; }); }
watch(() => chatStore.messages.length, () => scrollToBottom());
watch(() => { const msgs = chatStore.messages; return msgs.length > 0 ? msgs[msgs.length - 1].content : ""; }, () => scrollToBottom());

function handlePhotoChange(e) {
  const f = e.target.files?.[0]; photoError.value = ""; visionResult.value = null;
  if (!f) return;
  if (!f.type.startsWith("image/")) { photoError.value = "仅支持图片文件。"; e.target.value = ""; return; }
  if (f.size > MAX_IMAGE_BYTES) { photoError.value = "图片不能超过 5MB。"; e.target.value = ""; return; }
  photoFile.value = f;
  const r = new FileReader(); r.onload = ev => { photoPreview.value = ev.target.result; }; r.readAsDataURL(f);
}

async function sendPhoto() {
  if (!photoFile.value || analyzingPhoto.value) return;
  analyzingPhoto.value = true; photoError.value = ""; visionResult.value = null;
  avatar.triggerAction("look_around");
  try { visionResult.value = await analyzeImage(photoFile.value); }
  catch (err) { photoError.value = err?.message || "识别失败，请重试"; }
  finally { analyzingPhoto.value = false; }
}

function askFromExploreImage() {
  const q = visionResult.value?.retrieval_query?.trim(); if (!q) return;
  chatStore.sendMessage("请根据这张图片识别出的线索，基于官方资料介绍它最可能对应的景区景点。", interactionStore.selectionPayload, { ...sendOptions.base, visionContext: visionResult.value, displayQuery: q });
}

function resetPhoto() { photoPreview.value = ""; photoFile.value = null; if (photoInputRef.value) photoInputRef.value.value = ""; photoError.value = ""; visionResult.value = null; }

function handleBack() { chatStore.stopOutput(); audioPlayer.stop(); router.push("/tourist/select?index=1").catch(() => {}); }

function goToChatView() {
  router.push("/tourist").catch(() => {});
}

function triggerPhotoInput() { photoInputRef.value?.click(); }

function shareExplore() {
  navigator.clipboard?.writeText(window.location.href).catch(() => {});
}

const photoTips = [
  "拍摄完整建筑主体，识别更准确",
  "尽量避免逆光或大面积遮挡",
  "支持识别佛像、殿堂、塔等建筑",
  "识别结果仅供参考，以现场导览为准",
];

const scenicSpots = [
  { name: "灵山大佛", emoji: "🗿", desc: "88米高青铜释迦牟尼佛像，灵山景区标志", zone: "qianshan", type: "foxiang", image: "/assets/slides/灵山大佛.png" },
  { name: "九龙灌浴", emoji: "🐉", desc: "大型动态音乐群雕，再现佛祖诞生盛景", zone: "qianshan", type: "foxiang", image: "/assets/slides/九龙灌浴.png" },
  { name: "降魔浮雕", emoji: "🪨", desc: "青铜浮雕艺术长墙，讲述佛陀修行故事", zone: "qianshan", type: "wenhua", image: "/assets/slides/降魔浮雕.png" },
  { name: "阿育王柱", emoji: "🪷", desc: "古印度风格石柱，铭刻阿育王经文", zone: "qianshan", type: "wenhua", image: "/assets/slides/阿育王柱_1.png" },
  { name: "百子戏弥勒", emoji: "😊", desc: "大型青铜雕塑群，弥勒与百名童子嬉戏", zone: "qianshan", type: "foxiang", image: "/assets/slides/百子戏弥勒.png" },
  { name: "灵山梵宫", emoji: "🏰", desc: "佛教艺术殿堂，世界佛教论坛永久会址", zone: "houshan", type: "simiao", image: "/assets/slides/灵山梵宫.png" },
  { name: "五印坛城", emoji: "🏔️", desc: "藏传佛教风格建筑，金顶辉煌庄严", zone: "houshan", type: "simiao", image: "/assets/slides/五印坛城.png" },
  { name: "曼飞龙塔", emoji: "🕌", desc: "南传佛教风格白塔群，异域风情浓郁", zone: "houshan", type: "wenhua", image: "/assets/slides/曼飞龙塔.png" },
  { name: "无尽意斋", emoji: "🍵", desc: "禅意茶道空间，静心品味人生", zone: "houshan", type: "simiao", image: "/assets/slides/无尽意斋.png" },
  { name: "佛教文化博览馆", emoji: "🔔", desc: "动态升降佛塔，佛教科技艺术融合", zone: "houshan", type: "wenhua", image: "/assets/slides/佛教文化博览馆.png" },
  { name: "菩提大道", emoji: "🌳", desc: "景观步道，两侧菩提树绿荫如盖", zone: "huqu", type: "ziran", image: "/assets/slides/菩提大道.png" },
  { name: "五灯湖", emoji: "🌊", desc: "风景如画的湖面，波光粼粼", zone: "huqu", type: "ziran", image: "/assets/slides/五灯湖.png" },
  { name: "拈花广场", emoji: "🌸", desc: "湖畔集散广场，莲花造型铺装", zone: "huqu", type: "ziran", image: "/assets/slides/沾化广场.png" },
  { name: "香月花街", emoji: "🏘️", desc: "古色古香的商业步行街", zone: "huqu", type: "ziran", image: "/assets/slides/香月花街.png" },
  { name: "梵天花海", emoji: "🌺", desc: "壮观的花海景观，四季换景", zone: "huqu", type: "ziran", image: "/assets/slides/梵天花海_1.png" },
  { name: "鹿鸣谷", emoji: "🦌", desc: "生态自然谷地，鹿鸣声声", zone: "huqu", type: "ziran", image: "/assets/slides/鹿鸣谷.png" },
  { name: "灵山大照壁", emoji: "🧱", desc: "入口照壁浮雕，镌刻灵山胜境四字", zone: "guangchang", type: "wenhua", image: "/assets/slides/灵山大照壁.png" },
  { name: "佛足坛", emoji: "🦶", desc: "佛足迹石刻，信众朝拜祈福之地", zone: "guangchang", type: "wenhua", image: "/assets/slides/佛足坛.png" },
  { name: "五智门", emoji: "🚪", desc: "牌坊式山门，五门象征五智", zone: "guangchang", type: "wenhua", image: "/assets/slides/五智门.png" },
  { name: "五明桥", emoji: "🌉", desc: "汉白玉石拱桥，横跨香水海", zone: "guangchang", type: "foxiang", image: "/assets/slides/五明桥.png" },
  { name: "祥符禅寺", emoji: "🏯", desc: "千年古刹，灵山佛教文化发源地", zone: "guangchang", type: "simiao", image: "/assets/slides/祥符禅寺.png" },
  { name: "拈花堂", emoji: "⛩️", desc: "景区入口广场，开启灵山之旅", zone: "guangchang", type: "wenhua", image: "/assets/slides/拈花堂.png" },
];

const areaSubNav = [
  { key: "qianshan", label: "前山区", icon: "⛰️", count: 5 },
  { key: "houshan", label: "后山区", icon: "🏔️", count: 5 },
  { key: "huqu", label: "湖区", icon: "🌊", count: 6 },
  { key: "guangchang", label: "广场区", icon: "🏛️", count: 6 },
];

const typeSubNav = [
  { key: "foxiang", label: "佛像建筑", icon: "🗿", count: 4 },
  { key: "ziran", label: "自然景观", icon: "🌳", count: 6 },
  { key: "simiao", label: "寺庙殿堂", icon: "🏯", count: 4 },
  { key: "wenhua", label: "文化展馆", icon: "🏛️", count: 8 },
];

const navLevel = ref("level1");
const navCategory = ref("");
const navSubCategory = ref("");
const failedImgNames = ref(new Set());

const navTitleLabelMap = {
  scenic: "景点推荐",
  area: "按区域浏览",
  type: "按类型浏览",
  photo: "拍照识景",
  qianshan: "前山区景点",
  houshan: "后山区景点",
  huqu: "湖区景点",
  guangchang: "广场区景点",
  foxiang: "佛像建筑",
  ziran: "自然景观",
  simiao: "寺庙殿堂",
  wenhua: "文化展馆",
};

const navTitle = computed(() => {
  if (navLevel.value === "level2") return navTitleLabelMap[navCategory.value] || "";
  if (navLevel.value === "level3") return navTitleLabelMap[navSubCategory.value] || "";
  return "探索工具";
});

function goLevel1() {
  navLevel.value = "level1";
  navCategory.value = "";
  navSubCategory.value = "";
}

function goLevel2(category) {
  navLevel.value = "level2";
  navCategory.value = category;
  navSubCategory.value = "";
  if (category === "scenic") {
    navSubCategory.value = "all";
  }
}

function goLevel3(subKey, subLabel) {
  navLevel.value = "level3";
  navSubCategory.value = subKey;
}

const currentLevel3Sections = computed(() => {
  const key = navSubCategory.value;
  if (!key) return [];

  if (key === "all" || key === "scenic") {
    const zoneOrder = ["qianshan", "houshan", "huqu", "guangchang"];
    const zoneLabels = { qianshan: "前山区", houshan: "后山区", huqu: "湖区", guangchang: "广场区" };
    return zoneOrder
      .map(z => ({
        label: zoneLabels[z],
        spots: scenicSpots.filter(s => s.zone === z),
      }))
      .filter(s => s.spots.length > 0);
  }

  if (["qianshan", "houshan", "huqu", "guangchang"].includes(key)) {
    const zoneLabels = { qianshan: "前山区", houshan: "后山区", huqu: "湖区", guangchang: "广场区" };
    return [{ label: zoneLabels[key], spots: scenicSpots.filter(s => s.zone === key) }];
  }

  if (["foxiang", "ziran", "simiao", "wenhua"].includes(key)) {
    const typeLabels = { foxiang: "佛像建筑", ziran: "自然景观", simiao: "寺庙殿堂", wenhua: "文化展馆" };
    return [{ label: typeLabels[key], spots: scenicSpots.filter(s => s.type === key) }];
  }

  return [];
});

function askSpot(spot) {
  if (chatStore.streaming) return;
  chatStore.sendMessage(`请详细介绍灵山景区的"${spot.name}"，包括历史背景、建筑特色和文化内涵。`, interactionStore.selectionPayload, sendOptions.base);
}

function onImgError(name) {
  failedImgNames.value.add(name);
  nextTick(() => {});
}

onMounted(() => { interactionStore.initialize(); loadAvatarConfig(); startWeather(); });
onBeforeUnmount(() => { chatStore.stopOutput(); audioPlayer.stop(); avatar.setState("idle"); stopWeather(); });
</script>

<style scoped>
/* ============================================================
   DARK THEME TOURIST PAGE - aligned to design-redesign spec
   ============================================================ */
.tourist-page {
  position: relative;
  width: 100%; height: 100vh; height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1a1612;
  color: #f0ece5;
  color-scheme: dark;
}

.scenic-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.scenic-bg-img {
  position: absolute; inset: 0;
  background-position: center; background-repeat: no-repeat; background-size: cover;
  filter: blur(10px) saturate(0.3) brightness(0.4);
  transform: scale(1.06);
}
.scenic-bg-overlay {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 60% 40% at 50% 35%, transparent 0%, rgba(20,16,10,0.55) 80%),
    radial-gradient(ellipse 80% 50% at 50% 100%, rgba(22,18,10,0.5) 0%, transparent 70%);
}

.back-btn {
  position: absolute; top: clamp(10px, 2vw, 32px); left: clamp(10px, 2vw, 32px); z-index: 25;
  display: inline-flex; align-items: center; gap: 6px;
  padding: clamp(8px, 0.9vw, 14px) clamp(16px, 1.8vw, 28px);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 999px;
  background: rgba(255,250,242,0.05);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  color: rgba(232,228,219,0.55);
  font-family: inherit; font-size: clamp(14px, 1.2vw, 20px);
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
  outline: none;
}
.back-btn:hover {
  border-color: rgba(255,250,242,0.19);
  background: rgba(255,255,255,0.09);
  color: rgba(232,228,219,0.85);
}
.back-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 3px; }

.top-right {
  position: absolute; top: clamp(10px, 2vw, 32px); right: clamp(10px, 2vw, 32px); z-index: 20;
  display: flex; flex-direction: column;
  align-items: flex-end; gap: 8px;
}
.top-brand {
  color: rgba(232,228,219,0.88);
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: clamp(24px, 2.8vw, 40px);
  font-weight: 400;
  letter-spacing: 0.12em;
  text-shadow: 0 0 30px rgba(217,164,65,0.1);
  line-height: 1.2;
}
.top-status-row {
  display: flex; flex-direction: column; gap: 5px;
}
.status-item {
  display: flex; align-items: center; gap: 8px;
  font-size: clamp(13px, 0.9vw, 17px); font-weight: 400;
  letter-spacing: 0.06em;
  color: rgba(232,228,219,0.55);
  font-family: system-ui, sans-serif;
}
.status-dot {
  width: 12px; height: 12px;
  border-radius: 50%; flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
}
.status-dot--ready  { background: #d9a441; box-shadow: 0 0 4px rgba(217,164,65,0.5); }
.status-dot--live   { background: #5ec9a4; box-shadow: 0 0 4px rgba(94,201,164,0.5); }
.status-dot--weather { background: #6bb8e8; box-shadow: 0 0 4px rgba(107,184,232,0.5); }

.tourist-stage {
  position: relative; z-index: 10;
  flex: 1; min-height: 0;
  display: grid;
  grid-template-columns: minmax(clamp(160px, 12vw, 260px), clamp(240px, 17vw, 350px)) 1fr minmax(clamp(160px, 12vw, 260px), clamp(240px, 17vw, 350px));
  gap: clamp(8px, 1vw, 16px);
  align-items: stretch;
  padding: 20px clamp(10px, 1.5vw, 24px) 0;
  margin-top: 0;
}

.chat-center {
  grid-column: 2; grid-row: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  position: relative; z-index: 2;
  width: 100%; height: 100%;
  min-height: 0;
  padding: 0 8px;
}
.top-caption {
  position: absolute;
  top: 16px; left: 50%; transform: translateX(-50%);
  z-index: 20;
  display: flex; align-items: baseline; justify-content: center; gap: 12px;
  white-space: nowrap;
}
.caption-kicker {
  color: #f8e7bb;
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(18px, 2vw, 28px); font-weight: 700; letter-spacing: 0.1em;
  text-shadow: 0 0 20px rgba(217,164,65,0.15);
}
.caption-weather {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(23,18,14,0.6);
  color: rgba(232,228,219,0.38);
  font-family: system-ui, sans-serif;
  font-size: clamp(12px, 0.8vw, 14px); font-weight: 400;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.caption-weather-live {
  color: rgba(232,228,219,0.55);
}
.crowd-indicator {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(23,18,14,0.6);
  font-size: 13px; font-weight: 400;
  color: rgba(232,228,219,0.55);
  letter-spacing: 0.04em;
  font-family: system-ui, sans-serif;
  white-space: nowrap;
  cursor: default;
}
.crowd-dot {
  width: 12px; height: 12px;
  border-radius: 50%; flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
}
.crowd-indicator[data-level="green"] .crowd-dot { background: #5ec9a4; }

.avatar-stage {
  position: relative; z-index: 2;
  width: min(clamp(360px, 34vw, 650px), 100vw);
  height: calc(min(clamp(360px, 42vh, 560px), 66vh) + 140px);
  padding-top: 140px;
  margin: -140px auto 0;
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  background: transparent;
  box-sizing: border-box;
}
.avatar-stage::after {
  content: "";
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 140px;
  z-index: 3;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent 0%, #1a1612 100%);
}
.avatar-stage :deep(.three-wrapper),
.avatar-stage :deep(.avatar-display) {
  width: 100%; height: 100%;
  transform: translateY(8%);
}

.side-card {
  position: absolute;
  left: clamp(12px, 1.5vw, 28px); bottom: clamp(60px, 7vh, 120px);
  z-index: 15;
  width: clamp(260px, 17vw, 420px); height: clamp(340px, 52vh, 500px);
  background: rgba(23,18,14,0.88);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 10px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.side-card.speaking {
  animation: card-breathe 3s ease-in-out infinite;
}
@keyframes card-breathe {
  0%, 100% { box-shadow: 0 0 0 rgba(217,164,65,0); }
  50% { box-shadow: 0 0 40px rgba(217,164,65,0.08); }
}
.side-card-head {
  flex-shrink: 0;
  position: relative;
}
.side-card-tabs {
  display: flex;
}
.side-card-tab {
  flex: 1;
  padding: 7px 0;
  border: none;
  background: transparent;
  color: rgba(232,228,219,0.35);
  font-family: inherit; font-size: clamp(14px, 0.9vw, 17px);
  font-weight: 600; letter-spacing: 0.06em;
  cursor: pointer;
  transition: color 0.25s ease;
  position: relative;
}
.side-card-tab:hover { color: rgba(232,228,219,0.7); }
.side-card-tab.active { color: rgba(232,228,219,0.75); }
.side-card-tab.active::after {
  content: "";
  position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 24px; height: 2px;
  border-radius: 1px;
  background: #d9a441;
}
.side-card-body {
  flex: 1; min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px 12px;
  display: flex; flex-direction: column;
  gap: 10px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.15) transparent;
}
.side-card-body.hidden { display: none; }
.side-card-body::-webkit-scrollbar { width: 4px; }
.side-card-body::-webkit-scrollbar-track { background: transparent; }
.side-card-body::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.15); border-radius: 2px; }
.side-card-body::-webkit-scrollbar-thumb:hover { background: rgba(217,164,65,0.25); }

.msg-item { display: flex; flex-direction: column; }
.msg-item.assistant { align-items: flex-start; }
.msg-item.user { align-items: flex-end; }
.msg-item.user.collapsed { gap: 4px; }
.msg-item.user.collapsed .msg-bubble {
  max-height: 24px; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis;
  opacity: 0.45; font-size: 16px;
  padding: 4px 10px; border-radius: 6px;
  border-bottom-right-radius: 2px;
}
.msg-bubble {
  max-width: 90%;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 15px; line-height: 1.5;
  letter-spacing: 0.03em;
  word-break: break-word;
}
.msg-item.user .msg-bubble {
  background: rgba(217,164,65,0.12);
  border: none;
  color: rgba(232,228,219,0.9);
  border-bottom-right-radius: 4px;
}
.msg-item.assistant .msg-bubble {
  background: rgba(232,228,219,0.05);
  border: none;
  color: rgba(232,228,219,0.85);
  border-bottom-left-radius: 4px;
}
.typing-cursor {
  animation: blink 0.8s infinite;
  color: #d9a441;
  font-weight: 700; font-size: 16px; margin-left: 4px;
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

.followup-panel {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 12px;
  border: 1px solid rgba(248,231,187,0.16);
  border-radius: 14px;
  background: rgba(255,248,232,0.06);
}
.followup-panel button {
  padding: 8px 14px;
  border: 1px solid rgba(248,231,187,0.2);
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  color: #f8e7bb; font-size: clamp(13px, 0.8vw, 15px);
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}
.followup-panel button:hover:not(:disabled) {
  background: rgba(255,255,255,0.16);
  border-color: rgba(248,231,187,0.42);
  transform: translateY(-1px);
}
.followup-panel button:disabled { opacity: 0.5; cursor: not-allowed; }

.source-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
.source-item {
  padding: 10px;
  border: 1px solid rgba(232,228,219,0.08);
  border-radius: 8px;
  background: rgba(232,228,219,0.04);
  transition: border-color 0.3s ease, background 0.3s ease;
}
.source-item:hover { border-color: rgba(232,228,219,0.20); background: rgba(232,228,219,0.08); }
.source-item.highlight {
  border-color: rgba(217,164,65,0.5);
  background: rgba(217,164,65,0.08);
}
.source-item h4 {
  display: flex; align-items: center; gap: 6px;
  margin: 0 0 5px;
  color: rgba(232,228,219,0.85); font-size: 18px; font-weight: 600;
}
.source-num {
  display: inline-flex; flex-shrink: 0;
  align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  background: rgba(217,164,65,0.2);
  color: #d9a441; font-size: 13px; font-weight: 700;
}
.source-item p {
  margin: 0 0 3px;
  color: rgba(232,228,219,0.55); font-size: 14px; line-height: 1.5;
}
.source-meta { color: rgba(232,228,219,0.3); font-size: 13px; }
.source-empty { color: rgba(240,242,236,0.52); text-align: center; padding: 60px 0; font-size: 15px; }

.stop-notice { text-align: center; padding: 8px; color: rgba(248,231,187,0.6); font-size: 14px; }
.error-notice { text-align: center; padding: 8px; color: #f87171; font-size: 14px; }

.right-card {
  position: absolute;
  right: clamp(12px, 1.5vw, 28px); top: clamp(80px, 8vh, 130px); bottom: clamp(60px, 7vh, 120px);
  z-index: 15;
  width: clamp(270px, 18vw, 450px);
  background: rgba(23,18,14,0.88);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 10px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.right-card-head {
  flex-shrink: 0;
  position: relative;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(232,228,219,0.06);
  color: rgba(232,228,219,0.5);
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(12px, 0.8vw, 14px); font-weight: 600;
  letter-spacing: 0.06em;
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
}
.right-card-body {
  flex: 1; min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px 12px;
  display: flex; flex-direction: column;
  gap: 6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.15) transparent;
}
.right-card-body::-webkit-scrollbar { width: 4px; }
.right-card-body::-webkit-scrollbar-track { background: transparent; }
.right-card-body::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.15); border-radius: 2px; }
.right-card-body::-webkit-scrollbar-thumb:hover { background: rgba(217,164,65,0.25); }

.service-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 8px;
}
.explore-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: clamp(6px, 0.5vw, 10px);
  padding: clamp(10px, 1.2vw, 18px) clamp(6px, 0.8vw, 14px);
  border-radius: 8px;
  border: 1px solid rgba(232,228,219,0.10);
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  text-align: center; min-height: 0;
  transition: border-color 0.3s ease, background 0.3s ease;
  outline: none; position: relative; overflow: hidden;
  font-family: inherit; color: inherit;
}
.explore-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.06);
}
.explore-card:active { transform: scale(0.96); }
.explore-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.explore-card-icon {
  width: clamp(44px, 3vw, 64px); height: clamp(44px, 3vw, 64px); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: clamp(22px, 1.6vw, 32px); flex-shrink: 0;
  transition: transform 0.3s ease;
}
.explore-card:hover .explore-card-icon { transform: scale(1.1); }
.explore-card--scenic .explore-card-icon { background: rgba(217,164,65,0.15); color: #d9a441; }
.explore-card--area   .explore-card-icon { background: rgba(94,201,164,0.15); color: #5ec9a4; }
.explore-card--type   .explore-card-icon { background: rgba(107,184,232,0.15); color: #6bb8e8; }
.explore-card--photo  .explore-card-icon { background: rgba(232,168,64,0.15); color: #e8a840; }
.explore-card-title {
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: clamp(16px, 1.3vw, 24px); font-weight: 600;
  color: rgba(232,228,219,0.82);
  letter-spacing: 0.05em; line-height: 1.3;
}
.explore-card-desc {
  font-size: clamp(12px, 0.8vw, 15px); font-weight: 400;
  color: rgba(232,228,219,0.3);
  letter-spacing: 0.04em; line-height: 1.2;
  font-family: system-ui, sans-serif;
}

/* ---------- hotline section ---------- */
.hotline-section {
  margin-top: clamp(1px, 0.15vw, 4px);
  padding-top: clamp(8px, 0.8vw, 14px);
  border-top: 1px solid rgba(232,228,219,0.08);
}
.hotline-section-title {
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(10px, 0.7vw, 13px); font-weight: 600;
  color: rgba(232,228,219,0.35);
  letter-spacing: 0.06em;
  margin-bottom: clamp(5px, 0.5vw, 10px);
  padding: 0 2px;
}
.hotline-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: clamp(4px, 0.4vw, 8px);
}
.hotline-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: clamp(2px, 0.2vw, 5px);
  padding: clamp(4px, 0.5vw, 10px) clamp(2px, 0.3vw, 6px);
  border-radius: clamp(6px, 0.5vw, 10px);
  border: 1px solid rgba(232,228,219,0.10);
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease;
  outline: none; min-width: 0;
  font-family: inherit; color: inherit;
}
.hotline-card:hover {
  border-color: rgba(248,113,113,0.35);
  background: rgba(248,113,113,0.06);
}
.hotline-card:active { transform: scale(0.96); }
.hotline-card:focus-visible { outline: 2px solid #f87171; outline-offset: 2px; }
.hotline-card-icon {
  font-size: clamp(14px, 1.2vw, 22px); flex-shrink: 0;
  transition: transform 0.25s ease;
}
.hotline-card:hover .hotline-card-icon { transform: scale(1.12); }
.hotline-card-label {
  font-size: clamp(9px, 0.6vw, 12px); font-weight: 500;
  color: rgba(232,228,219,0.6);
  letter-spacing: 0.03em;
  line-height: 1.2;
}

.input-row {
  position: absolute;
  bottom: clamp(24px, 2.5vh, 40px); left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  width: min(clamp(420px, 42vw, 800px), 88vw);
  display: flex; align-items: center; justify-content: center; gap: 12px;
}
.input-field {
  flex: 1;
  height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(16px, 1.5vw, 28px);
  border: 1px solid rgba(232,228,219,0.12);
  border-radius: 10px;
  background: rgba(23,18,14,0.78);
  color: rgba(232,228,219,0.82);
  font-family: inherit; font-size: clamp(16px, 1.2vw, 24px);
  letter-spacing: 0.03em;
  outline: none;
  transition: border-color 0.25s ease;
}
.input-field::placeholder { color: rgba(232,228,219,0.25); font-size: clamp(15px, 1.1vw, 22px); }
.input-field:focus { border-color: rgba(217,164,65,0.35); }
.input-field:disabled { opacity: 0.5; }

.voice-btn {
  flex-shrink: 0; width: auto; height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(14px, 1.8vw, 32px);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(217,164,65,0.3);
  border-radius: 999px;
  background: rgba(217,164,65,0.14);
  color: #d9a441;
  font-family: inherit; font-size: clamp(16px, 1.2vw, 24px); font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
  outline: none; white-space: nowrap;
}
.voice-btn:hover {
  border-color: rgba(217,164,65,0.45);
  background: rgba(217,164,65,0.2);
  box-shadow: 0 0 20px rgba(217,164,65,0.15);
}
.voice-btn:active { transform: scale(0.95); }
.voice-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 3px; }

.image-btn {
  flex-shrink: 0; width: auto; height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(14px, 1.4vw, 28px);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(94,201,164,0.25);
  border-radius: 999px;
  background: rgba(94,201,164,0.1);
  color: #5ec9a4;
  font-family: inherit; font-size: clamp(15px, 1.1vw, 22px); font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
  outline: none; white-space: nowrap;
}
.image-btn:hover {
  border-color: rgba(94,201,164,0.45);
  background: rgba(94,201,164,0.2);
  box-shadow: 0 0 20px rgba(94,201,164,0.15);
}
.image-btn:active { transform: scale(0.95); }
.image-btn:focus-visible { outline: 2px solid #5ec9a4; outline-offset: 3px; }

/* ---------- level navigation ---------- */
.level1-view {
  display: flex; flex: 1; min-height: 0; flex-direction: column;
}
.level1-view.hidden { display: none; }
.level2-view {
  display: none;
  flex: 1; min-height: 0;
  flex-direction: column;
}
.level2-view.open { display: flex; }
.level3-view {
  display: none;
  flex: 1; min-height: 0;
  flex-direction: column;
}
.level3-view.open { display: flex; }
.l2-back-row {
  flex-shrink: 0;
  padding: 0 12px 8px;
}
.l2-back-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 0;
  border: none; background: transparent;
  color: rgba(232,228,219,0.4);
  font-family: inherit; font-size: clamp(13px, 0.9vw, 16px); cursor: pointer;
  transition: color 0.25s ease;
}
.l2-back-btn:hover { color: #d9a441; }
.l2-back-arrow { font-size: 18px; transition: transform 0.3s ease; }
.l2-back-btn:hover .l2-back-arrow { transform: translateX(-2px); }
.l2-scroll {
  flex: 1; min-height: 0;
  overflow-y: auto; padding: 0 12px 8px;
  display: flex; flex-direction: column; gap: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.1) transparent;
}
.l2-scroll::-webkit-scrollbar { width: 3px; }
.l2-scroll::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.1); border-radius: 2px; }
.l2-scroll::-webkit-scrollbar-track { background: transparent; }

/* ---------- scenic card with thumbnail ---------- */
.scenic-card {
  display: flex; align-items: center; gap: 10px;
  padding: 8px;
  border: 1px solid rgba(232,228,219,0.10);
  border-radius: 8px;
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease;
  outline: none; font-family: inherit; color: inherit;
}
.scenic-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.05);
}
.scenic-card:active { transform: scale(0.97); }
.scenic-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.scenic-card-img {
  width: 58px; height: 58px;
  flex-shrink: 0;
  border-radius: 6px;
  border: 1px solid rgba(217,164,65,0.25);
  background: rgba(232,228,219,0.04);
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.scenic-card-img img {
  width: 100%; height: 100%;
  object-fit: cover; display: block;
}
.scenic-card-img-placeholder {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: rgba(217,164,65,0.25);
  font-size: 12px; font-weight: 600;
  font-family: system-ui, sans-serif;
  letter-spacing: 0.03em;
}
.scenic-card-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.scenic-card-info h4 {
  margin: 0;
  color: rgba(232,228,219,0.82); font-size: clamp(15px, 1.1vw, 18px); font-weight: 600;
  letter-spacing: 0.04em; line-height: 1.3;
}
.scenic-card-info p {
  margin: 0; color: rgba(232,228,219,0.33);
  font-size: clamp(12px, 0.8vw, 14px); line-height: 1.4;
  letter-spacing: 0.03em;
}
.scenic-dot {
  width: 8px; height: 8px; border-radius: 2px;
  background: #d9a441; flex-shrink: 0;
}
.scenic-section-divider {
  padding: 6px 0 2px;
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(11px, 0.8vw, 14px); font-weight: 600;
  color: rgba(217,164,65,0.45);
  letter-spacing: 0.06em;
  text-align: center;
  border-bottom: 1px solid rgba(217,164,65,0.10);
  margin-bottom: 2px;
}

/* ---------- sub-nav grid ---------- */
.sub-nav-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px 8px;
  flex: 1;
  align-content: start;
}
.sub-nav-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: 8px;
  border: 1px solid rgba(232,228,219,0.10);
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  text-align: center;
  min-height: 72px;
  transition: border-color 0.3s ease, background 0.3s ease;
  outline: none;
  font-family: inherit; color: inherit;
}
.sub-nav-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.06);
}
.sub-nav-card:active { transform: scale(0.96); }
.sub-nav-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.sub-nav-card-icon { font-size: clamp(24px, 2vw, 32px); line-height: 1; }
.sub-nav-card-title {
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: clamp(16px, 1.2vw, 20px); font-weight: 600;
  color: rgba(232,228,219,0.82);
  letter-spacing: 0.05em; line-height: 1.2;
}
.sub-nav-card-count {
  font-size: clamp(12px, 0.8vw, 14px); font-weight: 400;
  color: rgba(232,228,219,0.3);
  letter-spacing: 0.04em;
  font-family: system-ui, sans-serif;
}

/* ---------- photo section ---------- */
.photo-capture-area {
  flex-shrink: 0;
  display: flex; flex-direction: column;
  align-items: center; gap: 10px;
  padding: 16px 0 10px;
}
.photo-capture-btn {
  width: 72px; height: 72px;
  border-radius: 50%;
  border: 2px solid rgba(232,168,64,0.4);
  background: rgba(232,168,64,0.12);
  color: #e8a840; font-size: 28px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: border-color 0.3s ease, background 0.3s ease;
  outline: none;
  font-family: inherit;
}
.photo-capture-btn:hover {
  border-color: rgba(232,168,64,0.7);
  background: rgba(232,168,64,0.22);
}
.photo-capture-btn:active { transform: scale(0.92); }
.photo-capture-btn:focus-visible { outline: 2px solid #e8a840; outline-offset: 3px; }
.photo-capture-label {
  color: rgba(232,228,219,0.5);
  font-size: 12px; font-weight: 400;
  letter-spacing: 0.04em;
  font-family: "STKaiti","KaiTi",serif;
}

.photo-result-area { display: flex; flex-direction: column; gap: 8px; }
.photo-preview-box { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.photo-preview-box img { max-width: 100%; max-height: 140px; border-radius: 8px; border: 1px solid rgba(248,231,187,0.14); }
.photo-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.photo-actions .followup-btn {
  padding: 6px 12px;
  border: 1px solid rgba(248,231,187,0.2);
  border-radius: 999px;
  background: rgba(255,255,255,0.06);
  color: #f8e7bb; font-size: 12px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.18s ease, border-color 0.18s ease;
}
.photo-actions .followup-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.14);
  border-color: rgba(248,231,187,0.4);
}
.photo-actions .followup-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.photo-error { font-size: 12px; color: #f87171; }
.photo-status { font-size: 12px; color: rgba(232,228,219,0.5); }
.file-hidden { display: none; }
.vision-summary { color: rgba(240,242,236,0.85); font-size: 13px; line-height: 1.5; margin: 0; }

/* ---------- share section ---------- */
.share-section {
  flex-shrink: 0;
  margin: 0 8px 8px;
  padding: 10px;
  border: 1px solid rgba(232,228,219,0.08);
  border-radius: 8px;
  background: rgba(232,228,219,0.03);
}
.share-section-label {
  font-size: 14px; font-weight: 600;
  color: rgba(232,228,219,0.4);
  letter-spacing: 0.05em;
  margin-bottom: 8px;
  font-family: "STKaiti","KaiTi",serif;
}
.share-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.share-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 12px;
  border: 1px solid rgba(232,228,219,0.12);
  border-radius: 8px;
  background: rgba(232,228,219,0.04);
  color: rgba(232,228,219,0.6);
  font-family: inherit; font-size: 14px;
  font-weight: 500; letter-spacing: 0.03em;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease, color 0.25s ease;
  outline: none;
}
.share-btn:hover {
  border-color: rgba(217,164,65,0.3);
  background: rgba(217,164,65,0.08);
  color: #d9a441;
}
.share-btn:active { transform: scale(0.95); }
.share-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.share-btn-icon { font-size: 14px; flex-shrink: 0; }

/* ---------- photo guide ---------- */
.photo-guide {
  flex: 1; min-height: 0;
  overflow-y: auto;
  padding: 0 8px 8px;
  display: flex; flex-direction: column; gap: 6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.1) transparent;
}
.photo-guide::-webkit-scrollbar { width: 3px; }
.photo-guide::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.1); border-radius: 2px; }
.photo-guide::-webkit-scrollbar-track { background: transparent; }
.photo-guide-tip {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 8px;
  border: 1px solid rgba(232,228,219,0.06);
  border-radius: 6px;
  background: rgba(232,228,219,0.02);
  font-size: clamp(12px, 0.8vw, 14px); color: rgba(232,228,219,0.35);
  letter-spacing: 0.03em; line-height: 1.4;
}
.photo-guide-tip-icon { font-size: 14px; flex-shrink: 0; opacity: 0.6; }

/* ---- status inline dots (scoped override) ---- */
.status-inline-dot {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 400;
  letter-spacing: 0.03em;
  color: rgba(232,228,219,0.45);
  font-family: system-ui, "Noto Sans SC", sans-serif;
  white-space: nowrap;
}
.status-inline-dot::before {
  content: "";
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
  transition: background 0.3s ease, box-shadow 0.3s ease;
}
.status-inline-dot--ready::before { background: #5ec9a4; box-shadow: 0 0 5px rgba(94,201,164,0.35); }
.status-inline-dot--loading::before { background: #e8a840; box-shadow: 0 0 5px rgba(232,168,64,0.35); animation: dot-pulse 1.6s ease-in-out infinite; }
.status-inline-dot--live::before { background: #d9a441; box-shadow: 0 0 5px rgba(217,164,65,0.35); }
.right-card-head-status {
  display: inline-flex; align-items: center; gap: 10px;
  flex-shrink: 0;
}
.answer-feedback { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 8px; color: rgba(232,228,219,.62); font-size: 11px; }
.answer-feedback button { border: 1px solid rgba(232,228,219,.2); border-radius: 999px; background: rgba(255,255,255,.04); color: rgba(255,250,242,.82); padding: 4px 10px; font-size: 11px; cursor: pointer; font-family: inherit; }
.answer-feedback button:hover, .answer-feedback button.active { border-color: rgba(94,201,164,.75); background: rgba(94,201,164,.14); color: #b8f1dd; }
.answer-feedback button:disabled { cursor: wait; opacity: .55; }
.feedback-reasons { display: flex; flex-basis: 100%; flex-wrap: wrap; align-items: center; gap: 6px; padding-top: 2px; }
.feedback-reasons button { border-color: rgba(248,113,113,.25); }
.feedback-reasons button:hover, .feedback-reasons button.active { border-color: rgba(248,113,113,.6); background: rgba(248,113,113,.12); color: #ffb4a8; }
.feedback-error { flex-basis: 100%; color: #ffb4a8; }
@keyframes dot-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* ---- responsive ---- */
@media (max-width: 720px) {
  .tourist-page { overflow: hidden; padding: 0; }
  .tourist-stage { display: flex; flex-direction: column; padding: 0; margin-top: 40px; gap: 0; flex: 1; min-height: 0; padding-bottom: 48px; }
  .side-card { display: none; }
  .right-card { display: none; }
  .chat-center { flex: 1; padding: 0; min-height: 0; }
  .avatar-stage { width: min(52vh, 78vw); height: 100%; min-height: 0; flex: 1; }
  .avatar-stage :deep(.three-wrapper),
  .avatar-stage :deep(.avatar-display) { transform: translateY(10%); }
  .avatar-stage::after { height: 80px; }
  .input-row { position: absolute; bottom: 56px; left: 0; right: 0; transform: none; width: auto; gap: 6px; padding: 0 10px; margin: 0; }
  .input-field { height: 48px; font-size: 16px; padding: 0 14px; }
  .input-field::placeholder { font-size: 14px; }
  .back-btn { top: 6px; left: 6px; padding: 5px 12px; font-size: 14px; }
  .top-right { top: 6px; right: 6px; }
  .top-brand { font-size: 15px; }
  .top-caption { flex-wrap: wrap; gap: 4px; }
  .caption-kicker { font-size: 15px; }
  .caption-weather { font-size: 10px; padding: 3px 8px; }
  .crowd-indicator { font-size: 10px; padding: 3px 8px; }
  .service-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
  .explore-card { padding: 10px 6px; }
  .explore-card-icon { width: 40px; height: 40px; font-size: 22px; }
  .explore-card-title { font-size: 16px; }
  .explore-card-desc { font-size: 12px; }
  .voice-btn { padding: 0 10px; height: 44px; font-size: 14px; }
  .image-btn { padding: 0 10px; height: 44px; font-size: 13px; }
}

@media (prefers-reduced-motion: reduce) {
  .side-card.speaking { animation: none; }
  .status-inline-dot--loading::before { animation: none; }
}
</style>
