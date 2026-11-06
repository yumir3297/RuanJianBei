import { defineStore } from "pinia";
import {
  bootstrapTourSessions, createTourSession, fetchTourSession, fetchTourRevisions, fetchTourSessions,
  fetchTourTrash, purgeTourSession, removeTourSession, restoreTourSession, saveTourSession,
  restoreTourRevision, saveTourSessionV2, upgradeTourSessionV2, fetchTourProgress, startTourProgress,
  sendTourProgressCommand, fetchTourBudget,
} from "../api/tourSessions.js";
import { getOperationKey } from "../utils/tourSessionKeys.js";
import { createRequestGeneration } from "../utils/requestGeneration.js";
import { cloneJson } from "../utils/cloneJson.js";
import { isProposalDraftStale, stableSnapshotStringify } from "../utils/proposalSnapshot.js";
import { refreshProgressAfterItineraryApply, refreshProgressAfterPlanSave } from "../utils/progressRefresh.js";
import { reconcileDraftAfterAsyncApply } from "../utils/proposalApplyState.js";
import { applyItineraryProposal, createItineraryProposal, fetchItineraryProposal } from "../api/itinerary.js";

function newKey() {
  return globalThis.crypto?.randomUUID?.() || `tour-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
function readCurrentId() { try { return globalThis.localStorage?.getItem("a5-current-tour-id") || ""; } catch { return ""; } }
function writeCurrentId(id) { try { id ? globalThis.localStorage?.setItem("a5-current-tour-id", id) : globalThis.localStorage?.removeItem("a5-current-tour-id"); } catch {} }
async function snapshotDigest(value) {
  if (!globalThis.crypto?.subtle) throw new Error("浏览器不支持草稿校验");
  const bytes = new TextEncoder().encode(stableSnapshotStringify(value));
  const hash = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, "0")).join("");
}
const proposalRequests = createRequestGeneration();

function waitForProposalPoll(signal, delayMs = 1000) {
  if (signal.aborted) return Promise.reject(new DOMException("Aborted", "AbortError"));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, delayMs);
    const abort = () => { clearTimeout(timer); signal.removeEventListener("abort", abort); reject(new DOMException("Aborted", "AbortError")); };
    signal.addEventListener("abort", abort, { once: true });
  });
}

export const useTourSessionsStore = defineStore("tourSessions", {
  state: () => ({
    csrfToken: "",
    identityId: "",
    items: [],
    trash: [],
    current: null,
    revisions: [],
    currentId: readCurrentId(),
    draftSnapshot: null,
    progress: null,
    progressSyncRequired: false,
    currentStopRemainingMinutes: null,
    budget: null,
    proposal: null,
    proposalCanonical: "",
    proposalBaseSnapshot: null,
    proposalLoading: false,
    saveState: "idle",
    error: "",
    operationKeys: {},
  }),
  getters: {
    proposalIsStale: state => isProposalDraftStale(state.proposalCanonical, state.draftSnapshot),
  },
  actions: {
    clearProposal() {
      proposalRequests.cancel();
      this.proposalLoading = false;
      this.proposal = null; this.proposalCanonical = ""; this.proposalBaseSnapshot = null;
    },
    async prepare() {
      if (this.csrfToken && this.identityId) return this.csrfToken;
      const first = await bootstrapTourSessions();
      const second = await bootstrapTourSessions();
      if (!first.identity_id || first.identity_id !== second.identity_id) {
        const error = new Error("此浏览器未能保存匿名身份 Cookie，请允许本站使用 Cookie 后重试。");
        error.code = "TOUR_COOKIE_UNAVAILABLE";
        throw error;
      }
      this.identityId = second.identity_id;
      this.csrfToken = second.csrf_token || "";
      return this.csrfToken;
    },
    operationKey(operation, payload) {
      return getOperationKey(this.operationKeys, operation, payload, newKey);
    },
    clearOperationKey(fingerprint) {
      const next = { ...this.operationKeys };
      delete next[fingerprint];
      this.operationKeys = next;
    },
    async loadList() {
      this.error = "";
      try {
        await this.prepare();
        this.items = await fetchTourSessions();
      } catch (error) {
        this.error = error?.code === "TOUR_COOKIE_UNAVAILABLE"
          ? error.message
          : "暂时无法读取已保存的游览，请检查网络后重试。";
      }
    },
    async loadTrash() {
      await this.prepare();
      this.trash = await fetchTourTrash();
    },
    async open(id) {
      this.error = "";
      try {
        await this.prepare();
        this.current = await fetchTourSession(id);
        this.currentId = id; writeCurrentId(id);
        this.clearProposal();
        this.draftSnapshot = cloneJson(this.current.snapshot || {});
        this.revisions = await fetchTourRevisions(id).catch(() => []);
        this.progress = await fetchTourProgress(id).catch(() => null);
        this.progressSyncRequired = !this.progress;
        this.currentStopRemainingMinutes = null;
        this.budget = this.current.snapshot?.schema_version === 2 ? await fetchTourBudget(id).catch(() => null) : null;
        this.saveState = "saved";
        return this.current;
      } catch {
        this.error = "无法打开这条游览，请刷新列表后重试。";
        return null;
      }
    },
    async create(payload) {
      this.error = "";
      this.saveState = "saving";
      this.draftSnapshot = cloneJson(payload.snapshot || {});
      const { fingerprint, key } = this.operationKey("create", payload);
      try {
        await this.prepare();
        this.current = await createTourSession(payload, this.csrfToken, key);
        this.currentId = this.current.id; writeCurrentId(this.current.id);
        this.clearProposal();
        this.progress = null; this.progressSyncRequired = false;
        this.currentStopRemainingMinutes = null; this.budget = null;
        this.draftSnapshot = cloneJson(this.current.snapshot || {});
        this.items = [this.current, ...this.items.filter(item => item.id !== this.current.id)];
        this.revisions = await fetchTourRevisions(this.current.id).catch(() => []);
        this.saveState = "saved";
        this.clearOperationKey(fingerprint);
        return this.current;
      } catch (error) {
        this.saveState = error?.response?.status === 409 ? "conflict" : "error";
        this.error = error?.code === "TOUR_COOKIE_UNAVAILABLE"
          ? error.message
          : error?.response?.status === 409
          ? "该游览发生版本冲突，请刷新列表后重新打开。"
          : "保存失败，当前内容仍保留在页面中，可重试。";
        return null;
      }
    },
    async save(snapshot = this.draftSnapshot) {
      if (!this.current) return null;
      this.error = "";
      this.saveState = "saving";
      this.draftSnapshot = cloneJson(snapshot || {});
      const payload = { expected_version: this.current.version, snapshot: this.draftSnapshot };
      const progressBeforeSave = this.progress;
      const { fingerprint, key } = this.operationKey(`save:${this.current.id}`, payload);
      try {
        await this.prepare();
        this.current = this.draftSnapshot?.schema_version === 2
          ? await saveTourSessionV2(this.current.id, payload, this.csrfToken, key)
          : await saveTourSession(this.current.id, payload, this.csrfToken, key);
        this.draftSnapshot = cloneJson(this.current.snapshot || {});
        this.items = this.items.map(item => item.id === this.current.id ? this.current : item);
        this.revisions = await fetchTourRevisions(this.current.id).catch(() => this.revisions);
        this.saveState = "saved";
        this.progress = await refreshProgressAfterPlanSave(this.current.id, progressBeforeSave, fetchTourProgress);
        this.progressSyncRequired = progressBeforeSave?.status === "active" && !this.progress;
        if (this.progressSyncRequired) this.error = "行程已保存，但游览进度未能同步；刷新后再继续记录进度。";
        this.budget = this.current.snapshot?.schema_version === 2 ? await fetchTourBudget(this.current.id).catch(() => null) : null;
        this.clearOperationKey(fingerprint);
        return this.current;
      } catch (error) {
        this.saveState = error?.response?.status === 409 ? "conflict" : "error";
        this.error = error?.code === "TOUR_COOKIE_UNAVAILABLE"
          ? error.message
          : error?.response?.status === 409
          ? "这条游览已在其他标签页更新。你的当前内容已保留，请重新打开后再继续。"
          : "保存失败，当前内容仍保留在页面中，可重试。";
        return null;
      }
    },
    async upgradeV2() {
      if (!this.current) return null;
      try {
        await this.prepare();
        const payload = { expected_version: this.current.version };
        const { fingerprint, key } = this.operationKey(`upgrade:${this.current.id}`, payload);
        this.current = await upgradeTourSessionV2(this.current.id, this.current.version, this.csrfToken, key);
        this.draftSnapshot = cloneJson(this.current.snapshot);
        this.items = this.items.map(item => item.id === this.current.id ? this.current : item);
        this.revisions = await fetchTourRevisions(this.current.id).catch(() => this.revisions);
        this.saveState = "saved"; this.clearOperationKey(fingerprint);
        this.progress = await fetchTourProgress(this.current.id).catch(() => null);
        this.progressSyncRequired = !this.progress;
        this.currentStopRemainingMinutes = null;
        this.budget = await fetchTourBudget(this.current.id).catch(() => null);
        return this.current;
      } catch (error) { this.error = error?.response?.data?.detail || "行程升级失败，请刷新后重试。"; return null; }
    },
    async start() {
      if (!this.current || this.current.snapshot?.schema_version !== 2) return null;
      if (stableSnapshotStringify(this.draftSnapshot) !== stableSnapshotStringify(this.current.snapshot)) {
        this.error = "请先保存当前行程修改，再开始游览。";
        return null;
      }
      try {
        await this.prepare();
        const payload = { expected_version: this.current.version };
        const { fingerprint, key } = this.operationKey(`start:${this.current.id}`, payload);
        this.progress = await startTourProgress(this.current.id, this.current.version, this.csrfToken, key);
        this.progressSyncRequired = false;
        this.currentStopRemainingMinutes = null;
        this.clearOperationKey(fingerprint); this.budget = await fetchTourBudget(this.current.id).catch(() => null);
        return this.progress;
      } catch (error) { this.error = error?.response?.data?.detail || "无法开始游览，请刷新后检查行程。"; return null; }
    },
    async applyProgress(command) {
      if (!this.current || !this.progress) return null;
      try {
        await this.prepare();
        const previousCurrentStopId = this.progress.current_stop_id;
        const payload = { expected_progress_version: this.progress.progress_version, command };
        const { fingerprint, key } = this.operationKey(`progress:${this.current.id}`, payload);
        this.progress = await sendTourProgressCommand(this.current.id, this.progress.progress_version, command, this.csrfToken, key);
        this.progressSyncRequired = false;
        if (this.progress.current_stop_id !== previousCurrentStopId) this.currentStopRemainingMinutes = null;
        this.clearOperationKey(fingerprint); this.budget = await fetchTourBudget(
          this.current.id, this.currentStopRemainingMinutes,
        ).catch(() => null);
        return this.progress;
      } catch (error) { this.error = error?.response?.data?.detail || "进度已更新，请刷新后继续。"; return null; }
    },
    async setCurrentStopRemainingMinutes(value) {
      if (!this.current || !this.progress?.current_stop_id) return null;
      const minutes = value === "" || value == null ? null : Number(value);
      if (minutes != null && (!Number.isInteger(minutes) || minutes < 0 || minutes > 720)) {
        this.error = "当前点剩余时间需为 0 到 720 分钟。";
        return null;
      }
      this.currentStopRemainingMinutes = minutes;
      this.error = "";
      this.budget = await fetchTourBudget(this.current.id, minutes).catch(error => {
        this.error = error?.response?.data?.detail || "无法更新剩余预算，请检查网络后重试。";
        return null;
      });
      return this.budget;
    },
    async requestProposal(text) {
      if (!this.current || this.draftSnapshot?.schema_version !== 2) { this.error = "请先在路线页升级并打开 V2 游览。"; return null; }
      const request = proposalRequests.begin();
      this.proposalLoading = true; this.error = "";
      const draft = cloneJson(this.draftSnapshot); const canonical = stableSnapshotStringify(draft);
      try {
        const digest = await snapshotDigest(draft); await this.prepare();
        if (!proposalRequests.isCurrent(request)) return null;
        const payload = { expected_version: this.current.version, progress_version: this.progress?.progress_version || 0,
          draft_digest: digest, draft_snapshot: draft, text };
        const { fingerprint, key } = this.operationKey(`proposal:${this.current.id}`, payload);
        let proposal = await createItineraryProposal(this.current.id, payload, this.csrfToken, key, request.signal);
        for (let attempt = 0; proposal.status === "executing" && attempt < 30; attempt += 1) {
          await waitForProposalPoll(request.signal);
          proposal = await fetchItineraryProposal(this.current.id, proposal.id, request.signal);
        }
        if (!proposalRequests.isCurrent(request)) return null;
        if (proposal.status === "executing") throw new Error("提案仍在处理中，可稍后重试查看结果。");
        if (proposal.status === "failed") {
          this.clearOperationKey(fingerprint);
          throw new Error(proposal.validation?.message || "提案未能完成，请重试。");
        }
        if (stableSnapshotStringify(this.draftSnapshot) !== canonical) { this.error = "生成期间草稿已修改，请重新提出需求；手动修改已保留。"; return null; }
        this.proposal = proposal; this.proposalCanonical = canonical; this.proposalBaseSnapshot = draft;
        this.clearOperationKey(fingerprint); return proposal;
      } catch (error) {
        if (proposalRequests.isCurrent(request) && error?.name !== "AbortError" && !request.signal.aborted) {
          this.error = error?.response?.data?.detail || error?.message || "无法生成提案，当前草稿未改变。";
        }
        return null;
      } finally {
        if (proposalRequests.finish(request)) {
          this.proposalLoading = false;
        }
      }
    },
    async confirmProposal() {
      const proposal = this.proposal;
      if (!proposal || !this.current) return null;
      if (isProposalDraftStale(this.proposalCanonical, this.draftSnapshot)) { this.error = "草稿已变化，请重新生成提案。"; return null; }
      const submittedDraft = cloneJson(this.draftSnapshot);
      const sessionId = this.current.id;
      try {
        await this.prepare();
        if (this.current?.id !== sessionId || this.proposal?.id !== proposal.id
          || isProposalDraftStale(this.proposalCanonical, this.draftSnapshot)) {
          this.error = "确认期间游览或草稿已变化，请重新检查提案。";
          return null;
        }
        const previousCurrentStopId = this.progress?.current_stop_id;
        const payload = { expected_version: this.current.version, progress_version: this.progress?.progress_version || 0, draft_digest: proposal.draft_digest };
        const { fingerprint, key } = this.operationKey(`proposal-apply:${proposal.id}`, payload);
        const applied = await applyItineraryProposal(sessionId, proposal.id, payload, this.csrfToken, key);
        if (this.current?.id !== sessionId) return null;
        this.current = applied;
        const reconciledDraft = reconcileDraftAfterAsyncApply(submittedDraft, this.draftSnapshot, this.current.snapshot);
        this.draftSnapshot = reconciledDraft.draftSnapshot;
        this.items = this.items.map(item => item.id === this.current.id ? this.current : item);
        this.progress = await refreshProgressAfterItineraryApply(this.current.id, fetchTourProgress);
        this.progressSyncRequired = !this.progress;
        if (!this.progress) this.error = "行程已保存，但游览进度未能同步；刷新后再继续记录进度。";
        if (this.progress?.current_stop_id !== previousCurrentStopId) this.currentStopRemainingMinutes = null;
        this.revisions = await fetchTourRevisions(this.current.id).catch(() => this.revisions);
        this.proposal = null; this.proposalCanonical = ""; this.proposalBaseSnapshot = null; this.clearOperationKey(fingerprint);
        if (reconciledDraft.hasConcurrentEdits) {
          this.saveState = "idle";
          this.error = "提案已应用；确认期间的手动修改已保留为未保存草稿，请核对后再保存。";
        }
        this.budget = await fetchTourBudget(this.current.id, this.currentStopRemainingMinutes).catch(() => null); return this.current;
      } catch (error) { this.error = error?.response?.data?.detail || "提案已失效，请刷新后重新生成。"; return null; }
    },
    cancelProposal() {
      this.clearProposal();
      this.error = "";
    },
    async restoreRevision(revision) {
      if (!this.current || !revision?.id) return null;
      try {
        await this.prepare();
        const payload = { revision_id: revision.id, expected_version: this.current.version };
        const { fingerprint, key } = this.operationKey(`restore-revision:${this.current.id}`, payload);
        this.current = await restoreTourRevision(this.current.id, revision.id, this.current.version, this.csrfToken, key);
        this.draftSnapshot = cloneJson(this.current.snapshot);
        this.items = this.items.map(item => item.id === this.current.id ? this.current : item);
        this.progress = await fetchTourProgress(this.current.id).catch(() => this.progress);
        this.progressSyncRequired = !this.progress;
        if (!this.progress?.current_stop_id) this.currentStopRemainingMinutes = null;
        this.budget = this.current.snapshot?.schema_version === 2
          ? await fetchTourBudget(this.current.id, this.currentStopRemainingMinutes).catch(() => null) : null;
        this.revisions = await fetchTourRevisions(this.current.id).catch(() => this.revisions);
        this.clearOperationKey(fingerprint);
        return this.current;
      } catch (error) {
        this.error = error?.response?.data?.detail || "无法恢复此版本；若有已完成游览记录，服务端会阻止覆盖。";
        return null;
      }
    },
    async remove(id) {
      const item = this.items.find(entry => entry.id === id) || this.current;
      if (!item) return false;
      await this.prepare();
      await removeTourSession(id, item.version, this.csrfToken);
      this.items = this.items.filter(entry => entry.id !== id);
      if (this.current?.id === id) { this.current = null; this.currentId = ""; writeCurrentId(""); }
      await this.loadTrash();
      return true;
    },
    async restoreDeleted(id) {
      await this.prepare();
      this.current = await restoreTourSession(id, this.csrfToken);
      this.currentId = id; writeCurrentId(id);
      this.clearProposal();
      this.items = [this.current, ...this.items.filter(item => item.id !== id)];
      this.revisions = await fetchTourRevisions(id).catch(() => []);
      this.draftSnapshot = cloneJson(this.current.snapshot || {});
      this.progress = await fetchTourProgress(id).catch(() => null);
      this.progressSyncRequired = !this.progress;
      this.currentStopRemainingMinutes = null;
      this.budget = this.current.snapshot?.schema_version === 2 ? await fetchTourBudget(id).catch(() => null) : null;
      await this.loadTrash();
      return this.current;
    },
    async purge(id) {
      await this.prepare();
      await purgeTourSession(id, this.csrfToken);
      this.trash = this.trash.filter(item => item.id !== id);
    },
    clearCurrent() {
      this.current = null;
      this.revisions = [];
      this.currentId = ""; writeCurrentId("");
      this.draftSnapshot = null;
      this.progress = null; this.budget = null;
      this.progressSyncRequired = false;
      this.currentStopRemainingMinutes = null;
      this.clearProposal();
      this.saveState = "idle";
      this.error = "";
    },
  },
});
