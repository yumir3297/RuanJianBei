import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

test('invalid position drops pending narration without interrupting audio', async () => {
  const vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-narration-position', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  try {
    const { useNarration } = await vite.ssrLoadModule('/src/composables/useNarration.js');
    let interrupts = 0, triggers = 0;
    const narration = useNarration({ getPosition: () => null, getSpots: () => [], isBusy: () => true,
      onInterrupt: () => interrupts++, onTrigger: () => triggers++, maxPendingWaitMs: 0 });
    narration.trigger({ name: '景点', lat: 31, lng: 120 });
    narration.drainPending();
    assert.equal(interrupts, 0);
    assert.equal(triggers, 0);
  } finally { await vite.close(); }
});
