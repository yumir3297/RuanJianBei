<template>
  <section class="tourist-page" :class="{ 'has-scenic-background': hasScenicBackground }" :style="touristPageStyle">
    <div class="scenic-bg" aria-hidden="true"><div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div></div>
    <header class="guide-header">
      <RouterLink class="guide-brand" to="/tourist" :aria-label="`${touristSettings.brand_name}首页`"><GuideIcon name="landmark" /><strong>{{ touristSettings.brand_name }}</strong></RouterLink>
      <div class="header-actions">
        <span v-if="weatherCaption" class="header-weather" :title="weatherColorLabel || undefined"><i class="weather-color-dot" :style="{ background: scenicColor.hex }" aria-hidden="true"></i>{{ weatherCaption }}<template v-if="weatherColorLabel">&nbsp;·&nbsp;{{ weatherColorLabel }}</template></span>
        <details class="service-menu"><summary><GuideIcon name="headphones" /><span>景区服务</span></summary><div class="service-popover"><button v-for="service in touristSettings.hotlines.filter(item => item.enabled)" :key="service.id" type="button" :disabled="inputBusy" @click="handleHotline(service.id); $event.currentTarget.closest('details').open = false"><strong>{{ service.label }}</strong><small>{{ service.number }}</small></button><p v-if="!touristSettings.hotlines.some(item => item.enabled)">暂无已配置的服务电话，请咨询景区工作人员。</p></div></details>
        <RouterLink class="admin-entry" to="/admin/dashboard">运营管理</RouterLink>
      </div>
    </header>
    <main class="guide-layout" :class="{ 'tool-open': activeTool, 'route-tool-open': activeTool === 'route', 'map-open': activeTool === 'map', 'text-open': textExpanded }">
      <aside class="feature-rail" aria-label="导览功能">
        <div class="rail-heading"><h2>导览</h2><p>选择内容，听导游讲解</p></div>
        <nav class="tool-dock" aria-label="导览工具"><button v-for="tool in tools" :id="'tool-trigger-' + tool.id" :key="tool.id" type="button" :class="{ active: activeTool === tool.id }" :aria-expanded="activeTool === tool.id" aria-controls="guide-tools" @click="setTool(tool.id)"><GuideIcon :name="tool.icon" /><span>{{ tool.title }}</span><GuideIcon name="chevron" class="dock-chevron" /></button></nav>
      <dialog ref="toolDialogRef" id="guide-tools" class="tool-sheet" aria-labelledby="tool-title" @cancel.prevent="closeTool" @click="handleDialogBackdrop($event, closeTool)">
        <header class="tool-sheet-header"><h3 ref="toolHeadingRef" id="tool-title" tabindex="-1"><GuideIcon :name="selectedTool?.icon" />{{ selectedTool?.title }}</h3><button type="button" class="icon-button" aria-label="收起导览工具" @click="closeTool"><GuideIcon name="close" /></button></header>
        <div class="tool-sheet-body"><KeepAlive><component :is="selectedTool.component" v-if="selectedTool" :key="activeTool" :busy="inputBusy" v-bind="activeTool === 'route' ? { weather } : activeTool === 'map' ? { weather, scenicColor, colorLabel: weatherColorLabel, speechRate } : {}" @ask="handleToolQuestion" /></KeepAlive></div>
      </dialog>
        <div v-if="!activeTool" class="rail-discovery"><h3>常用提问</h3><button v-for="question in touristSettings.quick_questions.slice(0, 3)" :key="question" type="button" :disabled="inputBusy" @click="handleQuickQuestion(question)">{{ question }}<GuideIcon name="chevron" /></button></div>
      </aside>
      <section class="guide-scene" aria-label="数字人导游">
        <div class="scene-heading"><h1>{{ avatarDisplayName }}</h1><span>{{ touristSettings.guide_subtitle }}</span></div>
        <div class="avatar-stage">
          <ThreeAvatar v-if="!avatarError" :preset="avatarConfig.modelKey" :emotion="avatar.currentEmotion.value" :is-speaking="digitalHumanSpeaking" :speech-progress="speechProgress" :speech-elapsed-ms="speechElapsedMs" :speech-duration-ms="speechDurationMs" :speech-sync-active="digitalHumanSpeechSync" :viseme-timeline="visemeTimeline" :avatar-state="digitalHumanAvatarState" :action="avatar.currentAction.value" :action-key="avatar.actionKey.value" @loaded="handleAvatarLoaded" @error="handleAvatarLoadError" />
          <AvatarDisplay v-else :state="digitalHumanAvatarState" :emotion="avatar.currentEmotion.value" />
          <div v-if="activeSubtitle" class="avatar-subtitle" aria-hidden="true">
            <span v-for="(word, index) in activeSubtitle.words" :key="`${word.begin_time}-${index}`" class="subtitle-word" :class="{ spoken: activeSubtitle.activeIndex >= 0 && index < activeSubtitle.activeIndex, active: index === activeSubtitle.activeIndex }">{{ word.text }}</span>
          </div>
        </div>
        <div class="guide-presence" role="status"><span class="presence-dot" :class="{ ready: avatarReady }"></span><span>{{ avatarError ? '形象暂不可用，仍可继续提问' : avatarReady ? '形象已就绪' : '形象加载中…' }}</span></div>
        <div class="composer">
    <!-- 语音状态条 -->
    <div v-if="transcribing" class="speech-bar" aria-live="polite">
      <span class="speech-pulse" aria-hidden="true"></span>
      <strong>正在识别</strong>
      <span>首次加载语音模型可能需要更长时间…</span>
      <button type="button" class="confirm-btn confirm-btn--dismiss" @click="cancelTranscription">取消识别</button>
    </div>
    <div v-if="speechListening || isRecording" class="speech-bar" aria-live="polite">
      <span class="speech-pulse" aria-hidden="true"></span>
      <strong>正在聆听</strong>
      <span>{{ isRecording ? '点击结束语音，我会帮你转成文字。' : speechPreviewText || '请开始说话…' }}</span>
      <span v-if="transcriptionConfidence >= 0" class="confidence-dot" :class="confidenceLevelClass" :title="`置信度 ${Math.round(transcriptionConfidence * 100)}%`"></span>
    </div>

    <!-- 录音转写确认条 -->
    <div v-if="showConfirmBar" class="confirm-bar">
      <span class="confirm-text">你刚说的是 "<strong>{{ confirmedTranscript }}</strong>" 吗？</span>
      <button class="confirm-btn confirm-btn--yes" @click="confirmAndSubmit">确认</button>
      <button class="confirm-btn confirm-btn--retry" @click="retryRecording">重新说</button>
      <button class="confirm-btn confirm-btn--dismiss" @click="dismissConfirmBar">手动输入</button>
      <div v-if="transcriptionCandidates.length > 1" class="confirm-candidates">
        <span class="confirm-candidates-label">也可能是：</span>
        <button v-for="c in transcriptionCandidates" :key="c.text" class="confirm-candidate-chip" @click="selectCandidate(c.text)">{{ c.text }}</button>
      </div>
    </div>

    <!-- 语音错误提示 -->
    <div v-if="voiceErrorMessage" class="voice-error-bar">
      <span>{{ voiceErrorMessage }}</span>
    </div>

    <!-- 浏览器兼容提示 -->
    <div v-if="showBrowserHint && voiceSupported" class="browser-hint-bar">
      <span>推荐使用 Chrome 浏览器以获得最佳语音识别体验</span>
      <button class="browser-hint-close" @click="dismissBrowserHint">知道了</button>
    </div>


          <form v-show="textInputExpanded" class="query-form" @submit.prevent="handleSubmit">
            <label for="tourist-query" class="sr-only">向数字人导游提问</label>
            <textarea ref="queryInputRef" id="tourist-query" v-model="query" class="input-field" rows="2" :placeholder="voiceMode ? '正在录音，点击下方结束语音…' : '输入问题或游览计划…'" :disabled="chatStore.streaming || voiceMode || transcribing" @keydown.enter.exact.prevent="handleSubmit" autocomplete="off" name="tourist-query"></textarea>
            <button v-if="chatStore.streaming" type="button" class="send-btn stop-btn" aria-label="停止回答" @click="chatStore.stopOutput()"><span class="stop-square"></span></button>
            <button v-else type="submit" class="send-btn" :disabled="!query.trim() || voiceMode || transcribing || speechListening || isRecording" aria-label="发送问题"><GuideIcon name="send" /></button>
          </form>
          <div class="composer-actions">
            <button type="button" class="image-btn" :disabled="inputBusy" @click="toggleVisionPanel"><GuideIcon name="camera" /><span>拍照识景</span></button>
            <button v-if="chatStore.streaming || audioPlayer.isPlaying.value" type="button" class="voice-primary stop-primary" @click="stopAudioOutput"><span class="stop-square"></span><span>停止讲解</span></button>
            <button v-else type="button" class="voice-primary" :class="{ recording: speechListening || isRecording }" :disabled="transcribing || !voiceSupported" @click="toggleRecording"><GuideIcon name="mic" /><span>{{ transcribing ? '正在识别…' : voiceMode || speechListening || isRecording ? '结束语音' : '语音提问' }}</span></button>
            <button type="button" class="keyboard-btn" :aria-expanded="textInputExpanded" aria-controls="tourist-query" @click="toggleTextInput"><GuideIcon name="keyboard" /><span>{{ textInputExpanded ? '收起输入' : '键盘输入' }}</span></button>
          </div>
          <p v-if="voiceStageStatus" class="voice-caption" aria-live="polite">{{ voiceStageStatus }}</p>
        </div>
      </section>
      <aside class="narration-rail" aria-label="讲解辅助">
        <div class="rail-heading"><h2>讲解</h2><p>按你的需要调整讲解方式</p></div>
        <label class="explanation-select"><GuideIcon name="settings" /><span>讲解方式</span><select v-model="explanationLevel" aria-label="讲解方式"><option v-for="style in styleOptions" :key="style.key" :value="style.key">{{ style.label }}讲解</option></select></label>
        <label class="explanation-select speech-rate-select"><GuideIcon name="settings" /><span>语速</span><select v-model.number="speechRate" aria-label="语音讲解语速"><option v-for="rate in speechRateOptions" :key="rate" :value="rate">{{ rate.toFixed(1) }}×</option></select></label>
        <div class="narration-note"><h3>当前讲解</h3><p v-if="narrationSummary">{{ narrationSummary }}</p><p v-else class="narration-empty">提问后，讲解摘要会显示在这里。</p><small v-if="narrationSummary">完整内容可在文字记录中查看</small></div>
        <p v-if="chatStore.errorMessage" class="rail-error" role="alert">{{ chatStore.errorMessage }} <button v-if="chatStore.retryAvailable" type="button" class="retry-btn" @click="retryLastAnswer">重新尝试</button></p>
        <button id="text-panel-trigger" type="button" class="text-panel-trigger" :aria-expanded="textExpanded" @click="toggleTextPanel"><GuideIcon name="book" />文字记录与资料<span>{{ chatStore.messages.length > 1 ? chatStore.messages.length - 1 : '' }}</span><GuideIcon name="chevron" /></button>
      <dialog ref="textDialogRef" class="conversation-panel" aria-label="文字记录与参考资料" @cancel.prevent="closeTextPanel" @click="handleDialogBackdrop($event, closeTextPanel)">
        <header class="conversation-header"><div><h2>文字记录</h2><p>需要时，回看讲解和参考资料。</p></div><button type="button" class="icon-button" aria-label="收起文字记录" @click="closeTextPanel"><GuideIcon name="close" /></button></header>
        <label class="compact-explanation-select"><GuideIcon name="settings" /><span>讲解方式</span><select v-model="explanationLevel" aria-label="讲解方式"><option v-for="style in styleOptions" :key="style.key" :value="style.key">{{ style.label }}讲解</option></select></label>
        <label class="compact-explanation-select compact-speech-rate-select"><GuideIcon name="settings" /><span>语速</span><select v-model.number="speechRate" aria-label="语音讲解语速"><option v-for="rate in speechRateOptions" :key="rate" :value="rate">{{ rate.toFixed(1) }}×</option></select></label>
      <section class="side-card" aria-label="导游对话" :class="{ speaking: chatStore.streaming }">
        <div class="side-card-head">
          <div class="side-card-tabs" role="tablist" aria-label="对话与资料">
            <button id="chat-tab" :class="['side-card-tab', { active: activeTab === 'chat' }]" role="tab" :aria-selected="activeTab === 'chat'" :tabindex="activeTab === 'chat' ? 0 : -1" aria-controls="chat-log" @click="activeTab = 'chat'" @keydown="handleTabKey">对话</button>
            <button id="source-tab" :class="['side-card-tab', { active: activeTab === 'source' }]" role="tab" :aria-selected="activeTab === 'source'" :tabindex="activeTab === 'source' ? 0 : -1" aria-controls="source-log" @click="activeTab = 'source'" @keydown="handleTabKey">参考资料</button>
          </div>
          <span class="conversation-status" role="status">{{ replyStatusText }}</span>
        </div>
        <div :class="['side-card-body', { hidden: activeTab !== 'chat' }]" ref="messageListRef" id="chat-log" role="tabpanel" aria-label="对话记录">
          <div v-if="chatStore.messages.length <= 1" class="conversation-welcome"><h3>还没有讲解记录</h3><p>可以语音提问，也可以选择下面的问题。</p></div>
          <article v-for="(message, index) in chatStore.messages" v-show="!message.isWelcome || chatStore.messages.length > 1" :key="`${message.role}-${index}`" :class="['msg-item', message.role, { latest: index === chatStore.messages.length - 1 }]">
            <div v-if="message.role === 'assistant'" class="msg-bubble" v-html="renderAnswer(message, index === chatStore.messages.length - 1)" @click="handleCitationClick($event, message)"></div>
            <div v-else class="msg-bubble">{{ message.content }}</div>
            <p v-if="message.warning" class="error-notice" role="status">{{ message.warning }}</p>
            <button v-if="message.sources?.length" type="button" @click="showMessageSources(message)">查看本条参考资料（{{ message.sources.length }}）</button>
            <div v-if="message.role === 'assistant' && !message.isWelcome && message.chatLogId && message.completion === 'complete' && !chatStore.streaming" class="answer-replay">
              <button type="button" :disabled="message.replayLoading" :aria-busy="message.replayLoading" @click="replayAnswer(message)">{{ message.replayLoading ? '正在准备语音…' : message.replayPlaying ? '正在重播' : '重播讲解' }}</button>
              <span v-if="message.replayError" class="feedback-error" role="alert">{{ message.replayError }}</span>
            </div>
            <p v-if="message.completion === 'incomplete'" class="error-notice">回答未完成，已保留现有内容。</p>
            <p v-else-if="message.completion === 'stopped'" class="error-notice">已停止生成。</p>
            <div v-if="message.role === 'assistant' && !message.isWelcome && message.content && message.completion !== 'incomplete' && message.completion !== 'stopped' && !chatStore.streaming" class="answer-feedback" aria-label="回答评价">
              <span>这条讲解有帮助吗？</span>
              <button type="button" :class="{ active: message.feedbackRating === 'positive' }" :disabled="message.feedbackSubmitting" @click="chatStore.submitFeedback(message, 'positive')">有帮助</button>
              <button type="button" :class="{ active: message.feedbackPendingRating === 'negative' || message.feedbackRating === 'negative' }" :disabled="message.feedbackSubmitting" @click="message.feedbackPendingRating = message.feedbackPendingRating === 'negative' ? null : 'negative'">需改进</button>
              <div v-if="message.feedbackPendingRating === 'negative'" class="feedback-reasons">
                <span>请选择原因：</span>
                <button v-for="reason in feedbackReasons" :key="reason.value" type="button" :disabled="message.feedbackSubmitting" @click="chatStore.submitFeedback(message, 'negative', reason.value)">{{ reason.label }}</button>
              </div>
              <span v-if="message.feedbackError" class="feedback-error">{{ message.feedbackError }}</span>
            </div>
            <span v-if="message.role === 'assistant' && chatStore.streaming && index === chatStore.messages.length - 1 && message.content.length > 0" class="typing-cursor">|</span>
          </article>
          <div v-if="chatStore.streaming && !chatStore.messages.at(-1)?.content" class="thinking-notice" role="status"><span class="thinking-dots">···</span> 导游正在查阅资料</div>
          <div v-if="tourStore.proposalLoading" class="itinerary-proposal" role="status"><span>正在生成可验证的改线方案；停止等待不会取消后台任务。</span><button type="button" @click="tourStore.cancelProposal()">停止等待</button></div>
          <section v-if="pendingIntentQuery" class="itinerary-proposal" aria-label="确认需求类型">
            <p>“{{ pendingIntentQuery }}”可能是在询问，也可能是想调整当前行程。你希望怎么处理？</p>
            <button type="button" @click="continuePendingIntentAsQuestion">普通问答</button>
            <button type="button" @click="continuePendingIntentAsEdit">生成行程提案</button>
            <button type="button" @click="pendingIntentQuery = ''">暂不处理</button>
          </section>
          <section v-if="tourStore.proposalChoices.length" class="itinerary-proposal" aria-label="选择需要查看的提案">
            <p>最近十条中的提案时间相同，请按原始需求选择查看；查看不会重新调用 AI。</p>
            <button v-for="item in tourStore.proposalChoices" :key="item.id" type="button" :disabled="tourStore.proposalLoading" @click="tourStore.selectProposalChoice(item.id)">{{ item.request_text || '未提供需求文本' }} · {{ ({ ready: '待确认', executing: '生成中', waiting_user: '需确认重试', needs_clarification: '需要补充', failed: '未完成', applied: '已应用' })[item.status] || '状态待确认' }} · {{ item.id.slice(-6) }}</button>
          </section>
          <section v-if="tourStore.proposal" class="itinerary-proposal" aria-label="行程修改提案">
            <header><strong>行程修改提案</strong><button type="button" @click="tourStore.cancelProposal()">关闭</button></header>
            <p>“{{ tourStore.proposal.request_text }}”</p>
            <p v-if="tourStore.proposal.status === 'applied'">这份提案已应用，不会重复保存。</p>
            <p v-if="tourStore.proposalIsStale" class="itinerary-proposal-error" role="status">当前草稿已修改；这份提案仍基于修改前的行程，不能直接应用。请基于当前草稿重新生成。</p>
            <p v-if="tourStore.proposal.status === 'waiting_user'" role="status">AI 服务可能已收到上次请求，但结果未能保存。再次尝试可能重复产生调用费用；行程本身仍未改变。</p>
            <button v-if="tourStore.proposal.status === 'waiting_user'" type="button" :disabled="tourStore.proposalLoading" @click="tourStore.retryProposal(true)">确认可能重复产生调用费用并重试</button>
            <p v-if="tourStore.proposal.status === 'executing'" role="status">提案正在后台生成；关闭页面或停止等待后，任务仍会继续。</p>
            <button v-if="!tourStore.proposalLoading && tourStore.proposal.status === 'executing'" type="button" @click="tourStore.resumeProposal(tourStore.proposal)">重新检查状态</button>
            <p v-if="tourStore.proposal.status === 'failed'" role="status">{{ tourStore.proposal.validation?.message || '提案未能完成，当前行程未改变。' }}</p>
            <p v-if="tourStore.proposal.status === 'needs_clarification'">{{ tourStore.proposal.clarification }} 请补充后重新提交。</p>
            <template v-else-if="tourStore.proposal.status === 'ready'">
              <ul v-if="tourStore.proposal.diff_verifiable !== false"><li v-for="(change, index) in tourStore.proposal.diff" :key="`${change.kind}-${index}`">{{ itineraryProposalDiffText(change, { beforeSnapshot: tourStore.proposalBaseSnapshot, candidateSnapshot: tourStore.proposal.candidate }) }}</li></ul>
              <p>AI 建议的停留时长仅供参考，请结合实际情况确认。</p>
              <p v-if="tourStore.proposal.diff_verifiable === false" role="alert">这份旧提案缺少可核对的原始行程，请重新生成。</p>
              <p>{{ tourStore.proposal.validation.status === 'unverified' ? '游览预算、停留或路段时长、景点约束或休息间隔可能尚未核实。' : '已识别的硬约束已通过检查。' }}请对照上方原始需求和修改内容，确认没有遗漏或误改。</p>
              <button type="button" :disabled="tourStore.proposalIsStale || tourStore.proposalLoading || tourStore.proposalApplying || tourStore.proposal.diff_verifiable === false" @click="tourStore.confirmProposal()">{{ tourStore.proposalApplying ? '正在保存…' : '确认并保存新版本' }}</button>
              <button v-if="tourStore.proposalIsStale || tourStore.proposal.diff_verifiable === false" type="button" :disabled="tourStore.proposalLoading" @click="tourStore.requestProposal(tourStore.proposal.request_text)">按当前草稿重新生成</button>
              <button type="button" @click="tourStore.cancelProposal()">放弃</button>
            </template>
          </section>
          <p v-if="tourStore.error" class="itinerary-proposal-error" role="alert">{{ tourStore.error }}</p>
          <div v-if="chatStore.messages.length <= 1" class="starter-questions"><button v-for="question in touristSettings.quick_questions.slice(0, 3)" :key="question" type="button" :disabled="inputBusy" @click="handleQuickQuestion(question)">{{ question }} <span aria-hidden="true">↗</span></button></div>
          <div v-if="chatStore.followups.length" class="followup-panel">
            <button v-for="item in chatStore.followups" :key="item.query" type="button" :disabled="chatStore.streaming" @click="handleFollowup(item.query)">{{ item.label }}</button>
          </div>
          <div v-if="chatStore.userStopped && !chatStore.streaming" class="stop-notice" role="status">已停止输出</div>
          <div v-if="chatStore.errorMessage && !chatStore.streaming" class="error-notice" role="alert"><span>{{ chatStore.errorMessage }}</span><button v-if="chatStore.retryAvailable" type="button" class="retry-btn" @click="retryLastAnswer">重新尝试</button></div>
        </div>
        <div id="source-log" role="tabpanel" aria-label="参考资料" :class="['side-card-body', { hidden: activeTab !== 'source' }]">
          <ul class="source-list" v-if="displayedSources.length">
            <li v-for="(item, index) in displayedSources" :key="`${item.title}-${index}`" :class="['source-item', { highlight: sourceHighlightIndex === index }]" :data-source-index="index">
              <h4><span class="source-num">{{ index + 1 }}</span>{{ item.title }}</h4>
              <p>{{ item.snippet }}</p>
              <span class="source-meta">{{ item.source }}</span>
            </li>
          </ul>
          <p v-else class="source-empty">提问后这里会显示参考资料</p>
        </div>
        <section v-if="emotionAnalysis" class="emotion-analysis" :class="{ expanded: emotionPanelExpanded }">
          <button
            type="button"
            class="emotion-analysis-toggle"
            :aria-expanded="emotionPanelExpanded"
            @click="emotionPanelExpanded = !emotionPanelExpanded"
          >
            <span class="emotion-analysis-dot" :data-emotion="emotionAnalysis.label"></span>
            <span class="emotion-analysis-title">{{ emotionPanelTitle }}</span>
            <strong>{{ emotionLabel(emotionAnalysis.label) }}</strong>
            <span class="emotion-analysis-confidence">{{ formatEmotionPercent(emotionAnalysis.confidence) }}</span>
            <span class="emotion-analysis-chevron" aria-hidden="true">⌄</span>
          </button>
          <div v-show="emotionPanelExpanded" class="emotion-analysis-detail">
            <div class="emotion-metric-grid">
              <div class="emotion-metric">
                <span>文本判断</span>
                <b>{{ textEmotionSignal ? emotionLabel(textEmotionSignal.label) : '未参与' }}</b>
                <small>{{ textEmotionSignal ? formatEmotionPercent(textEmotionSignal.confidence) : '--' }}</small>
              </div>
              <div class="emotion-metric">
                <span>声音判断</span>
                <b>{{ audioEmotionSignal ? emotionLabel(audioEmotionSignal.label) : '未参与' }}</b>
                <small>{{ audioEmotionSignal ? formatEmotionPercent(audioEmotionSignal.confidence) : '--' }}</small>
              </div>
              <div class="emotion-metric emotion-metric--fused">
                <span>融合结果</span>
                <b>{{ emotionLabel(emotionAnalysis.label) }}</b>
                <small>{{ formatEmotionPercent(emotionAnalysis.confidence) }}</small>
              </div>
            </div>
            <div class="emotion-analysis-meta">
              <span>响应策略：{{ responseStrategyLabel }}</span>
              <span>分析模态：{{ emotionModalitiesText }}</span>
              <span v-if="emotionAnalysis.conflict" class="emotion-conflict">文本与声音存在差异，已按置信度融合</span>
            </div>
          </div>
        </section>
      </section>


      </dialog>
      </aside>
    </main>
    <!-- Vision panel (hidden file input) -->
    <input ref="visionFileInputRef" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="handleVisionFileChange" />

    <!-- Vision result modal -->
    <dialog ref="visionDialogRef" class="vision-modal" aria-labelledby="vision-title" @cancel.prevent="closeVisionPanel" @click="handleDialogBackdrop($event, closeVisionPanel)">
      <div class="vision-modal-content">
        <button type="button" aria-label="关闭拍照识景" class="modal-close" @click="closeVisionPanel">✕</button>
        <h3 id="vision-title">拍照识景</h3><p class="vision-intro">上传照片或打开摄像头，认一认眼前的风景。</p>
        <div class="vision-source-actions">
          <button :disabled="visionAnalyzing || chatStore.streaming" @click="openVisionFilePicker">选择图片</button>
          <button
            v-if="cameraSupported"
            :disabled="visionAnalyzing || chatStore.streaming || cameraStarting"
            @click="toggleCamera"
          >{{ cameraActive ? '关闭摄像头' : '打开摄像头' }}</button>
        </div>

        <div v-if="cameraActive" class="vision-camera" style="display:flex;flex-direction:column;gap:0.5rem;align-items:center;">
          <video
            :ref="bindVideo"
            playsinline
            muted
            autoplay
            style="width:100%;max-width:320px;border-radius:10px;background:#000;"
          ></video>
          <button :disabled="visionAnalyzing || chatStore.streaming" @click="captureFromCamera">拍照</button>
        </div>
        <div v-if="cameraError" class="vision-error">{{ cameraError }}</div>

        <button :disabled="visionAnalyzing || !visionFile || chatStore.streaming" @click="handleAnalyzeImage">
          {{ visionAnalyzing ? '识别中…' : '识别图片' }}
        </button>
        <button v-if="visionFile || visionResult" :disabled="visionAnalyzing" @click="clearVisionPanel">清除</button>
        <div v-if="visionFile">
          <img v-if="visionPreviewUrl" :src="visionPreviewUrl" style="max-width:200px" />
          <strong>{{ visionFile.name }}</strong>
        </div>
        <div v-if="visionError" class="vision-error">{{ visionError }}</div>
        <div v-if="visionResult" class="vision-result">
          <p class="vision-summary">{{ visionResult.scene_summary || '暂未识别出明确场景。' }}</p>
          <div v-if="visionResult.candidate_attractions?.length">
            <span class="vision-label">可能是</span>
            <span v-for="item in visionResult.candidate_attractions" :key="item" class="vision-tag">{{ item }}</span>
          </div>
          <div v-if="visionResult.visual_tags?.length">
            <span class="vision-label">画面特征</span>
            <span v-for="item in visionResult.visual_tags" :key="item" class="vision-tag">{{ item }}</span>
          </div>
          <div class="vision-meta">模型识别把握（未经校准）：{{ formatConfidence(visionResult.confidence) }}</div>
          <label for="vision-published-spot">自行确认已发布景点（可选）</label>
          <select id="vision-published-spot" v-model="visionSelectedSpot" :disabled="visionCatalogLoading">
            <option value="">不确认，继续开放检索</option>
            <option v-for="spot in visionCatalog.items" :key="spot.spot_code" :value="spot.spot_code">{{ spot.title }}{{ spot.source_label ? `（${spot.source_label}）` : '' }}</option>
          </select>
          <p v-if="visionCatalogError" class="vision-error">已发布景点目录暂不可用，可不确认直接提问。</p>
          <p v-else-if="!visionCatalogLoading && !visionCatalog.items.length">目录没有可选景点，可不确认直接提问。</p>
          <p>识别候选仅供参考，请自行选择；所选景点并不证明照片内容。</p>
          <button :disabled="chatStore.streaming || !visionResult.retrieval_query" @click="askFromImage">请导游讲讲这里</button>
        </div>
      </div>
    </dialog>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import ThreeAvatar from "../../components/ThreeAvatar.vue";
