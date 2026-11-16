import test from "node:test";
import assert from "node:assert/strict";

import {
  getAvatarAction,
  getAvatarIntentAction,
} from "../src/components/avatar-actions.js";

test("avatar intents resolve to actions supported by each preset", () => {
  for (const preset of ["modern", "monk", "hanfu"]) {
    for (const intent of ["greet", "explain", "farewell", "remind", "think"]) {
      const action = getAvatarIntentAction(intent, preset);
      assert.ok(action, `${preset}/${intent} has a mapped action`);
      assert.ok(getAvatarAction(action), `${preset}/${intent} maps to a registered action`);
    }
  }
});

test("unknown preset falls back to the stable modern mapping", () => {
  assert.equal(getAvatarIntentAction("explain", "unknown"), "jingxing_exhibit_draft");
  assert.equal(getAvatarIntentAction("missing", "modern"), "");
});
