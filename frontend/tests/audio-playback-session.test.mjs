import test from "node:test";
import assert from "node:assert/strict";
import { useAudioPlayer } from "../src/composables/useAudioPlayer.js";

test("map and chat narration share one playback owner and replacement invalidates the old session", () => {
  const audio = useAudioPlayer();
  const stopped = [];
  const mapSession = audio.claimPlayback("map-narration", reason => stopped.push(["map", reason]));
  const chatSession = audio.claimPlayback("chat", reason => stopped.push(["chat", reason]));

  assert.equal(audio.isCurrentPlaybackSession(mapSession.id), false);
  assert.equal(audio.isCurrentPlaybackSession(chatSession.id), true);
  assert.deepEqual(audio.activePlayback.value, { id: chatSession.id, owner: "chat" });
  assert.deepEqual(stopped, [["map", "replaced"]]);
  assert.equal(audio.stop(mapSession.id), false);
  assert.equal(audio.stop(chatSession.id), true);
  assert.deepEqual(stopped, [["map", "replaced"], ["chat", "stopped"]]);
  assert.equal(audio.activePlayback.value, null);
});
