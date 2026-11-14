# CASS Competition Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Complete a deterministic CASS showcase linking contextual decisions to explainable itinerary suggestions and explicit V01 confirmation, while protecting core guide flows.

**Architecture:** Keep the existing FastAPI rules and Vue reducer. Make decisions carry stable reason/evidence metadata, rank simultaneous safety events, and gate stale UI results. A contextual suggestion may initiate the existing durable itinerary proposal workflow; only its current version-checked apply action mutates the tour.

**Tech Stack:** Vue 3, Pinia, Node built-in tests, FastAPI, Pydantic, SQLAlchemy/Alembic only if existing proposal contract requires persistence.

**Spec:** `docs/research/2026-11-07-cass-competition-completion.md`

## Global Constraints

- Preserve the current non-CASS chat, audio, map, stop and replay behavior when CASS is off or unavailable.
- Never treat demo location, weather or crowd values as live safety evidence.
- Never apply an itinerary change without explicit user confirmation and current version checks.
- Reuse V01/W02; do not add a second workflow engine or checkpoint database.

## Review Focus

- Event identity, expiry, priority and acknowledgement versus resolution.
- Out-of-order decision responses and stale proposal application.
- Provider/worker failure must leave the existing itinerary untouched.
- Safety events cannot accidentally trigger ordinary narration.

## Tasks

- [x] CASS-01: Add failing reducer tests for re-alert, priority arbitration, same-event instruction updates and generation invalidation; clear displayed assessments when visitor, location or tour inputs change, and expire decisions before their evidence becomes stale.
- [x] CASS-02: Return bounded decision reasons, evidence references, data mode, validity and suggestions; add a labeled simulated crowd scenario and show provenance on the card.
- [x] CASS-03: Add explicit “make itinerary proposal” action for short-time scenarios; it calls existing `tourStore.requestProposal` and preserves preview/apply path and version fences.
- [x] CASS-04: Automated frontend suite/build (187), focused CASS backend tests (20), related CASS/V01/W02 SQLite and worker regression (60), map checks and diff check pass; static review confirms existing ChatView query/recording/stop/replay/proposal-confirm handlers remain connected. Browser end-to-end scenario remains unverified.
- [x] Update CASS guide/acceptance docs and mark exact evidence and remaining field boundaries.
- [x] CASS-05: Add evidence-bounded, non-safety narration adaptation for fresh QWeather precipitation; add an explicitly simulated, repeatable rainy-weather showcase; verify the Vue panel event path and repair the shared demo decision setter found by component testing.
- [x] CASS-06: Suggest nearby published attractions only from fresh accurate real positioning and coordinate-evidenced GCJ-02 catalog entries; require visitor selection and keep raw GPS local to the browser.
- [x] CASS-07: Bound QWeather precipitation adaptation by both fetch and observation timestamps and fail closed when the observation is stale or absent.
- [x] CASS-08: Write and index a repeatable competition demo script with setup requirements, main flows and transparent fallback behavior.
