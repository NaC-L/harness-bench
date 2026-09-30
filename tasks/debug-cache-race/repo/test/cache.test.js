'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createCache } = require('../src/cache');
const tick = () => new Promise(resolve => setImmediate(resolve));

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

test('invalidating during a load does not resurrect its stale value', { timeout: 2000 }, async () => {
  const gate = deferred();
  let calls = 0;
  const cache = createCache({
    now: () => 0,
    ttlMs: 100,
    load() {
      calls += 1;
      return calls === 1 ? gate.promise : 'fresh';
    }
  });
  const oldReader = cache.get('item');
  await tick();
  cache.invalidate('item');
  gate.resolve('stale');
  assert.equal(await oldReader, 'stale');
  assert.equal(await cache.get('item'), 'fresh');
  assert.equal(calls, 2);
});
