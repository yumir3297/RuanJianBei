import test from "node:test";
import assert from "node:assert/strict";
import { isItineraryEditIntent } from "../src/utils/itineraryIntent.js";

test("classifies a direct stop-duration change as an itinerary edit", () => {
  assert.equal(isItineraryEditIntent("把灵山大佛停留时间改成30分钟"), true);
});

test("does not classify an ordinary attraction question as an edit", () => {
  assert.equal(isItineraryEditIntent("灵山大佛有什么故事？"), false);
});
