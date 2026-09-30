'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createCache } = require('../src/cache');
const tick = () => new Promise(resolve => setImmediate(resolve));

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function gatedCache(gates, options = {}) {
  const calls = [];
  const cache = createCache({
    now: () => 0,
    ttlMs: 100,
    ...options,
    load(key) {
      calls.push(key);
      assert.ok(calls.length <= gates.length, 'unexpected additional load');
      return gates[calls.length - 1].promise;
    }
  });
  return { cache, calls };
}

test('race: a fresh flight can finish before the invalidated flight', { timeout: 2000 }, async () => {
  const gates = [deferred(), deferred()];
  const { cache, calls } = gatedCache(gates);
  const old = cache.get('k');
  await tick();
  cache.invalidate('k');
  const fresh = cache.get('k');
  await tick();
  assert.deepEqual(calls, ['k', 'k']);
  gates[1].resolve('fresh');
  assert.equal(await fresh, 'fresh');
  gates[0].resolve('obsolete');
  assert.equal(await old, 'obsolete');
  assert.equal(await cache.get('k'), 'fresh');
  assert.equal(cache.size, 1);
});

test('race: obsolete success cannot remove or replace a still-pending fresh flight', { timeout: 2000 }, async () => {
  const gates = [deferred(), deferred(), deferred()];
  const { cache, calls } = gatedCache(gates);
  const old = cache.get('k');
  await tick();
  cache.invalidate('k');
  const fresh = cache.get('k');
  await tick();
  gates[0].resolve('obsolete');
  assert.equal(await old, 'obsolete');
  assert.equal(cache.size, 0);
  const joining = cache.get('k');
  await tick();
  assert.equal(calls.length, 2);
  gates[1].resolve('fresh');
  assert.deepEqual(await Promise.all([fresh, joining]), ['fresh', 'fresh']);
  assert.equal(await cache.get('k'), 'fresh');
});

test('race: two invalidations survive every completion order of three generations', { timeout: 2000 }, async () => {
  const orders = [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]];
  for (const order of orders) {
    const gates = [deferred(), deferred(), deferred()];
    const { cache, calls } = gatedCache(gates);
    const readers = [];
    for (let generation = 0; generation < 3; generation += 1) {
      if (generation) cache.invalidate('k');
      readers.push(cache.get('k'));
      await tick();
    }
    assert.equal(calls.length, 3);
    for (const generation of order) {
      gates[generation].resolve(`value-${generation}`);
      assert.equal(await readers[generation], `value-${generation}`);
      assert.equal(cache.size, order.indexOf(2) <= order.indexOf(generation) ? 1 : 0);
    }
    assert.equal(await cache.get('k'), 'value-2', `completion order ${order}`);
    assert.equal(calls.length, 3);
  }
});

test('race: repeated invalidation without a stored value still detaches all old work', { timeout: 2000 }, async () => {
  const gates = [deferred(), deferred()];
  const { cache, calls } = gatedCache(gates);
  const old = cache.get('k');
  cache.invalidate('k');
  cache.invalidate('k');
  const fresh = cache.get('k');
  await tick();
  assert.equal(calls.length, 2);
  gates[0].resolve('old');
  assert.equal(await old, 'old');
  assert.equal(cache.size, 0);
  gates[1].resolve('new');
  assert.equal(await fresh, 'new');
  assert.equal(await cache.get('k'), 'new');
});

test('race: set wins and obsolete success cannot extend the set value TTL', { timeout: 2000 }, async () => {
  let time = 0;
  const gates = [deferred(), deferred()];
  const { cache, calls } = gatedCache(gates, { ttlMs: 10, now: () => time });
  const old = cache.get('k');
  await tick();
  time = 3;
  assert.equal(cache.set('k', 'manual'), undefined);
  assert.equal(await cache.get('k'), 'manual');
  time = 8;
  gates[0].resolve('obsolete');
  assert.equal(await old, 'obsolete');
  assert.equal(await cache.get('k'), 'manual');
  time = 13;
  assert.equal(cache.size, 0);
  const fresh = cache.get('k');
  await tick();
  assert.equal(calls.length, 2);
  gates[1].resolve('fresh');
  assert.equal(await fresh, 'fresh');
});

test('race: expired set values do not rejoin an older detached flight', { timeout: 2000 }, async () => {
  let time = 0;
  const gates = [deferred(), deferred(), deferred()];
  const { cache, calls } = gatedCache(gates, { ttlMs: 5, now: () => time });
  const old = cache.get('k');
  await tick();
  cache.set('k', 'manual');
  time = 5;
  const fresh = cache.get('k');
  await tick();
  assert.equal(calls.length, 2);
  gates[0].resolve('obsolete');
  assert.equal(await old, 'obsolete');
  const joining = cache.get('k');
  await tick();
  assert.equal(calls.length, 2);
  gates[1].resolve('fresh');
  assert.deepEqual(await Promise.all([fresh, joining]), ['fresh', 'fresh']);
});

test('race: clear detaches every flight without cancelling its original readers', { timeout: 2000 }, async () => {
  const gates = [deferred(), deferred(), deferred()];
  const { cache, calls } = gatedCache(gates);
  cache.set('stored', 1);
  const oldA = cache.get('a');
  const oldB = cache.get('b');
  await tick();
  assert.equal(cache.clear(), undefined);
  assert.equal(cache.size, 0);
  const freshA = cache.get('a');
  await tick();
  assert.deepEqual(calls, ['a', 'b', 'a']);
  gates[2].resolve('fresh-a');
  assert.equal(await freshA, 'fresh-a');
  gates[0].resolve('old-a');
  gates[1].resolve('old-b');
  assert.deepEqual(await Promise.all([oldA, oldB]), ['old-a', 'old-b']);
  assert.equal(cache.size, 1);
  assert.equal(await cache.get('a'), 'fresh-a');
});

