# Tourist Speech Rate Preference Implementation Plan

> **For agentic workers:** Execute inline with `superpowers:executing-plans`. Use TDD for each behavior change and preserve all existing worktree changes.

**Goal:** Give visitors one persistent speech-rate preference shared by chat audio, PCM streaming, map narration, and the welcome audio.

**Architecture:** Store a constrained rate locally in a small preference utility. Pass it from ChatView to the shared audio player and MapView. Apply it at the browser playback layer to AudioBuffer, PCM buffer sources, and browser speech synthesis. Keep progress callbacks in source-content time so existing word and viseme timelines remain aligned.

**Tech Stack:** Vue 3, Vue reactivity, localStorage, Web Audio, Node built-in tests, Vite.

**Scope:** Tourist-side 0.8×, 1.0×, 1.2× and 1.5× options, default 1.0×. Applies to playback started after the preference changes. No backend, provider, cache, or stream contract changes. No dynamic rate changes during an active answer.

## Repository context

- Feature map: `docs/REPO_MAP.md`; compatibility notes: `docs/COMPATIBILITY.md`.
- Work continues in the existing project mirror on `codex/repository-map`; it contains prior uncommitted F01 changes required for this feature. Do not clean, reset, commit, or edit `sources/`.
- The frontend uses Node's built-in test runner. `frontend/node_modules` is not tracked in this mirror; if temporarily symlinked to the existing dependency tree for checks, remove only that symlink afterward.

## Files

- Add `frontend/src/utils/speechRatePreference.js` and `frontend/tests/speech-rate-preference.test.mjs` for storage, allowed rates and safe fallback.
- Update `frontend/src/composables/useAudioPlayer.js` and `frontend/tests/audio-player.test.mjs` for consistent rate application and content-time progress.
- Update `frontend/src/stores/chat.js` to carry client playback rate while sending neutral `tts_rate: 100` to the currently rate-agnostic backend.
- Update `frontend/src/views/tourist/ChatView.vue` and `MapView.vue` for shared preference wiring and accessible desktop/mobile controls.
- Update V03 checklist, compatibility notes, repository map and validation record with only covered behavior.

## Tasks

1. **Preference contract**
   - Add tests for the four allowed rates, default fallback, corrupt JSON, out-of-range values and storage exceptions.
   - Run them to see the expected missing-module failures.
   - Implement a pure rate normalization/read/write utility with an independent tourist storage key.

2. **Playback behavior**
   - Add failing player tests: AudioBuffer playback rate and content-time progress; PCM playback rate, real-time queue duration and content-time progress; speech synthesis rate.
   - Apply a shared clamped rate to all three paths. PCM chunk schedule duration is `buffer.duration / rate`; `elapsedMs`, duration and timeline remain source-content time.
   - Run focused player and speech tests.

3. **Tourist UI integration**
   - Add a persisted selector to the desktop narration settings and mobile conversation panel.
   - Pass the rate to Chat store playback options, map narration and welcome playback. Keep backend `tts_rate` fixed at 100 to avoid double adjustment if server-side rate support is added later.
   - Verify preference utility and audio tests plus a production build.

4. **Docs and final verification**
   - Update V03 status at the sub-item level and document active-playback behavior and device-testing limits.
   - Run full `npm test`, `npm run build -- --configLoader runner`, `python3 scripts/check_repo_map.py` and `git diff --check`.
   - Record that true-device sound quality and live subtitle/avatar synchronization remain pending manual acceptance.

## Completion evidence

- Tests cover persistence/fallback, rate application to each playback path, PCM scheduling and content-time callback alignment.
- Full frontend suite and production build pass; repository map and diff checks pass.
- No claim of real-device acoustic quality or full V03 completion.
