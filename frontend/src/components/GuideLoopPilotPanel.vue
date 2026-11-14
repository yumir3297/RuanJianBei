<template>
  <section class="guide-loop-panel">
    <header class="panel-header">
      <div><h2>GuideLoop 知识演化试验</h2><p>管理员导入的脱敏观察 → 来源审核 → 版本发布 → 游客新会话复测</p></div>
      <el-button :loading="loading" @click="loadCases">刷新待办</el-button>
    </header>
    <el-alert type="info" :closable="false" title="试验数据仅用于开发演示；合成场次不代表真实运营安排。" />
    <el-alert v-if="error" type="error" :closable="false" :title="error" />
    <div class="case-list">
      <article v-for="item in cases" :key="item.cluster_id" class="case-card">
        <div class="case-title"><strong>{{ item.cluster_id }}</strong><el-tag size="small">{{ item.category }}</el-tag><el-tag size="small" type="info">{{ item.status }}</el-tag><el-tag v-if="item.clarification_required" size="small" type="warning">待人工澄清：{{ item.clarification_reasons.join("、") }}</el-tag></div>
        <p>独立会话 {{ item.distinct_session_count }} · 观察 {{ item.observation_count }} · 回放 {{ item.replay_ids.join("、") || "无" }}</p>
        <ul><li v-for="question in item.sample_questions" :key="question">{{ question }}</li></ul>
        <el-form label-position="top" class="draft-form">
          <el-form-item label="景点 ID"><el-select v-model="stateFor(item).form.poi_id" :disabled="stateFor(item).busy || stateFor(item).published" @change="invalidateDraft(item)"><el-option label="九龙灌浴" value="bathing"/><el-option label="灵山大佛" value="buddha"/></el-select></el-form-item>
          <el-form-item label="对象 ID"><el-input v-model="stateFor(item).form.target_id" placeholder="例如 prince / bath_show" :disabled="stateFor(item).busy || stateFor(item).published" @input="invalidateDraft(item)"/></el-form-item>
          <el-form-item label="修订类型"><el-select v-model="stateFor(item).form.action" :disabled="stateFor(item).busy || stateFor(item).published" @change="invalidateDraft(item)"><el-option label="新增口语别名" value="add_alias"/><el-option label="替换事实" value="replace_fact"/><el-option label="撤回" value="withdraw"/></el-select></el-form-item>
          <el-form-item v-if="stateFor(item).form.action === 'add_alias'" label="游客别名"><el-input v-model="stateFor(item).form.alias" :disabled="stateFor(item).busy || stateFor(item).published" @input="invalidateDraft(item)"/></el-form-item>
          <el-form-item v-if="stateFor(item).form.action !== 'withdraw'" label="人工审核后的回答"><el-input v-model="stateFor(item).form.answer" type="textarea" :rows="2" :disabled="stateFor(item).busy || stateFor(item).published" @input="invalidateDraft(item)"/></el-form-item>
          <el-form-item label="证据 ID"><el-input v-model="stateFor(item).form.evidence_id" :disabled="stateFor(item).busy || stateFor(item).published" @input="invalidateDraft(item)"/></el-form-item>
          <el-form-item label="来源说明（需人工核验支持关系）"><el-input v-model="stateFor(item).form.source_ref" :disabled="stateFor(item).busy || stateFor(item).published" @input="invalidateDraft(item)"/></el-form-item>
          <el-form-item label="关联已发布知识（试验可留空）">
            <el-select :model-value="selectedKnowledge(item)" filterable clearable :loading="knowledgeLoading" :disabled="stateFor(item).busy || stateFor(item).published || knowledgeLoading || !!knowledgeError" placeholder="按条目 ID 或版本搜索" @change="selectKnowledge(item, $event)">
              <el-option v-for="option in knowledgeOptions" :key="option.entryId" :label="option.label" :value="option.entryId" />
            </el-select>
          </el-form-item>
          <el-form-item label="已选知识版本"><span>{{ stateFor(item).form.knowledge_revision_id || "未绑定（仅试验）" }}</span></el-form-item>
          <el-form-item label="生效起始（ISO 时间）"><el-input v-model="stateFor(item).form.effective_from" :disabled="stateFor(item).busy || stateFor(item).published" @input="invalidateDraft(item)"/></el-form-item>
          <el-form-item label="基线版本"><el-input v-model="stateFor(item).form.base_revision" :disabled="stateFor(item).busy || stateFor(item).published" @input="invalidateDraft(item)"/></el-form-item>
        </el-form>
        <el-alert v-if="knowledgeError" type="error" :closable="false" :title="`知识列表加载失败：${knowledgeError}`" />
        <el-alert v-else-if="stateFor(item).form.knowledge_revision_id && !knowledgeLoading && !isCurrentKnowledgeSelection(stateFor(item).form, knowledgeOptions)" type="warning" :closable="false" title="所选知识版本已变更或下架，请重新选择并保存草稿。" />
        <el-button size="small" :loading="knowledgeLoading" @click="loadKnowledge">刷新已发布知识</el-button>
        <div class="actions">
          <el-button :disabled="stateFor(item).published" :loading="stateFor(item).busy" @click="saveDraft(item)">保存草稿</el-button>
          <el-button :disabled="!stateFor(item).draftId || stateFor(item).dirty || stateFor(item).published" :loading="stateFor(item).busy" @click="verify(item)">技术路由验证</el-button>
          <el-checkbox :model-value="stateFor(item).sourceReviewed && stateFor(item).reviewedDraftId === stateFor(item).draftId" :disabled="stateFor(item).dirty || stateFor(item).published || !stateFor(item).verified" @change="setSourceReviewed(item, $event)">我已人工核对来源确实支持该回答</el-checkbox>
          <el-button type="primary" :disabled="!stateFor(item).verified || !stateFor(item).sourceReviewed || stateFor(item).reviewedDraftId !== stateFor(item).draftId || stateFor(item).dirty || stateFor(item).published" :loading="stateFor(item).busy" @click="publish(item)">发布版本</el-button>
        </div>
        <el-alert v-if="stateFor(item).verified" type="warning" :closable="false" title="技术验证仅检查结构和路由，不代表来源支持回答；发布前须由管理员人工核验事实与来源。" />
        <div v-if="stateFor(item).liveResult" class="live-result">
          <strong>新会话 SSE 复测</strong><p>{{ stateFor(item).liveResult.text || stateFor(item).liveResult.error }}</p>
          <small>决策：{{ stateFor(item).liveResult.context?.decision || "无" }} · 版本：{{ stateFor(item).liveResult.context?.revision_id || "无" }} · check：{{ stateFor(item).liveResult.context?.check_id || "无" }}</small>
          <p v-for="source in stateFor(item).liveResult.sources" :key="source.evidence_id">证据 {{ source.evidence_id }}：{{ source.source }}</p>
          <template v-if="stateFor(item).liveResult.context?.check_id">
            <el-button size="small" type="success" @click="confirm(stateFor(item).liveResult.context.check_id, true)">复测通过（人工核对）</el-button>
            <el-button size="small" type="danger" @click="confirm(stateFor(item).liveResult.context.check_id, false)">复测失败并重开</el-button>
          </template>
        </div>
        <div class="actions"><el-input v-model="stateFor(item).replayQuery" placeholder="发布后输入未参与编辑的新问法"/><el-button :disabled="!stateFor(item).published" :loading="stateFor(item).replaying" @click="replay(item)">游客真实 SSE 复测</el-button></div>
      </article>
      <el-empty v-if="!loading && !cases.length" description="暂无试验待办；请先通过受保护 API 导入脱敏观察事件"/>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { confirmGuideLoopLive, createGuideLoopDraft, fetchGuideLoopCases, publishGuideLoopDraft, replayGuideLoopQuestion, verifyGuideLoopDraft } from "../api/guideLoop";