test('race: set then invalidate does not let a pre-set load resurrect a value', { timeout: 2000 }, async () => {
  const gates = [deferred(), deferred()];
  const { cache, calls } = gatedCache(gates);
  const old = cache.get('k');
  await tick();
  cache.set('k', 'manual');
  cache.invalidate('k');
  gates[0].resolve('obsolete');
  assert.equal(await old, 'obsolete');
  assert.equal(cache.size, 0);
  const fresh = cache.get('k');
  await tick();
  assert.equal(calls.length, 2);
  gates[1].resolve('fresh');
  assert.equal(await fresh, 'fresh');
});

test('failure: all waiters receive the same reason and the next flight can retry', { timeout: 2000 }, async () => {
  const gates = [deferred(), deferred()];
  const { cache, calls } = gatedCache(gates);
  const reason = new Error('backend unavailable');
  const waiters = Array.from({ length: 8 }, () => cache.get('k'));
  const checked = waiters.map(promise => assert.rejects(promise, actual => actual === reason));
  await tick();
  assert.equal(calls.length, 1);
  gates[0].reject(reason);
  await Promise.all(checked);
  assert.equal(cache.size, 0);
  const retry = cache.get('k');
  const observed = retry.then(value => ({ value }), error => ({ error }));
  await tick();
  // Resolve even when the baseline incorrectly reuses the failed promise.
  gates[1].resolve('recovered');
  assert.deepEqual(await observed, { value: 'recovered' });
  assert.equal(await retry, 'recovered');
  assert.equal(calls.length, 2);
});

test('failure: synchronous throws do not poison subsequent reads', { timeout: 2000 }, async () => {
  const reason = { unavailable: true };
  let calls = 0;
  const cache = createCache({ now: () => 0, load() {
    calls += 1;
    if (calls === 1) throw reason;
    return 'recovered';
  } });
  const first = cache.get('k');
  const second = cache.get('k');
  assert.ok(first instanceof Promise);
  await Promise.all([first, second].map(promise => assert.rejects(promise, actual => actual === reason)));
  assert.equal(calls, 1);
  assert.equal(await cache.get('k'), 'recovered');
  assert.equal(calls, 2);
});

test('failure: rejected thenables with non-Error reasons are retriable', { timeout: 2000 }, async () => {
  for (const reason of [undefined, null, false, 'not an Error']) {
    let calls = 0;
    const cache = createCache({ now: () => 0, load() {
      calls += 1;
      return calls === 1 ? { then(resolve, reject) { reject(reason); } } : 7;
    } });
    await assert.rejects(cache.get('k'), actual => actual === reason);
    assert.equal(await cache.get('k'), 7);
    assert.equal(calls, 2);
  }
});

test('failure: rejection of the replacement cannot make an obsolete success cacheable', { timeout: 2000 }, async () => {
  const gates = [deferred(), deferred(), deferred()];
  const { cache, calls } = gatedCache(gates);
  const old = cache.get('k');
  await tick();
  cache.invalidate('k');
  const replacement = cache.get('k');
  const checked = assert.rejects(replacement, /new flight failed/);
  await tick();
  gates[1].reject(new Error('new flight failed'));
  await checked;
  gates[0].resolve('obsolete');
  assert.equal(await old, 'obsolete');
  assert.equal(cache.size, 0);
  const retry = cache.get('k');
  await tick();
  assert.equal(calls.length, 3);
  gates[2].resolve('recovered');
  assert.equal(await retry, 'recovered');
});

test('race: a loader can invalidate its own flight synchronously', { timeout: 2000 }, async () => {
  let calls = 0;
  const cache = createCache({ now: () => 0, load(key) {
    calls += 1;
    if (calls === 1) cache.invalidate(key);
    return calls === 1 ? 'obsolete' : 'fresh';
  } });
  assert.equal(await cache.get('k'), 'obsolete');
  assert.equal(cache.size, 0);
  assert.equal(await cache.get('k'), 'fresh');
  assert.equal(calls, 2);
});

test('race: a loader can set a winning value before returning', { timeout: 2000 }, async () => {
  const cache = createCache({ now: () => 0, load(key) {
    cache.set(key, 'manual');
    return 'obsolete';
  } });
  assert.equal(await cache.get('k'), 'obsolete');
  assert.equal(await cache.get('k'), 'manual');
});

test('race: clear inside a loader invalidates stored values and all pending keys', { timeout: 2000 }, async () => {
  const gate = deferred();
  let bCalls = 0;
  const cache = createCache({ now: () => 0, load(key) {
    if (key === 'a') {
      cache.clear();
      return 'old-a';
    }
    bCalls += 1;
    return bCalls === 1 ? gate.promise : 'fresh-b';
  } });
  cache.set('stored', 1);
  const oldB = cache.get('b');
  await tick();
  assert.equal(await cache.get('a'), 'old-a');
  gate.resolve('old-b');
  assert.equal(await oldB, 'old-b');
  assert.equal(cache.size, 0);
  assert.equal(await cache.get('b'), 'fresh-b');
});