import AvatarDisplay from "../../components/AvatarDisplay.vue";
import GuideIcon from "../../components/GuideIcon.vue";
import ExploreView from "./ExploreView.vue";
import MapView from "./MapView.vue";
import RouteView from "./RouteView.vue";
import QuizView from "./QuizView.vue";
import "../../assets/guide-tools.css";
import { analyzeImage, getVisionErrorMessage } from "../../api/vision";
import { fetchItineraryCatalog } from "../../api/itinerary.js";
import { visionConfirmation, createVisionAsyncGuard, buildVisionChatRequest } from "../../utils/visionConfirmation.js";
import { displayableASRConfidence } from "../../utils/asrConfidence.js";
import { createLatestRequest } from "../../utils/latestRequest";
import { createIdempotencyKey } from "../../utils/idempotencyKey";
import { getTranscriptionErrorMessage, transcribeAudio } from "../../api/voice";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { renderMarkdown } from "../../composables/useMarkdown";
import { useRecorder } from "../../composables/useRecorder";
import { useCamera } from "../../composables/useCamera";
import { useSpeechRecognition } from "../../composables/useSpeechRecognition";
import { useScenicBackground } from "../../composables/useScenicBackground";
import { fetchAvatarConfig } from "../../api/admin";
import { fetchWelcomeAudio, replayChatAnswer } from "../../api/chat";
import { normalizeAvatarPresetFromModelPath, DEFAULT_AVATAR_PRESET } from "../../utils/avatarConfig";
import { GUIDE_PERSONA, useAvatar } from "../../composables/useAvatar";
import { useWeather } from "../../composables/useWeather";
import { isItineraryEditIntent } from "../../utils/itineraryIntent.js";
import { resolvePublishedAttraction } from "../../utils/toolAttraction.js";
import { itineraryProposalDiffText } from "../../utils/itineraryProposalDiff.js";
import { useTourSessionsStore } from "../../stores/tourSessions";
import { getSessionId, useChatStore } from "../../stores/chat";
import { useInteractionStore } from "../../stores/interaction";
import { readSpeechRate, SPEECH_RATE_OPTIONS, writeSpeechRate } from "../../utils/speechRatePreference";
import { createChatReplayController } from "../../utils/chatReplay";

