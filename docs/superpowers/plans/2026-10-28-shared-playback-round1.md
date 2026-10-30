# Shared Playback Round 1 Implementation Plan

> **For agentic workers:** Execute this plan inline with `superpowers:executing-plans`. Use TDD for each behavior change. Preserve all existing worktree changes.

**Goal:** Make chat playback and map narration mutually exclusive, safely stoppable by their owner, and inactive when the KeepAlive map tool is hidden.

**Architecture:** Keep the existing singleton `useAudioPlayer`. Add explicit playback-session ownership and scoped stop/preemption notifications; carry session identity through queued audio and PCM entry points. Bind chat and map narration to sessions. Treat KeepAlive deactivation as a real lifecycle boundary for map timers, geolocation, pending requests and narration.

**Tech Stack:** Vue 3 composables, Pinia, Node test runner, Vite SSR test harness.

**Scope:** F01 playback isolation + the ownership/stop portion of V03 + the KeepAlive/mobile lifecycle portion of C01. Speech-rate preferences, historical chat replay, true-device/browser testing, and performance benchmarks remain separate work.

## Repository and safety context

- Repository map: `docs/REPO_MAP.md`; compatibility matrix: `docs/COMPATIBILITY.md`.
- Work occurs in the task's project mirror on `codex/repository-map`, based on `672a104`, with prior uncommitted F01 work. Keep those changes and all existing user edits.
- K01 is developed in a separate checkout; do not edit it or push/commit.
- The shared player is a module singleton. Chat and MapView currently use unscoped global stop. MapView is rendered under `<KeepAlive>`; its timer and geolocation currently stop only on unmount, not deactivation.

## Tasks

1. **Playback session contract**
   - Add Node tests for a chat session being preempted by map narration, stale sessions being unable to enqueue after replacement, and a stale scoped stop not stopping the newer owner.
   - Run the tests and observe the intended failures before changing production code.
   - Add session acquisition, current-session checks, scoped stop and preemption callbacks to `useAudioPlayer.js`; session-bound enqueue/PCM start must reject stale callers.
   - Run the new and existing audio-player tests.

2. **Bind chat and map narration**
   - Add tests for chat session ownership and map narration cancellation/state reset where the current test harness permits.
   - Bind Chat store queued audio and PCM playback to its session; stop only that session for request errors and retain an explicit global stop for the visitor's global stop control.
   - Bind map narration fetch, replay and stop to a map-owned session. A chat takeover must clear map loading/progress state; a map takeover must trigger ChatView's existing playback-stop cleanup.
   - Regression test: cancelling an obsolete map request cannot stop a later chat session.

3. **KeepAlive and page lifecycle**
   - Add a focused lifecycle test for inactive map work if it can exercise the extracted behavior without a DOM; otherwise document the manual checks and keep lifecycle helpers small.
   - On map deactivation, cancel in-flight narration, stop its own playback, pause location/walk mode, clear the periodic timer and drop stale pending narration. On activation, restore only the map view and layout; do not resume audio or GPS without a user action.
   - On unmount, perform idempotent cleanup.

4. **Compatibility and verification**
   - Run the full frontend test suite and production build, plus `python3 scripts/check_repo_map.py`.
   - Record desktop browser/manual checks and explicitly leave iOS Safari, WeChat, Android and real weak-network checks pending unless actually run on devices.
   - Update `docs/COMPATIBILITY.md`, `docs/REPO_MAP.md`, the F01/V03/C01 checklist and the validation record with only verified scope.

## Completion evidence

- Tests prove preemption, scoped stop, stale-session rejection, cancellation and KeepAlive deactivation behavior.
- Existing chat, audio, SSE and map tests remain green; production build succeeds.
- The backlog marks only ownership/stop and lifecycle sub-items complete. Speech rate, replay of historic chat answers, true-device validation and performance baselines stay open.