import { buildGuideLoopDraftPayload } from "../api/guideLoopPayload";
import { fetchKnowledgeList } from "../api/knowledge";
import { applyKnowledgeSelection, isCurrentKnowledgeSelection, publishedKnowledgeOptions } from "../api/guideLoopKnowledge";
const cases=ref([]), loading=ref(false), error=ref("");
const knowledgeOptions=ref([]), knowledgeLoading=ref(false), knowledgeError=ref("");
const states=reactive({});
const initialForm={base_revision:"0",action:"add_alias",poi_id:"bathing",target_id:"prince",alias:"",answer:"",evidence_id:"",source_ref:"",knowledge_entry_id:"",knowledge_revision_id:"",effective_from:"2026-11-10T00:00:00+08:00"};
function stateFor(item){return states[item.cluster_id] ||= {form:{...initialForm},draftId:"",verified:false,sourceReviewed:false,reviewedDraftId:"",published:false,dirty:false,liveResult:null,replayQuery:"",busy:false,replaying:false};}
function invalidateDraft(item){const s=stateFor(item);s.dirty=true;s.verified=false;s.sourceReviewed=false;s.reviewedDraftId="";s.published=false;}
function selectedKnowledge(item){const form=stateFor(item).form;return isCurrentKnowledgeSelection(form,knowledgeOptions.value)?Number(form.knowledge_entry_id):undefined;}
function selectKnowledge(item,id){applyKnowledgeSelection(stateFor(item).form,knowledgeOptions.value.find(option=>option.entryId===id));invalidateDraft(item);}
async function loadKnowledge(){knowledgeLoading.value=true;knowledgeError.value="";knowledgeOptions.value=[];try{knowledgeOptions.value=publishedKnowledgeOptions(await fetchKnowledgeList());}catch(e){knowledgeError.value=e?.response?.data?.detail||e.message;}finally{knowledgeLoading.value=false;}}
function setSourceReviewed(item, value){const s=stateFor(item);s.sourceReviewed=Boolean(value);s.reviewedDraftId=value?s.draftId:"";}
async function loadCases(){loading.value=true;error.value="";for(const s of Object.values(states)){s.sourceReviewed=false;s.reviewedDraftId="";}try{cases.value=await fetchGuideLoopCases();for(const item of cases.value){const s=stateFor(item);if(item.draft){const d=item.draft;const loadedDraftId=item.draft_id||"";const published=item.status==="published_pending_check";s.draftId=loadedDraftId;s.form={base_revision:(published||item.status==="reopened")?(item.active_revision_id||d.base_revision):d.base_revision,action:d.action,poi_id:d.poi_id,target_id:d.target_id,alias:d.alias||"",answer:d.answer||"",evidence_id:d.evidence?.evidence_id||"",source_ref:d.evidence?.source_ref||"",knowledge_entry_id:d.knowledge_entry_id||"",knowledge_revision_id:d.knowledge_revision_id||"",effective_from:d.effective_from,effective_until:d.effective_until||null};s.verified=item.status==="verified"&&Boolean(item.verification?.passed);s.published=published;s.dirty=false;}}}catch(e){error.value=e?.response?.data?.detail||e.message;}finally{loading.value=false;}}
async function saveDraft(item){const s=stateFor(item);const payload=buildGuideLoopDraftPayload(s.form);const snapshot=JSON.stringify(payload);s.busy=true;try{const r=await createGuideLoopDraft(item.cluster_id,payload);s.draftId=r.draft_id;s.verified=false;s.sourceReviewed=false;s.reviewedDraftId="";s.published=false;s.dirty=JSON.stringify(buildGuideLoopDraftPayload(s.form))!==snapshot;ElMessage.success(s.dirty?"已保存请求时的草稿；当前表单有未保存修改":"草稿已保存");}catch(e){ElMessage.error(e?.response?.data?.detail||e.message);}finally{s.busy=false;}}
async function verify(item){const s=stateFor(item);const verifyingDraftId=s.draftId;s.busy=true;try{const r=await verifyGuideLoopDraft(item.cluster_id,verifyingDraftId);if(s.draftId===verifyingDraftId&&!s.dirty){s.verified=r.passed;s.sourceReviewed=false;s.reviewedDraftId="";}ElMessage[r.passed?"success":"error"](r.passed?"技术路由验证通过；仍需人工核验来源":"技术路由验证未通过");}catch(e){ElMessage.error(e?.response?.data?.detail||e.message);}finally{s.busy=false;}}
async function publish(item){const s=stateFor(item);if(!s.sourceReviewed||s.reviewedDraftId!==s.draftId){ElMessage.warning("请先核验当前草稿的来源与回答支持关系");return;}const publishingDraftId=s.draftId;const publishingBase=s.form.base_revision;s.busy=true;try{const r=await publishGuideLoopDraft(item.cluster_id,publishingDraftId,publishingBase,true);ElMessage.success(`已发布 ${r.revision_id}`);await loadCases();s.form.base_revision=r.revision_id;s.published=true;}catch(e){ElMessage.error(e?.response?.data?.detail||e.message);}finally{s.busy=false;}}
async function replay(item){const s=stateFor(item);s.replaying=true;try{s.liveResult=await replayGuideLoopQuestion({query:s.replayQuery||s.form.alias,poiId:s.form.poi_id});}catch(e){s.liveResult={error:e.message};}finally{s.replaying=false;}}
async function confirm(checkId,passed){try{const r=await confirmGuideLoopLive(checkId,passed);ElMessage.success(`复测状态：${r.status}`);await loadCases();}catch(e){ElMessage.error(e?.response?.data?.detail||e.message);}}
onMounted(()=>{loadCases();loadKnowledge();});
</script>

<style scoped>
.guide-loop-panel{display:grid;gap:16px}.panel-header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.panel-header h2{margin:0}.panel-header p,.case-card p{color:#647067;margin:6px 0}.case-list{display:grid;gap:14px}.case-card{border:1px solid #dce5df;border-radius:12px;padding:16px;background:white}.case-title{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.draft-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 12px;margin-top:14px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.actions :deep(.el-input){flex:1;min-width:180px}.live-result{margin-top:14px;padding:12px;background:#f3f7f4;border-radius:8px;overflow-wrap:anywhere}.live-result small{color:#59645d}@media(max-width:640px){.panel-header{align-items:stretch;flex-direction:column}.draft-form{grid-template-columns:1fr}.actions :deep(.el-button){min-height:42px;width:100%}}
</style>