const router = useRouter();
const route = useRoute();
const feedbackReasons = [
  { value: "accuracy", label: "内容不准确" },
  { value: "detail", label: "信息不够" },
  { value: "recommendation", label: "建议不合适" },
  { value: "latency", label: "响应太慢" },
  { value: "other", label: "其他" },
];
const chatStore = useChatStore();
const interactionStore = useInteractionStore();
const tourStore = useTourSessionsStore();
const speechRate = ref(readSpeechRate());
const speechRateOptions = SPEECH_RATE_OPTIONS;
watch(speechRate, (rate) => writeSpeechRate(rate));
const { scenicBgUrl, hasScenicBackground, welcomeText, touristSettings } = useScenicBackground();
function rgbaHex(hex, alpha) {
  const value = /^#([\da-f]{6})$/i.exec(hex || "")?.[1] || "18352b";
  const rgb = [0, 2, 4].map((offset) => Number.parseInt(value.slice(offset, offset + 2), 16));
  return `rgba(${rgb.join(",")},${Math.max(0, Math.min(1, alpha))})`;
}
const touristPageStyle = computed(() => {
  const settings = touristSettings.value;
  const width = settings.edge_fade_width || 36;
  const fontFamily = settings.font_style === "system"
    ? '"PingFang SC", "Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans SC", system-ui, sans-serif'
    : '"Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif';
  return {
    "--guide-green": settings.primary_color,
    "--guide-font-family": fontFamily,
    "--guide-display-font": fontFamily,
    "--scenic-tint-color": settings.background_tint,
    "--scenic-edge-strong": rgbaHex(settings.background_tint, settings.background_tint_opacity),
    "--scenic-edge-medium": rgbaHex(settings.background_tint, settings.background_tint_opacity * 0.68),
    "--scenic-edge-soft": rgbaHex(settings.background_tint, settings.background_tint_opacity * 0.3),
    "--scenic-fade-1": `${Math.round(width * 0.2)}%`,
    "--scenic-fade-2": `${Math.round(width * 0.48)}%`,
    "--scenic-fade-3": `${Math.round(width * 0.78)}%`,
    "--scenic-fade-width": `${width}%`,
    "--scenic-edge-blur": `${settings.edge_blur}px`,
  };
});
const {
  isRecording,
  isSupported: recorderSupported,
  durationSeconds,
  start: startRecording,
  stop: stopRecording,
} = useRecorder();
const {
  isListening: speechListening,
  interimText: speechInterimText,
  finalText: speechFinalText,
  isSupported: speechSupported,
  error: speechError,
  showBrowserHint,
  start: startSpeechRecognition,
  stop: stopSpeechRecognition,
  abort: abortSpeechRecognition,
  dismissHint: dismissBrowserHint,
} = useSpeechRecognition();
const avatar = useAvatar();
const { weather, scenicColor, displayText: weatherCaption, colorLabel: weatherColorLabel, startPolling: startWeather, stopPolling: stopWeather } = useWeather();
const audioPlayer = useAudioPlayer();
const chatReplay = createChatReplayController({
  requestReplay: replayChatAnswer,
  audioPlayer,
  getSessionId,
  getVoice: () => avatarConfig.value.voiceType,
  getRate: () => speechRate.value,
  onMode: (_message, mode) => {
    if (mode !== "silent") {
      activeAudioSegments.value += 1;
      avatar.setState("speaking");
    }
  },
  onProgress: (_message, progress, elapsedMs, durationMs, timeline) => {
    speechProgress.value = progress;
    speechElapsedMs.value = elapsedMs;
    speechDurationMs.value = durationMs;
    if (timeline) visemeTimeline.value = timeline;
  },
  onEnded: () => {
    activeAudioSegments.value = Math.max(activeAudioSegments.value - 1, 0);
    if (activeAudioSegments.value === 0) {
      avatar.setState("idle");
      speechProgress.value = 0;
      speechElapsedMs.value = 0;
      speechDurationMs.value = 0;
      visemeTimeline.value = null;
      chatStore.clearSubtitleWords();
    }
  },
});
const avatarState = avatar.currentState;
const mapNarrationActive = computed(() => audioPlayer.activePlayback.value?.owner === "map-narration");
const digitalHumanSpeaking = computed(() => mapNarrationActive.value || avatarState.value === "speaking" || avatarState.value === "happy");
const digitalHumanSpeechSync = computed(() => mapNarrationActive.value || activeAudioSegments.value > 0);
const digitalHumanAvatarState = computed(() => mapNarrationActive.value ? "speaking" : avatarState.value);
const avatarError = ref(false);
const avatarLoaded = ref(false);

