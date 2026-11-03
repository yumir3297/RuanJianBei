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
import { applyItineraryProposal, createItineraryProposal, fetchItineraryProposal, fetchItineraryProposals, retryItineraryProposal } from "../api/itinerary.js";

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
const openRequests = createRequestGeneration();
const currentStopBudgetRequests = createRequestGeneration();

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
    proposalApplying: false,
    proposalChoices: [],
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
      this.proposalApplying = false;
      this.proposal = null; this.proposalCanonical = ""; this.proposalBaseSnapshot = null;
      this.proposalChoices = [];
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
      const request = openRequests.begin();
      this.clearProposal();
      this.error = "";
      try {
        await this.prepare();
        const current = await fetchTourSession(id);
        if (!openRequests.isCurrent(request)) return null;
        const [revisions, progress, budget] = await Promise.all([
          fetchTourRevisions(id).catch(() => []),
          fetchTourProgress(id).catch(() => null),
          current.snapshot?.schema_version === 2 ? fetchTourBudget(id).catch(() => null) : null,
        ]);
        if (!openRequests.isCurrent(request)) return null;
        this.clearProposal();
        this.current = current;
        this.currentId = id; writeCurrentId(id);
        this.draftSnapshot = cloneJson(current.snapshot || {});
        this.revisions = revisions; this.progress = progress;
        this.progressSyncRequired = !progress;
        this.currentStopRemainingMinutes = null; this.budget = budget;
        this.saveState = "saved";
        // Restore independently: opening a tour must not wait for a worker.
        void this.restoreProposal(id);
        return current;
      } catch {
        if (openRequests.isCurrent(request)) this.error = "无法打开这条游览，请刷新列表后重试。";
        return null;
      } finally { openRequests.finish(request); }
    },
    async restoreProposal(sessionId = this.current?.id) {
      if (this.proposalApplying) return null;
      if (this.current?.id !== sessionId || this.current.snapshot?.schema_version !== 2) return null;
      const request = proposalRequests.begin();
      this.proposalLoading = true;
      try {
        const items = await fetchItineraryProposals(sessionId, 10, request.signal);
        if (!proposalRequests.isCurrent(request) || this.current?.id !== sessionId) return null;
        if (items.length > 1 && items[0].created_at && items[0].created_at === items[1].created_at) {
          this.clearProposal();
          this.proposalChoices = items.filter(item => item.created_at === items[0].created_at);
          this.error = "多个提案创建时间相同，无法确定最新结果。请选择要查看的提案；避免重复调用 AI 产生费用。";
          return null;
        }
        // The API returns newest first. Never resurrect an older proposal
        // merely because the latest one has reached a terminal state.
        const latest = items[0];
        const resumable = latest && ["executing", "waiting_user", "ready", "needs_clarification", "failed"].includes(latest.status) ? latest : null;
        if (!resumable) { this.clearProposal(); return null; }
        const detail = await fetchItineraryProposal(sessionId, resumable.id, request.signal);
        if (!proposalRequests.isCurrent(request) || this.current?.id !== sessionId) return null;
        return await this.resumeProposal(detail);
      } catch (error) {
        if (proposalRequests.isCurrent(request) && !request.signal.aborted) this.error = "游览已打开，但提案状态暂时无法恢复；可重新检查后台提案。";
        return null;
      } finally { if (proposalRequests.finish(request)) this.proposalLoading = false; }
    },
    async selectProposalChoice(proposalId) {
      if (this.proposalApplying) return null;
      const sessionId = this.current?.id;
      if (!sessionId || !this.proposalChoices.some(item => item.id === proposalId && item.session_id === sessionId)) return null;
      const request = proposalRequests.begin();
      this.proposalLoading = true;
      try {
        const detail = await fetchItineraryProposal(sessionId, proposalId, request.signal);
        if (!proposalRequests.isCurrent(request) || this.current?.id !== sessionId || detail.id !== proposalId || detail.session_id !== sessionId) return null;
        this.proposalChoices = [];
        return await this.resumeProposal(detail);
      } catch {
        if (proposalRequests.isCurrent(request) && !request.signal.aborted) this.error = "无法读取提案，请检查网络后重试。";
        return null;
      } finally { if (proposalRequests.finish(request)) this.proposalLoading = false; }
    },
    async create(payload) {
      openRequests.cancel(); this.clearProposal();
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
      if (!this.current || this.saveState === "saving") return null;
      this.error = "";
      this.saveState = "saving";
      this.draftSnapshot = cloneJson(snapshot || {});
      const original = this.current;
      const sessionId = original.id;
      const submittedDraft = cloneJson(this.draftSnapshot);
      const payload = { expected_version: original.version, snapshot: submittedDraft };
      const progressBeforeSave = this.progress;
      const { fingerprint, key } = this.operationKey(`save:${sessionId}`, payload);
      let expectedCurrent = original;
      const isCurrent = () => this.current === expectedCurrent;
      try {
        await this.prepare();
        if (!isCurrent()) return null;
        const saved = submittedDraft?.schema_version === 2
          ? await saveTourSessionV2(sessionId, payload, this.csrfToken, key)
          : await saveTourSession(sessionId, payload, this.csrfToken, key);
        this.clearOperationKey(fingerprint);
        if (!isCurrent()) return null;
        this.current = saved;
        expectedCurrent = this.current;
        const reconciled = reconcileDraftAfterAsyncApply(submittedDraft, this.draftSnapshot, saved.snapshot || {});
        this.draftSnapshot = reconciled.draftSnapshot;
        this.items = this.items.map(item => item.id === sessionId ? saved : item);
        const revisions = await fetchTourRevisions(sessionId).catch(() => null);
        if (!isCurrent()) return null;
        if (revisions) this.revisions = revisions;
        this.saveState = reconciled.hasConcurrentEdits ? "idle" : "saved";
        if (reconciled.hasConcurrentEdits) this.error = "行程已保存；保存期间的修改已保留为未保存草稿，请核对后再保存。";
        const progress = await refreshProgressAfterPlanSave(sessionId, progressBeforeSave, fetchTourProgress);
        if (!isCurrent()) return null;
        this.progress = progress;
        this.progressSyncRequired = progressBeforeSave?.status === "active" && !this.progress;
        if (this.progressSyncRequired) this.error = "行程已保存，但游览进度未能同步；刷新后再继续记录进度。";
        const budget = saved.snapshot?.schema_version === 2 ? await fetchTourBudget(sessionId).catch(() => null) : null;
        if (!isCurrent()) return null;
        this.budget = budget;
        return this.current;
      } catch (error) {
        if (!isCurrent()) return null;
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
      const current = this.current;
      const originalProgress = this.progress;
      try {
        await this.prepare();
        if (this.current !== current || this.progress !== originalProgress) return null;
        const payload = { expected_version: current.version };
        const { fingerprint, key } = this.operationKey(`start:${current.id}`, payload);
        const result = await startTourProgress(current.id, current.version, this.csrfToken, key);
        this.clearOperationKey(fingerprint);
        if (this.current !== current || this.progress !== originalProgress) return null;
        this.progress = result;
        this.progressSyncRequired = false;
        this.currentStopRemainingMinutes = null;
        const startedProgress = this.progress;
        const budget = await fetchTourBudget(current.id).catch(() => null);
        if (this.current !== current || this.progress !== startedProgress || this.currentStopRemainingMinutes !== null) return null;
        this.budget = budget;
        return startedProgress;
      } catch (error) {
        if (this.current === current && this.progress === originalProgress)
          this.error = error?.response?.data?.detail || "无法开始游览，请刷新后检查行程。";
        return null;
      }
    },
    async applyProgress(command) {
      if (!this.current || !this.progress) return null;
      const current = this.current;
      const originalProgress = this.progress;
      try {
        await this.prepare();
        if (this.current !== current || this.progress !== originalProgress) return null;
        const previousCurrentStopId = originalProgress.current_stop_id;
        const payload = { expected_progress_version: originalProgress.progress_version, command };
        const { fingerprint, key } = this.operationKey(`progress:${current.id}`, payload);
        const updated = await sendTourProgressCommand(current.id, originalProgress.progress_version, command, this.csrfToken, key);
        this.clearOperationKey(fingerprint);
        if (this.current !== current || this.progress !== originalProgress) return null;
        this.progress = updated;
        this.progressSyncRequired = false;
        if (this.progress.current_stop_id !== previousCurrentStopId) this.currentStopRemainingMinutes = null;
        const appliedProgress = this.progress;
        const remaining = this.currentStopRemainingMinutes;
        const budget = await fetchTourBudget(current.id, remaining).catch(() => null);
        if (this.current !== current || this.progress !== appliedProgress || this.currentStopRemainingMinutes !== remaining) return null;
        this.budget = budget;
        return appliedProgress;
      } catch (error) {
        if (this.current === current && this.progress === originalProgress)
          this.error = error?.response?.data?.detail || "进度已更新，请刷新后继续。";
        return null;
      }
    },
    async setCurrentStopRemainingMinutes(value) {
      if (!this.current || !this.progress?.current_stop_id) return null;
      currentStopBudgetRequests.cancel();
      const minutes = value === "" || value == null ? null : Number(value);
      if (minutes != null && (!Number.isInteger(minutes) || minutes < 0 || minutes > 720)) {
        this.error = "当前点剩余时间需为 0 到 720 分钟。";
        return null;
      }
      this.currentStopRemainingMinutes = minutes;
      this.error = "";
      const current = this.current, progress = this.progress;
      const request = currentStopBudgetRequests.begin();
      try {
        const budget = await fetchTourBudget(current.id, minutes);
        if (!currentStopBudgetRequests.isCurrent(request) || this.current !== current || this.progress !== progress) return null;
        this.budget = budget;
        return budget;
      } catch (error) {
        if (currentStopBudgetRequests.isCurrent(request) && this.current === current && this.progress === progress)
          this.error = error?.response?.data?.detail || "无法更新剩余预算，请检查网络后重试。";
        return null;
      } finally { currentStopBudgetRequests.finish(request); }
    },
    async requestProposal(text) {
      if (this.proposalApplying) return null;
      if (!this.current || this.draftSnapshot?.schema_version !== 2) { this.error = "请先在路线页升级并打开 V2 游览。"; return null; }
      const sessionId = this.current.id;
      const expectedVersion = this.current.version;
      const progressVersion = this.progress?.progress_version || 0;
      const request = proposalRequests.begin();
      this.proposalLoading = true; this.error = "";
      const draft = cloneJson(this.draftSnapshot);
      try {
        const digest = await snapshotDigest(draft); await this.prepare();
        if (!proposalRequests.isCurrent(request) || this.current?.id !== sessionId) return null;
        const payload = { expected_version: expectedVersion, progress_version: progressVersion,
          draft_digest: digest, draft_snapshot: draft, text };
        const { fingerprint, key } = this.operationKey(`proposal:${sessionId}`, payload);
        const proposal = await createItineraryProposal(sessionId, payload, this.csrfToken, key, request.signal);
        if (!proposalRequests.isCurrent(request) || this.current?.id !== sessionId) return null;
        this.clearOperationKey(fingerprint);
        return await this.resumeProposal(proposal, draft);
      } catch (error) {
        if (proposalRequests.isCurrent(request) && error?.name !== "AbortError" && !request.signal.aborted) {
          this.error = error?.response?.data?.detail || error?.message || "无法生成提案，当前草稿未改变。";
        }
        return null;
      } finally { if (proposalRequests.finish(request)) this.proposalLoading = false; }
    },
    async resumeProposal(proposal, fallbackBase = this.draftSnapshot) {
      if (this.proposalApplying) return null;
      const sessionId = this.current?.id;
      if (!proposal?.id || !sessionId || proposal.session_id !== sessionId) return null;
      const request = proposalRequests.begin();
      const isCurrent = () => proposalRequests.isCurrent(request) && this.current?.id === sessionId;
      this.proposal = proposal;
      // Recover provenance without overwriting edits made while the worker ran.
      this.proposalBaseSnapshot = cloneJson(proposal.base_snapshot || fallbackBase);
      this.proposalCanonical = stableSnapshotStringify(this.proposalBaseSnapshot);
      this.proposalLoading = proposal.status === "executing";
      this.error = "";
      try {
        let latest = proposal;
        for (let attempt = 0; latest.status === "executing" && attempt < 60; attempt += 1) {
          await waitForProposalPoll(request.signal);
          if (!isCurrent()) return null;
          latest = await fetchItineraryProposal(sessionId, proposal.id, request.signal);
          if (!isCurrent() || latest.session_id !== sessionId) return null;
          this.proposal = latest;
        }
        if (!isCurrent()) return null;
        if (latest.status === "executing") this.error = "提案仍在后台处理中，可稍后重新检查状态。";
        if (latest.status === "failed") this.error = latest.validation?.message || "提案未能完成，请重新生成。";
        return latest;
      } catch (error) {
        if (isCurrent() && !request.signal.aborted) this.error = "暂时无法恢复提案状态，请检查网络后重新检查。";
        return null;
      } finally { if (proposalRequests.finish(request)) this.proposalLoading = false; }
    },
    async retryProposal(confirmDuplicateRisk = false) {
      if (this.proposalApplying) return null;
      const proposal = this.proposal;
      const sessionId = this.current?.id;
      if (confirmDuplicateRisk !== true) { this.error = "请先确认可能重复调用 AI 并产生费用的风险。"; return null; }
      if (!proposal?.execution_job_id || proposal.status !== "waiting_user" || !sessionId || proposal.session_id !== sessionId || this.proposalLoading) return null;
      const request = proposalRequests.begin();
      const isCurrent = () => proposalRequests.isCurrent(request) && this.current?.id === sessionId && this.proposal?.id === proposal.id;
      this.proposalLoading = true; this.error = "";
      try {
        await this.prepare();
        if (!isCurrent()) return null;
        const payload = { job_id: proposal.execution_job_id, confirm_duplicate_risk: true };
        const { fingerprint, key } = this.operationKey(`proposal-retry:${proposal.execution_job_id}`, payload);
        await retryItineraryProposal(sessionId, proposal.execution_job_id, this.csrfToken, key, true, request.signal);
        if (!isCurrent()) return null;
        this.clearOperationKey(fingerprint);
        return await this.resumeProposal({ ...proposal, status: "executing" }, this.proposalBaseSnapshot);
      } catch (error) {
        if (isCurrent() && !request.signal.aborted) this.error = error?.response?.data?.detail || "暂时无法重试提案，请刷新状态后重试。";
        return null;
      } finally { if (proposalRequests.finish(request)) this.proposalLoading = false; }
    },
    async confirmProposal() {
      const proposal = this.proposal;
      if (this.proposalApplying || !proposal || proposal.status !== "ready" || !this.current || proposal.session_id !== this.current.id) return null;
      if (isProposalDraftStale(this.proposalCanonical, this.draftSnapshot)) { this.error = "草稿已变化，请重新生成提案。"; return null; }
      const submittedDraft = cloneJson(this.draftSnapshot);
      const sessionId = this.current.id;
      const request = proposalRequests.begin();
      const isCurrent = () => proposalRequests.isCurrent(request) && this.current?.id === sessionId;
      this.proposalApplying = true;
      try {
        await this.prepare();
        if (!isCurrent()) return null;
        if (this.proposal?.id !== proposal.id
          || isProposalDraftStale(this.proposalCanonical, this.draftSnapshot)) {
          this.error = "确认期间游览或草稿已变化，请重新检查提案。";
          return null;
        }
        const previousCurrentStopId = this.progress?.current_stop_id;
        const payload = { expected_version: this.current.version, progress_version: this.progress?.progress_version || 0, draft_digest: proposal.draft_digest };
        const { fingerprint, key } = this.operationKey(`proposal-apply:${proposal.id}`, payload);
        const applied = await applyItineraryProposal(sessionId, proposal.id, payload, this.csrfToken, key);
        if (!isCurrent() || this.proposal?.id !== proposal.id) return null;
        this.clearOperationKey(fingerprint);
        this.current = applied;
        const reconciledDraft = reconcileDraftAfterAsyncApply(submittedDraft, this.draftSnapshot, this.current.snapshot);
        this.draftSnapshot = reconciledDraft.draftSnapshot;
        this.items = this.items.map(item => item.id === this.current.id ? this.current : item);
        const progress = await refreshProgressAfterItineraryApply(sessionId, fetchTourProgress);
        if (!isCurrent() || this.proposal?.id !== proposal.id) return null;
        this.progress = progress;
        this.progressSyncRequired = !this.progress;
        if (!this.progress) this.error = "行程已保存，但游览进度未能同步；刷新后再继续记录进度。";
        if (this.progress?.current_stop_id !== previousCurrentStopId) this.currentStopRemainingMinutes = null;
        const revisions = await fetchTourRevisions(sessionId).catch(() => null);
        if (!isCurrent() || this.proposal?.id !== proposal.id) return null;
        if (revisions) this.revisions = revisions;
        this.proposal = null; this.proposalCanonical = ""; this.proposalBaseSnapshot = null;
        if (reconciledDraft.hasConcurrentEdits) {
          this.saveState = "idle";
          this.error = "提案已应用；确认期间的手动修改已保留为未保存草稿，请核对后再保存。";
        }
        const budget = await fetchTourBudget(sessionId, this.currentStopRemainingMinutes).catch(() => null);
        if (!isCurrent()) return null;
        this.budget = budget; return this.current;
      } catch (error) {
        if (isCurrent()) this.error = error?.response?.data?.detail || "提案已失效，请刷新后重新生成。";
        return null;
      } finally { if (proposalRequests.finish(request)) this.proposalApplying = false; }
    },
    cancelProposal() {
      this.clearProposal();
      this.error = "";
    },
    async restoreRevision(revision) {
      if (!this.current || !revision?.id) return null;
      const sessionId = this.current.id;
      const request = openRequests.begin();
      const isCurrent = () => openRequests.isCurrent(request) && this.current?.id === sessionId;
      try {
        await this.prepare();
        if (!isCurrent()) return null;
        const payload = { revision_id: revision.id, expected_version: this.current.version };
        const { fingerprint, key } = this.operationKey(`restore-revision:${sessionId}`, payload);
        const restored = await restoreTourRevision(sessionId, revision.id, this.current.version, this.csrfToken, key);
        if (!isCurrent()) return null;
        this.current = restored;
        this.draftSnapshot = cloneJson(this.current.snapshot);
        this.items = this.items.map(item => item.id === this.current.id ? this.current : item);
        const progress = await fetchTourProgress(sessionId).catch(() => null);
        if (!isCurrent()) return null;
        this.progress = progress;
        this.progressSyncRequired = !this.progress;
        if (!this.progress?.current_stop_id) this.currentStopRemainingMinutes = null;
        const budget = this.current.snapshot?.schema_version === 2
          ? await fetchTourBudget(sessionId, this.currentStopRemainingMinutes).catch(() => null) : null;
        if (!isCurrent()) return null;
        this.budget = budget;
        const revisions = await fetchTourRevisions(sessionId).catch(() => null);
        if (!isCurrent()) return null;
        if (revisions) this.revisions = revisions;
        this.clearOperationKey(fingerprint);
        return this.current;
      } catch (error) {
        if (isCurrent()) this.error = error?.response?.data?.detail || "无法恢复此版本；若有已完成游览记录，服务端会阻止覆盖。";
        return null;
      } finally { openRequests.finish(request); }
    },
    async remove(id) {
      const item = this.items.find(entry => entry.id === id) || this.current;
      if (!item) return false;
      await this.prepare();
      await removeTourSession(id, item.version, this.csrfToken);
      this.items = this.items.filter(entry => entry.id !== id);
      if (this.current?.id === id) { openRequests.cancel(); this.clearProposal(); this.current = null; this.currentId = ""; writeCurrentId(""); }
      await this.loadTrash();
      return true;
    },
    async restoreDeleted(id) {
      const request = openRequests.begin();
      const previousId = this.current?.id;
      const isCurrent = () => openRequests.isCurrent(request) && this.current?.id === previousId;
      this.clearProposal();
      try {
        await this.prepare();
        if (!isCurrent()) return null;
        const restored = await restoreTourSession(id, this.csrfToken);
        if (!isCurrent()) return null;
        const [revisions, progress, budget] = await Promise.all([
          fetchTourRevisions(id).catch(() => []),
          fetchTourProgress(id).catch(() => null),
          restored.snapshot?.schema_version === 2 ? fetchTourBudget(id).catch(() => null) : null,
        ]);
        if (!isCurrent()) return null;
        this.current = restored;
        this.currentId = id; writeCurrentId(id);
        this.items = [restored, ...this.items.filter(item => item.id !== id)];
        this.revisions = revisions;
        this.draftSnapshot = cloneJson(restored.snapshot || {});
        this.progress = progress;
        this.progressSyncRequired = !progress;
        this.currentStopRemainingMinutes = null;
        this.budget = budget;
        try {
          const trash = await fetchTourTrash();
          if (openRequests.isCurrent(request) && this.current?.id === id) this.trash = trash;
        } catch {
          if (openRequests.isCurrent(request) && this.current?.id === id) this.error = "游览已恢复，但回收站列表暂时无法刷新。";
        }
        return openRequests.isCurrent(request) ? restored : null;
      } catch (error) {
        if (!isCurrent()) return null;
        throw error;
      } finally { openRequests.finish(request); }
    },
    async purge(id) {
      await this.prepare();
      await purgeTourSession(id, this.csrfToken);
      this.trash = this.trash.filter(item => item.id !== id);
    },
    clearCurrent() {
      this.current = null;
      openRequests.cancel();
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