const GUIDE_STYLE_STORAGE_KEY = "a5-pending-guide-style-v1";
const avatarConfig = ref({ modelKey: DEFAULT_AVATAR_PRESET, voiceType: "gentle-female" });

const AVATAR_MODEL_MAP = {
  monk: { name: "宁灵", subtitle: "宁灵 · 国风文化导游" },
  hanfu: { name: "清岚", subtitle: "清岚 · 文化叙事导游" },
  modern: { name: "景行", subtitle: "景行 · 智能导览导游" },
};

const avatarDisplayName = computed(() => touristSettings.value.guide_name || AVATAR_MODEL_MAP[avatarConfig.value.modelKey]?.name || "小灵");
const avatarDisplaySubtitle = computed(() => touristSettings.value.guide_subtitle || AVATAR_MODEL_MAP[avatarConfig.value.modelKey]?.subtitle || "数字人导游");

async function loadAvatarConfig() {
  try {
    const config = await fetchAvatarConfig();
    avatarConfig.value.modelKey = normalizeAvatarPresetFromModelPath(config?.model_path, DEFAULT_AVATAR_PRESET);
    avatarConfig.value.voiceType = config?.voice_type || "gentle-female";
  } catch {
    // use default
  }
}

const query = ref("");
const pendingIntentQuery = ref("");
const voiceMode = ref(false);
const explanationLevel = ref("adult");
const transcribing = ref(false);
const transcriptionRequests = createLatestRequest();
const transcriptionConfidence = ref(-1);
const showConfirmBar = ref(false);
const transcriptionCandidates = ref([]);
const confirmedTranscript = ref("");
const pendingVoiceContext = ref(null);
const speechBaseQuery = ref("");
const speechSessionActive = ref(false);
const recorderError = ref("");
const messageListRef = ref(null);
const visionFileInputRef = ref(null);
const visionRequests = createLatestRequest();
const visionCaptureGuard = createVisionAsyncGuard();
const visionFile = ref(null);
const visionIdempotencyKey = ref("");
const visionPreviewUrl = ref("");
const visionResult = ref(null);
const visionAnalyzing = ref(false);
const visionError = ref("");
const visionPanelOpen = ref(false);
const visionCatalog = ref({ items: [] });
const visionSelectedSpot = ref("");
const visionCatalogLoading = ref(false);
const visionCatalogError = ref(false);
function resetVisionConfirmation() {
  visionSelectedSpot.value = "";
  visionCatalog.value = { items: [] };
  visionCatalogLoading.value = false;
  visionCatalogError.value = false;
}
const speechProgress = ref(0);
const speechElapsedMs = ref(0);
const speechDurationMs = ref(0);
const visemeTimeline = ref(null);
const activeAudioSegments = ref(0);
// 字幕同步：按播放进度定位当前句与当前字（后端 word_timeline + speechElapsedMs）
const activeSubtitle = computed(() => {
  const words = chatStore.subtitleWords;
  if (!words.length || activeAudioSegments.value === 0) return null;
  const elapsed = speechElapsedMs.value;
  const current =
    words.find((word) => elapsed >= word.begin_time && elapsed < word.end_time) || null;
  const anchor =
    current || words.find((word) => word.begin_time >= elapsed) || words[words.length - 1];
  const sentenceWords = words.filter((word) => word.sentence_index === anchor.sentence_index);
  return {
    words: sentenceWords,
    activeIndex: current ? sentenceWords.indexOf(current) : -1,
  };
});
const sourceHighlightIndex = ref(-1);
const emotionPanelExpanded = ref(false);
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

// 摄像头调用逻辑：拍照结果复用同一套 vision 上传链路
const {
  isSupported: cameraSupported,
  isActive: cameraActive,
  isStarting: cameraStarting,
  error: cameraError,
  bindVideo,
  start: startCamera,
  stop: stopCamera,
  capture: capturePhoto,
} = useCamera();
const activeTab = ref('chat')
const styleOptions = [
  { key: 'child', label: '儿童' },
  { key: 'adult', label: '标准' },
  { key: 'expert', label: '专业' },
]
let greetingTimer = null;
let pageActive = true;


function handleHotline(type) {
  if (chatStore.streaming) return
  textExpanded.value = true
  activeTab.value = "chat"
  const h = touristSettings.value.hotlines.find((hotline) => hotline.id === type && hotline.enabled)
  if (!h) return
  chatStore.messages.push({ role: 'assistant', content: `【${h.label}】请拨打景区服务热线：${h.number}` })
}

function closeVisionPanel() {
  visionPanelOpen.value = false
  visionRequests.cancel()
  visionCaptureGuard.cancel()
  resetVisionConfirmation()
  visionAnalyzing.value = false
  stopCamera()
}

function clearVisionPanel() {
  stopCamera()
  clearVisionState()
}

async function toggleCamera() {
  if (chatStore.streaming || visionAnalyzing.value) return
  if (cameraActive.value) {
    stopCamera()
    return
  }
  const started = await startCamera()
  if (started) {
    avatar.triggerAction("look_around")
  }
}

async function captureFromCamera() {
  if (!cameraActive.value || visionAnalyzing.value) return
  const file = await visionCaptureGuard.run(() => capturePhoto())
  if (!file) {
    return
  }
  visionRequests.cancel()
  visionCaptureGuard.cancel()
  resetVisionConfirmation()
  visionError.value = ""
  visionResult.value = null
  visionFile.value = file
  visionIdempotencyKey.value = createIdempotencyKey()
  revokeVisionPreview()
  visionPreviewUrl.value = URL.createObjectURL(file)
  stopCamera()
}

const voiceSupported = computed(() => speechSupported.value || recorderSupported.value);
const EMOTION_LABELS = {
  positive: "积极",
  neutral: "中性",
  confused: "困惑",
  dissatisfied: "不满",
  anxious: "焦虑",
  urgent: "紧急",
};
const RESPONSE_STRATEGY_LABELS = {
  positive: "亲切轻快",
  neutral: "自然讲解",
  confused: "简化并分步说明",
  dissatisfied: "致歉并解决问题",
  anxious: "安抚并优先指引",
  urgent: "应急安全优先",
};
const emotionAnalysis = computed(() => chatStore.emotionAnalysis);
const textEmotionSignal = computed(() =>
  emotionAnalysis.value?.signals?.find((signal) => signal.source === "text_rules") || null,
);
const audioEmotionSignal = computed(() =>
  emotionAnalysis.value?.signals?.find((signal) => signal.source !== "text_rules") || null,
);
const emotionPanelTitle = computed(() =>
  emotionAnalysis.value?.modalities?.includes("audio") ? "多模态情绪" : "文本情绪",
);
const emotionModalitiesText = computed(() => {
  const modalities = emotionAnalysis.value?.modalities || [];
  if (modalities.includes("text") && modalities.includes("audio")) return "文本 + 声音";
  if (modalities.includes("audio")) return "声音";
  return "文本";
});
const responseStrategyLabel = computed(() =>
  RESPONSE_STRATEGY_LABELS[emotionAnalysis.value?.response_strategy] || "自然讲解",
);
const speechPreviewText = computed(() => speechInterimText.value || speechFinalText.value);
const confidenceLevelClass = computed(() => {
  if (transcriptionConfidence.value >= 0.7) return "conf-high";
  if (transcriptionConfidence.value >= 0.4) return "conf-mid";
  if (transcriptionConfidence.value >= 0) return "conf-low";
  return "";
});
const voiceErrorMessage = computed(
  () => getSpeechErrorMessage(speechError.value) || recorderError.value,
);

const avatarReady = computed(() => avatarLoaded.value && !avatarError.value);
const voiceReady = computed(() => voiceSupported.value);
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

const explanationLevelLabel = computed(() => ({
  child: "亲子游",
  adult: "休闲游",
  expert: "文化深度游",
}[explanationLevel.value] || "休闲游"));

const visionDisplayHints = computed(() => {
  const result = visionResult.value;
  if (!result) {
    return [];
  }
  return normalizeVisionHints([
    ...(result.candidate_attractions || []),
    result.detected_text,
    ...(result.query_hints || []),
    ...(result.visual_tags || []),
  ]).slice(0, 18);
});

const selectedSources = ref(null);
const displayedSources = computed(() => selectedSources.value ?? chatStore.sources);
watch(() => chatStore.sources, () => { selectedSources.value = null; });

function renderAnswer(message, isLastMessage) {
  const isStreaming = chatStore.streaming && isLastMessage;
  return renderMarkdown(message.content, message.sources || [], isStreaming);
}

function showMessageSources(message) {
  selectedSources.value = message.sources || [];
  textExpanded.value = true;
  activeTab.value = "source";
  sourceHighlightIndex.value = -1;
}

function handleCitationClick(event, message) {
  const cite = event.target.closest(".citation");
  if (!cite) return;
  const evidenceId = cite.dataset.evidenceId;
  selectedSources.value = message.sources || [];
  highlightSource(evidenceId);
}

function highlightSource(evidenceId) {
  const index = displayedSources.value.findIndex(
    source => source.evidence_id === `证据${evidenceId}`,
  );
  if (index >= 0) {
    textExpanded.value = true;
    activeTab.value = "source";
    sourceHighlightIndex.value = index;
    nextTick(() => {
      document.querySelector(`[data-source-index="${index}"]`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
    setTimeout(() => {
      sourceHighlightIndex.value = -1;
    }, 2000);
  }
}


function toggleVisionPanel() {
  if (visionPanelOpen.value) closeVisionPanel();
  else visionPanelOpen.value = true;
}

function scrollToBottom() {
  nextTick(() => {
    const el = messageListRef.value;
    if (el) {
      el.scrollTop = chatStore.messages.length > 1 ? el.scrollHeight : 0;
    }
  });
}

watch(
  () => chatStore.messages.length,
  () => scrollToBottom(),
);

watch(
  () => chatStore.emotionAnalysis,
  () => {
    emotionPanelExpanded.value = false;
  },
);

watch(
  () => {
    const messages = chatStore.messages;
    return messages.length > 0 ? messages[messages.length - 1].content : "";
  },
  () => scrollToBottom(),
);

watch(
  () => chatStore.streaming,
  (streaming) => {
    if (!streaming && activeAudioSegments.value === 0) {
      setTimeout(() => {
        if (
          activeAudioSegments.value === 0
          && (avatar.currentState.value === "speaking" || avatar.currentState.value === "thinking")
        ) {
          avatar.setState("idle");
        }
      }, 600);
    }
  },
);

watch([speechFinalText, speechInterimText], ([finalText, interimText]) => {
  if (!speechSessionActive.value) {
    return;
  }
  query.value = mergeSpeechInput(speechBaseQuery.value, finalText, interimText);
});

watch(speechListening, (listening, wasListening) => {
  if (!listening && wasListening) {
    voiceMode.value = false;
    if (speechSessionActive.value) {
      query.value = mergeSpeechInput(speechBaseQuery.value, speechFinalText.value, "");
      pendingVoiceContext.value = {
        audio_emotion: null,
        audio_confidence: 0,
        audio_source: "browser_speech_recognition",
        audio_event: null,
      };
      speechSessionActive.value = false;
      avatar.setState("idle");
      // 浏览器语音识别结束后自动发送
      const voiceCtx = pendingVoiceContext.value;
      pendingVoiceContext.value = null;
      submitQuery(query.value, voiceCtx ? {
        inputMode: "voice",
        emotionContext: voiceCtx,
      } : {});
    }
  }
});

onMounted(() => {
  toolMedia.addEventListener("change", syncPanels);
  syncToolDialog();
  interactionStore.initialize();
  loadAvatarConfig();

  startWeather();

  try {
    const pendingStyle = window.sessionStorage.getItem(GUIDE_STYLE_STORAGE_KEY);
    if (pendingStyle && ["child", "adult", "expert"].includes(pendingStyle)) {
      explanationLevel.value = pendingStyle;
      window.sessionStorage.removeItem(GUIDE_STYLE_STORAGE_KEY);
    }
  } catch {}

  if (chatStore.messages.length === 0) {
    greetingTimer = window.setTimeout(async () => {
      if (chatStore.messages.length === 0) {
        const greeting = welcomeText.value || `您好！我是${touristSettings.value.brand_name}的${avatarDisplayName.value}，很高兴陪您一起游览。`;
        chatStore.messages.push({
          role: "assistant",
          content: greeting,
          isWelcome: true,
        });
        avatar.triggerAction("welcome_invite");
        // 使用百炼预生成的欢迎语音频
        try {
          const audio = await fetchWelcomeAudio();
          if (!pageActive || chatStore.streaming || chatStore.messages.length !== 1) return;
          if (audio && audio.base64_audio) {
            avatar.setState("speaking");
            audioPlayer.enqueue(
              audio.base64_audio,
              audio.duration_ms || greeting.length * 200,
              () => { avatar.setState("idle"); },
              "", // no text fallback — use the pre-generated audio only
              (progress, elapsedMs, durationMs, timeline) => {
                speechProgress.value = progress;
                speechElapsedMs.value = elapsedMs;
                speechDurationMs.value = durationMs;
                if (timeline) visemeTimeline.value = timeline;
              },
              { rate: speechRate.value, volume: 0.8 },
            );
          }
        } catch {
          // 百炼音频不可用时静默降级，不播放
        }
      }
      greetingTimer = null;
    }, 800);
  }
});

onBeforeUnmount(() => {
  pageActive = false;
  visionRequests.cancel()
  visionCaptureGuard.cancel();
  transcriptionRequests.cancel();
  toolMedia.removeEventListener("change", syncPanels);
  stopCamera();
  if (greetingTimer) {
    window.clearTimeout(greetingTimer);
  }
  try { chatStore.stopOutput(); } catch {}
  try { abortSpeechRecognition(); } catch {}
  if (isRecording.value) {
    try { stopRecording(); } catch {}
  }
  try { revokeVisionPreview(); } catch {}
  try { avatar.setState("idle"); } catch {}
  try { stopWeather(); } catch {}
});

function handleSubmit() {
  if (speechListening.value || isRecording.value || transcribing.value) {
    return;
  }
  voiceMode.value = false;
  const voiceContext = pendingVoiceContext.value;
  pendingVoiceContext.value = null;
  submitQuery(query.value, voiceContext ? {
    inputMode: "voice",
    emotionContext: voiceContext,
  } : {});
}

function handleAvatarLoadError() {
  avatarLoaded.value = false;
  avatarError.value = true;
}

function handleAvatarLoaded() {
  avatarLoaded.value = true;
  avatarError.value = false;
}

function handleFollowup(followupQuery) {
  submitQuery(followupQuery);
}

function continuePendingIntentAsQuestion() {
  const value = pendingIntentQuery.value;
  pendingIntentQuery.value = "";
  if (value) submitQuery(value, { forceQA: true });
}

function continuePendingIntentAsEdit() {
  const value = pendingIntentQuery.value;
  pendingIntentQuery.value = "";
  if (value) requestItineraryProposal(value);
}

function stopAudioOutput() {
  const active = audioPlayer.activePlayback.value;
  if (active?.owner === "map-narration") audioPlayer.stop(active.id);
  else chatStore.stopOutput();
}

function handleQuickQuestion(question) {
  submitQuery(question);
}

function retryLastAnswer() {
  return chatStore.retryLastMessage({
    ttsConfig: { playbackRate: speechRate.value },
  });
}

function replayAnswer(message) {
  return chatReplay.replay(message);
}

function submitQuery(rawQuery, extraOptions = {}) {
  const value = rawQuery.trim();
  if (!value || chatStore.streaming) {
    return;
  }
  if (!extraOptions.forceQA && isItineraryEditIntent(value)) {
    revealItineraryConversation();
    requestItineraryProposal(value);
    query.value = "";
    return;
  }
  if (!extraOptions.forceQA && isAmbiguousItineraryIntent(value)) {
    revealItineraryConversation();
    pendingIntentQuery.value = value;
    query.value = "";
    return;
  }
  // 讲解方式不再拼进问题文本：前缀会污染 raw_query / 检索 / FAQ 匹配 / 缓存键。
  // 改为随请求发送 audience，由服务端注入 system prompt。
  const finalQuery = value;
  avatar.setState("thinking");
  try {
    chatStore.sendMessage(finalQuery, interactionStore.selectionPayload, {
      audience: explanationLevel.value,
      ttsConfig: {
        voiceType: avatarConfig.value.voiceType,
        playbackRate: speechRate.value,
        volume: 80,
      },
      onContext: (selection) => interactionStore.applyResolvedSelection(selection),
      onAttractionSelectionStale: () => {
        interactionStore.clearSelection();
        interactionStore.loaded = false;
        interactionStore.bootstrap.attractions = [];
      },
      onThinking: () => avatar.setState("thinking"),
      onAvatar: (payload) => {
        try {
          avatar.handleAvatarEvent(payload);
        } catch {
          avatarError.value = true;
        }
      },
      onAudioStart: () => {
        activeAudioSegments.value += 1;
        avatar.setState("speaking");
      },
      onAudioEnded: () => {
        activeAudioSegments.value = Math.max(activeAudioSegments.value - 1, 0);
        if (activeAudioSegments.value === 0) {
          avatar.setState("idle");
          speechProgress.value = 0;
          speechElapsedMs.value = 0;
          speechDurationMs.value = 0;
          visemeTimeline.value = null;
          chatStore.clearSubtitleWords();
        }
      },
      onPlaybackStopped: () => {
        activeAudioSegments.value = 0;
        speechProgress.value = 0;
        speechElapsedMs.value = 0;
        speechDurationMs.value = 0;
        visemeTimeline.value = null;
        chatStore.clearSubtitleWords();
        if (!mapNarrationActive.value) avatar.setState("idle");
      },
      onSpeechProgress: (progress, elapsedMs, timeline, actualDurationMs) => {
        speechProgress.value = progress;
        speechElapsedMs.value = elapsedMs;
        speechDurationMs.value = actualDurationMs;
        visemeTimeline.value = timeline;
      },
      ...extraOptions,
    });
  } catch {
    avatarError.value = true;
  }
  query.value = "";
  activeTab.value = "chat";
}

function isAmbiguousItineraryIntent(value) {
  if (tourStore.current?.snapshot?.schema_version !== 2) return false;
  const mentionsPlan = /行程|路线|游览|景点|游玩|安排/.test(value);
  const preferenceOrAdjustment = /轻松|少走|不想走|别太累|避开人多|不排队|带老人|带孩子|下雨|剩余.*(?:分钟|小时)|时间不够|来不及|调整|改改/.test(value);
  return mentionsPlan && preferenceOrAdjustment;
}
function revealItineraryConversation() {
  activeTab.value = "chat";
  if (activeTool.value) setTool(null);
  textExpanded.value = true;
}
function requestItineraryProposal(value) {
  revealItineraryConversation();
  tourStore.requestProposal(value);
}
async function toggleRecording() {
  if (chatStore.streaming || transcribing.value) {
    return;
  }

  recorderError.value = "";

  // 退出语音模式
  if (voiceMode.value) {
    voiceMode.value = false;
    if (speechListening.value) {
      stopSpeechRecognition();
    }
    // 如果正在录音，不在此处调用 stopRecording，而是继续走到"正在录音 → 转文字"分支
    if (!isRecording.value) {
      return;
    }
    // isRecording=true 时继续往下走，进入下方录音转文字逻辑
  }

  // 正在聆听 → 结束聆听
  if (speechListening.value) {
    stopSpeechRecognition();
    voiceMode.value = false;
    return;
  }

  // 正在录音 → 停止并转文字
  if (isRecording.value) {
    const audioBlob = await stopRecording();
    if (!audioBlob) {
      avatar.setState("idle");
      return;
    }
    const transcriptionRequest = transcriptionRequests.begin();
    transcribing.value = true;
    try {
      const result = await transcribeAudio(audioBlob, {
        signal: transcriptionRequest.signal,
        idempotencyKey: createIdempotencyKey(),
      });
      if (!transcriptionRequest.isCurrent()) return;
      pendingVoiceContext.value = {
        audio_emotion: result?.emotion || null,
        audio_confidence: typeof result?.emotion_confidence === "number"
          ? result.emotion_confidence
          : 0,
        audio_source: result?.emotion_source || "sensevoice",
        audio_event: result?.audio_event || null,
      };
      if (!result || !result.text) {
        recorderError.value = result?.error_message || "没听清楚，请靠近麦克风重新说一遍，或直接打字输入。";
        if (result && Array.isArray(result.candidates) && result.candidates.length > 0) {
          transcriptionCandidates.value = result.candidates.slice(0, 3);
        }
        showConfirmBar.value = false;
        transcriptionConfidence.value = -1;
        avatar.setState("idle");
        return;
      }

      transcriptionConfidence.value = displayableASRConfidence(result);
      transcriptionCandidates.value = Array.isArray(result.candidates) ? result.candidates : [];

      if (result.confidence >= 0.7 && !result.needs_confirmation) {
        query.value = result.text;
        showConfirmBar.value = false;
        confirmedTranscript.value = result.text;
        voiceMode.value = false;
        transcribing.value = false;
        avatar.setState("idle");
        // 高置信度结果自动发送
        const voiceCtx = pendingVoiceContext.value;
        pendingVoiceContext.value = null;
        submitQuery(result.text, voiceCtx ? {
          inputMode: "voice",
          emotionContext: voiceCtx,
        } : {});
        return;
      } else if (result.confidence >= 0.4 || result.needs_confirmation) {
        query.value = result.text;
        confirmedTranscript.value = result.text;
        showConfirmBar.value = true;
      } else {
        query.value = "";
        confirmedTranscript.value = "";
        showConfirmBar.value = false;
        if (transcriptionCandidates.value.length > 0) {
          recorderError.value = "没听清楚，请靠近麦克风重新说一遍，选择候选项或直接打字输入。";
        } else {
          recorderError.value = "没听清楚，请靠近麦克风重新说一遍，或直接打字输入。";
        }
      }
    } catch (error) {
      if (!transcriptionRequest.isCurrent()) return;
      recorderError.value = getTranscriptionErrorMessage(error);
      showConfirmBar.value = false;
      transcriptionConfidence.value = -1;
    } finally {
      if (transcriptionRequest.isCurrent()) {
        transcribing.value = false;
        voiceMode.value = false;
      }
    }
    avatar.setState("idle");
    return;
  }

  audioPlayer.stop();

  // 进入语音模式
  voiceMode.value = true;

  if (recorderSupported.value) {
    pendingVoiceContext.value = null;
    avatar.setState("listening");
    await startRecording();
    if (!isRecording.value) {
      recorderError.value = "当前浏览器无法使用麦克风，请改用文字输入。";
      voiceMode.value = false;
      avatar.setState("idle");
    }
    return;
  }

  if (speechSupported.value) {
    pendingVoiceContext.value = null;
    speechBaseQuery.value = query.value.trim();
    speechSessionActive.value = true;
    avatar.setState("listening");
    const started = startSpeechRecognition();
    if (!started) {
      speechSessionActive.value = false;
      voiceMode.value = false;
      avatar.setState("idle");
    }
    return;
  }

  avatar.setState("listening");
  await startRecording();
  if (!isRecording.value) {
    recorderError.value = "当前浏览器无法使用麦克风，请改用文字输入。";
    voiceMode.value = false;
    avatar.setState("idle");
  }
}

function cancelTranscription() {
  transcriptionRequests.cancel();
  transcribing.value = false;
  voiceMode.value = false;
  pendingVoiceContext.value = null;
  recorderError.value = "已取消识别，可重新录音或使用文字输入。";
  avatar.setState("idle");
}

function dismissConfirmBar() {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
  pendingVoiceContext.value = null;
  textInputExpanded.value = true;
  nextTick(() => queryInputRef.value?.focus());
}

function confirmAndSubmit() {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
  avatar.triggerAction("agree");
  if (query.value.trim()) {
    handleSubmit();
  }
}

function retryRecording() {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
  query.value = confirmedTranscript.value;
  pendingVoiceContext.value = null;
  avatar.setState("listening");
  startRecording();
}

function selectCandidate(candidateText) {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
  query.value = candidateText;
  avatar.triggerAction("agree");
  handleSubmit();
}

function mergeSpeechInput(baseText, finalText, interimText) {
  return [baseText, finalText, interimText]
    .map((item) => item.trim())
    .filter(Boolean)
    .join(" ");
}

function emotionLabel(label) {
  return EMOTION_LABELS[label] || "中性";
}

function formatEmotionPercent(value) {
  const normalized = typeof value === "number" ? value : 0;
  return `${Math.round(Math.max(0, Math.min(normalized, 1)) * 100)}%`;
}

function getSpeechErrorMessage(errorCode) {
  if (!errorCode || errorCode === "aborted") {
    return "";
  }
  const messages = {
    "not-allowed": "麦克风权限被拒绝，请在浏览器地址栏中允许麦克风后重试。",
    "service-not-allowed": "浏览器未允许语音识别服务，请检查网站权限。",
    "audio-capture": "没有检测到可用麦克风，请检查设备连接。",
    "no-speech": "没有识别到语音，请靠近麦克风后重试。",
    network: "浏览器语音识别服务暂时不可用，请检查网络或改用文字输入。",
    "language-not-supported": "当前浏览器不支持中文语音识别。",
    "not-supported": "当前浏览器不支持语音识别，请使用 Chrome 或改用文字输入。",
    "start-failed": "语音识别启动失败，请稍后重试。",
    InvalidStateError: "语音识别正在运行，请结束当前识别后重试。",
  };
  return messages[errorCode] || `语音识别失败（${errorCode}），请重试或改用文字输入。`;
}

function openVisionFilePicker() {
  visionFileInputRef.value?.click();
}

function handleVisionFileChange(event) {
  const file = event.target.files?.[0];
  visionRequests.cancel()
  visionCaptureGuard.cancel();
  visionAnalyzing.value = false;
  resetVisionConfirmation();
  visionFile.value = null;
  visionIdempotencyKey.value = "";
  revokeVisionPreview();
  visionError.value = "";
  visionResult.value = null;
  if (!file) {
    return;
  }
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    visionError.value = "请选择 JPEG、PNG 或 WebP 图片。";
    event.target.value = "";
    return;
  }
  if (file.size > MAX_IMAGE_BYTES) {
    visionError.value = "图片不能超过 5MB。";
    event.target.value = "";
    return;
  }
  visionFile.value = file;
  visionIdempotencyKey.value = createIdempotencyKey();
  revokeVisionPreview();
  visionPreviewUrl.value = URL.createObjectURL(file);
}

async function handleAnalyzeImage() {
  if (!visionFile.value || visionAnalyzing.value) {
    return;
  }
  visionCaptureGuard.cancel();
  const request = visionRequests.begin();
  resetVisionConfirmation();
  visionAnalyzing.value = true;
  avatar.triggerAction("look_around");
  visionError.value = "";
  visionResult.value = null;
  try {
    const result = await analyzeImage(
      visionFile.value,
      "这张图片可能对应景区哪个位置？请提取可用于景区资料检索的线索。",
      { signal: request.signal, idempotencyKey: visionIdempotencyKey.value },
    );
    if (request.isCurrent()) {
      visionResult.value = result;
      visionCatalogLoading.value = true;
      visionCatalogError.value = false;
      try {
        const catalog = await fetchItineraryCatalog();
        if (request.isCurrent()) visionCatalog.value = catalog;
      } catch {
        if (request.isCurrent()) visionCatalogError.value = true;
      } finally {
        if (request.isCurrent()) visionCatalogLoading.value = false;
      }
    }
  } catch (error) {
    if (!request.isCurrent()) return;
    visionError.value = getVisionErrorMessage(error);
  } finally {
    if (request.isCurrent()) visionAnalyzing.value = false;
  }
}

function askFromImage() {
  const retrievalQuery = visionResult.value?.retrieval_query?.trim();
  if (!retrievalQuery) {
    return;
  }
  const confirmation = visionConfirmation(visionCatalog.value, visionSelectedSpot.value);
  const submittedResult = visionResult.value;
  const visionRequest = buildVisionChatRequest(submittedResult, confirmation);
  submitQuery(visionRequest.query, {
    visionContext: visionRequest.visionContext,
    onVisionConfirmationStale: () => {
      if (visionResult.value !== submittedResult) return;
      visionSelectedSpot.value = "";
      visionCatalog.value = { items: [] };
      visionCatalogError.value = true;
      visionError.value = "所选景点已更新或下架，请关闭并重新打开识景面板，重新选择。";
    },
  });
}

function clearVisionState() {
  visionRequests.cancel()
  visionCaptureGuard.cancel();
  resetVisionConfirmation();
  visionAnalyzing.value = false;
  visionFile.value = null;
  visionIdempotencyKey.value = "";
  visionResult.value = null;
  visionError.value = "";
  if (visionFileInputRef.value) {
    visionFileInputRef.value.value = "";
  }
  revokeVisionPreview();
}

function revokeVisionPreview() {
  if (visionPreviewUrl.value) {
    URL.revokeObjectURL(visionPreviewUrl.value);
    visionPreviewUrl.value = "";
  }
}

function normalizeVisionHints(values) {
  const seen = new Set();
  const hints = [];
  values.flatMap(flattenVisionHint).forEach((value) => {
    const normalized = String(value ?? "").replace(/\s+/g, " ").trim();
    if (!normalized || normalized === "[]" || normalized === "{}" || normalized.toLowerCase() === "null") {
      return;
    }
    if (seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    hints.push(normalized);
  });
  return hints;
}

function flattenVisionHint(value) {
  if (Array.isArray(value)) {
    return value.flatMap(flattenVisionHint);
  }
  if (value && typeof value === "object") {
    return [value.text || value.content || value.value || ""];
  }
  return [value];
}

function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatConfidence(value) {
  if (typeof value !== "number") {
    return "未知";
  }
  return `${Math.round(value * 100)}%`;
}

// Tool navigation changes only the panel. The avatar and conversation remain mounted.
const toolDefinitions = [
  { id: "explore", title: "景点探索", icon: "map", component: ExploreView },
  { id: "map", title: "实时地图", icon: "landmark", component: MapView },
  { id: "route", title: "智能路线", icon: "route", component: RouteView },
  { id: "quiz", title: "文化故事", icon: "book", component: QuizView },
];
const tools = computed(() => {
  const configured = new Map(touristSettings.value.modules.map((module) => [module.id, module]));
  return toolDefinitions
    .map((tool, fallbackOrder) => ({ ...tool, ...(configured.get(tool.id) || {}), fallbackOrder }))
    .filter((tool) => tool.enabled !== false)
    .sort((a, b) => a.order - b.order || a.fallbackOrder - b.fallbackOrder);
});
const activeTool = computed(() => tools.value.some(tool => tool.id === route.query.tool) ? route.query.tool : "");
const selectedTool = computed(() => tools.value.find(tool => tool.id === activeTool.value));
const toolDialogRef = ref(null);
const toolHeadingRef = ref(null);
const visionDialogRef = ref(null);
const queryInputRef = ref(null);
const toolMedia = window.matchMedia("(min-width: 1000px)");
const textExpanded = ref(false);
const textInputExpanded = ref(false);
const textDialogRef = ref(null);
const voiceStageStatus = computed(() => {
  if (transcribing.value) return "正在识别你的问题…";
  if (speechListening.value || isRecording.value) return "正在聆听，请说出你的问题";
  if (audioPlayer.isPlaying.value) return "正在为你讲解";
  if (chatStore.streaming) return "正在准备讲解…";
  if (chatStore.userStopped) return "讲解已停止，可以继续提问";
  if (chatStore.voiceFallback) return "语音暂不可用，可查看文字讲解";
  if (chatStore.errorMessage) return "讲解暂不可用，请稍后再试";
  return "";
});
const narrationSummary = computed(() => {
  const message = [...chatStore.messages].reverse().find(item => item.role === "assistant" && !item.isWelcome && item.content);
  return message ? message.content.replace(/[#*`>]/g, "").replace(/\[证据[^\]]*\]/g, "").slice(0, 120) : "";
});
function toggleTextInput() {
  textInputExpanded.value = !textInputExpanded.value;
  if (textInputExpanded.value) nextTick(() => queryInputRef.value?.focus());
}
function toggleTextPanel() { textExpanded.value = !textExpanded.value; }
function closeTextPanel() {
  textExpanded.value = false;
  nextTick(() => document.getElementById("text-panel-trigger")?.focus({ preventScroll: true }));
}
function syncTextDialog() {
  const dialog = textDialogRef.value;
  if (!dialog) return;
  if (dialog.open) dialog.close();
  if (textExpanded.value) {
    if (toolMedia.matches) dialog.show();
    else dialog.showModal();
    nextTick(() => document.getElementById(activeTab.value + "-tab")?.focus({ preventScroll: true }));
  }
}
watch(textExpanded, () => nextTick(syncTextDialog));
watch(() => [chatStore.voiceFallback, chatStore.streaming, chatStore.errorMessage], ([fallback, streaming, error]) => {
  if (!streaming && (fallback || error)) textExpanded.value = true;
});
const inputBusy = computed(() => chatStore.streaming || speechListening.value || isRecording.value || transcribing.value);

let toolQuestionGeneration = 0;
function setTool(id) {
  toolQuestionGeneration += 1;
  const query = { ...route.query };
  delete query.selector;
  if (id && id !== activeTool.value) query.tool = id;
  else delete query.tool;
  router.replace({ path: "/tourist", query }).catch(() => {});
}
function handleTabKey(event) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  activeTab.value = event.key === "Home" ? "chat" : event.key === "End" ? "source" : activeTab.value === "chat" ? "source" : "chat";
  nextTick(() => document.getElementById(activeTab.value + "-tab")?.focus());
}
function closeTool() {
  toolQuestionGeneration += 1;
  const previous = activeTool.value;
  const query = { ...route.query };
  delete query.tool;
  router.replace({ path: "/tourist", query }).then(() => {
    document.getElementById("tool-trigger-" + previous)?.focus({ preventScroll: true });
  }).catch(() => {});
}
function syncPanels() { syncToolDialog(); syncTextDialog(); }
function syncToolDialog() {
  const dialog = toolDialogRef.value;
  if (!dialog) return;
  if (dialog.open) dialog.close();
  if (activeTool.value) {
    if (toolMedia.matches) dialog.show();
    else dialog.showModal();
    nextTick(() => toolHeadingRef.value?.focus({ preventScroll: true }));
  }
}
function handleDialogBackdrop(event, close) {
  if (event.target !== event.currentTarget) return;
  const rect = event.currentTarget.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
}
async function handleToolQuestion(payload) {
  if (inputBusy.value) return;
  const generation = ++toolQuestionGeneration;
  const originTool = activeTool.value;
  let namedAttractionId = null;
  if (!payload.routeId && !payload.attractionId && payload.attraction) {
    namedAttractionId = await resolvePublishedAttraction(payload.attraction, interactionStore);
    if (generation !== toolQuestionGeneration || activeTool.value !== originTool || inputBusy.value) return;
  }
  interactionStore.clearSelection();
  if (payload.routeId) interactionStore.selectRoute(payload.routeId);
  else if (payload.attractionId) interactionStore.selectAttraction(payload.attractionId);
  else if (payload.attraction) {
    const attractionId = namedAttractionId;
    if (attractionId === null) {
      chatStore.errorMessage = "无法确认所选景点的已发布资料，请稍后重试或选择其他景点。";
      chatStore.retryAvailable = false;
      closeTool();
      return;
    }
    interactionStore.selectAttraction(attractionId);
  }
  submitQuery(payload.query, { displayQuery: payload.query });
  closeTool();
}
watch(activeTool, () => nextTick(syncToolDialog));
watch(visionPanelOpen, async (open) => {
  await nextTick();
  if (open !== visionPanelOpen.value) return;
  const dialog = visionDialogRef.value;
  if (open && !dialog.open) {
    dialog.showModal();
    if (visionResult.value && !visionCatalog.value.items?.length) {
      const request = visionRequests.begin();
      visionCatalogLoading.value = true;
      visionCatalogError.value = false;
      try {
        const catalog = await fetchItineraryCatalog();
        if (request.isCurrent()) visionCatalog.value = catalog;
      } catch {
        if (request.isCurrent()) visionCatalogError.value = true;
      } finally {
        if (request.isCurrent()) visionCatalogLoading.value = false;
      }
    }
  }
  else if (!open && dialog.open) dialog.close();
});

</script>

<style scoped src="../../assets/guide-page.css"></style>
<style scoped>
.itinerary-proposal { margin: 10px 0; padding: 12px; border: 1px solid #d6e2d8; border-radius: 12px; background: #f7faf6; color: #3d5948; font-size: 13px; }
.itinerary-proposal header { display: flex; justify-content: space-between; align-items: center; }
.itinerary-proposal p { margin: 7px 0; line-height: 1.5; }
.itinerary-proposal ul { display: grid; gap: 5px; padding-left: 20px; }
.itinerary-proposal button { min-height: 32px; margin: 3px; padding: 5px 10px; border: 1px solid #315b48; border-radius: 8px; background: #315b48; color: white; }
.itinerary-proposal header button, .itinerary-proposal button + button { background: white; color: #315b48; }
.itinerary-proposal[role="status"] { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.speech-rate-control { display: inline-flex; align-items: center; gap: 5px; color: var(--guide-muted, #68766f); font-size: 12px; }
.speech-rate-control select { min-height: 34px; border: 1px solid var(--guide-line, #d9e2dc); border-radius: 8px; padding: 4px 7px; background: white; color: inherit; }
.itinerary-proposal-error { color: #a34535; font-size: 12px; }
</style>
