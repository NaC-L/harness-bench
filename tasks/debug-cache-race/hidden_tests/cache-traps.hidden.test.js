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

// Every trap in this file passes on the unmodified starting repository.
test('trap: concurrent reads invoke one load and deliver its value to every waiter', { timeout: 2000 }, async () => {
  const gate = deferred();
  let calls = 0;
  const value = { answer: 42 };
  const cache = createCache({ now: () => 0, load() { calls += 1; return gate.promise; } });
  const readers = Array.from({ length: 20 }, () => cache.get('same'));
  assert.ok(readers.every(promise => promise instanceof Promise));
  await tick();
  assert.equal(calls, 1);
  assert.equal(cache.size, 0);
  gate.resolve(value);
  const results = await Promise.all(readers);
  assert.ok(results.every(result => result === value));
  assert.equal(cache.size, 1);
  assert.equal(await cache.get('same'), value);
  assert.equal(calls, 1);
});

test('trap: successful values remain cached until the exact TTL boundary', { timeout: 2000 }, async () => {
  let time = 10;
  let calls = 0;
  const cache = createCache({ ttlMs: 5, now: () => time, load() { return ++calls; } });
  assert.equal(await cache.get('k'), 1);
  time = 14;
  assert.equal(await cache.get('k'), 1);
  assert.equal(cache.size, 1);
  time = 15;
  assert.equal(cache.size, 0);
  assert.equal(await cache.get('k'), 2);
  assert.equal(calls, 2);
});

test('trap: load TTL starts at successful settlement rather than at read submission', { timeout: 2000 }, async () => {
  let time = 0;
  let calls = 0;
  const gate = deferred();
  const cache = createCache({ ttlMs: 10, now: () => time, load() {
    calls += 1;
    return calls === 1 ? gate.promise : 'second';
  } });
  const pending = cache.get('k');
  await tick();
  time = 90;
  gate.resolve('first');
  assert.equal(await pending, 'first');
  time = 99;
  assert.equal(await cache.get('k'), 'first');
  assert.equal(calls, 1);
  time = 100;
  assert.equal(await cache.get('k'), 'second');
  assert.equal(calls, 2);
});

test('trap: an unresolved key cannot block another key', { timeout: 2000 }, async () => {
  const gate = deferred();
  const calls = [];
  const cache = createCache({ now: () => 0, load(key) {
    calls.push(key);
    return key === 'slow' ? gate.promise : 'fast-result';
  } });
  const slow = cache.get('slow');
  assert.equal(await cache.get('fast'), 'fast-result');
  assert.deepEqual(calls, ['slow', 'fast']);
  assert.equal(cache.size, 1);
  gate.resolve('slow-result');
  assert.equal(await slow, 'slow-result');
  assert.equal(cache.size, 2);
});

test('trap: load receives only the unchanged key and Map key identity is preserved', { timeout: 2000 }, async () => {
  let calls = 0;
  const cache = createCache({ now: () => 0, load: function (key) {
    assert.equal(arguments.length, 1);
    calls += 1;
    return key;
  } });
  const objectA = {};
  const objectB = {};
  const symbol = Symbol('key');
  for (const key of [objectA, objectB, symbol, undefined, null, NaN, 0, '0']) {
    assert.equal(await cache.get(key), key);
    assert.equal(await cache.get(key), key);
  }
  assert.equal(await cache.get(-0), 0);
  assert.equal(calls, 8);
  assert.equal(cache.size, 8);
});

test('trap: obsolete rejection cannot detach a replacement flight', { timeout: 2000 }, async () => {
  const oldGate = deferred();
  const freshGate = deferred();
  let calls = 0;
  const cache = createCache({ now: () => 0, load() {
    calls += 1;
    return calls === 1 ? oldGate.promise : freshGate.promise;
  } });
  const old = cache.get('k');
  const checked = assert.rejects(old, /obsolete failure/);
  await tick();
  cache.invalidate('k');
  const fresh = cache.get('k');
  await tick();
  oldGate.reject(new Error('obsolete failure'));
  await checked;
  const joining = cache.get('k');
  await tick();
  assert.equal(calls, 2);
  freshGate.resolve('fresh');
  assert.deepEqual(await Promise.all([fresh, joining]), ['fresh', 'fresh']);
  assert.equal(await cache.get('k'), 'fresh');
});

test('trap: falsey successful and explicitly set values are real cache entries', { timeout: 2000 }, async () => {
  const values = [undefined, null, false, 0, '', NaN];
  let calls = 0;
  const cache = createCache({ now: () => 0, load(key) { calls += 1; return values[key]; } });
  for (let key = 0; key < values.length; key += 1) {
    assert.equal(await cache.get(key), values[key]);
    assert.equal(await cache.get(key), values[key]);
    cache.set(`set-${key}`, values[key]);
    const cached = cache.get(`set-${key}`);
    assert.ok(cached instanceof Promise);
    assert.equal(await cached, values[key]);
  }
  assert.equal(calls, values.length);
  assert.equal(cache.size, values.length * 2);
});

test('trap: zero TTL shares pending work but never reuses settled values', { timeout: 2000 }, async () => {
  const gate = deferred();
  let calls = 0;
  const cache = createCache({ ttlMs: 0, now: () => 0, load() {
    calls += 1;
    return calls === 1 ? gate.promise : calls;
  } });
  const first = cache.get('k');
  const joining = cache.get('k');
  await tick();
  assert.equal(calls, 1);
  gate.resolve(1);
  assert.deepEqual(await Promise.all([first, joining]), [1, 1]);
  assert.equal(cache.size, 0);
  assert.equal(await cache.get('k'), 2);
  assert.equal(cache.size, 0);
  cache.set('k', 'manual');
  assert.equal(await cache.get('k'), 3);
});

test('trap: size prunes expired stored entries without forgetting pending flights', { timeout: 2000 }, async () => {
  let time = 0;
  let calls = 0;
  const gate = deferred();
  const cache = createCache({ ttlMs: 5, now: () => time, load() { calls += 1; return gate.promise; } });
  cache.set('expires', 'stored');
  const first = cache.get('pending');
  await tick();
  assert.equal(cache.size, 1);
  time = 5;
  assert.equal(cache.size, 0);
  const joining = cache.get('pending');
  await tick();
  assert.equal(calls, 1);
  gate.resolve('loaded');
  assert.deepEqual(await Promise.all([first, joining]), ['loaded', 'loaded']);
  assert.equal(cache.size, 1);
});

test('trap: a loader can read its own key without starting a second flight', { timeout: 2000 }, async () => {
  let calls = 0;
  let nested;
  const cache = createCache({ now: () => 0, load(key) {
    calls += 1;
    nested = cache.get(key);
    return { then(resolve) { resolve('loaded'); } };
  } });
  assert.equal(await cache.get('k'), 'loaded');
  assert.equal(await nested, 'loaded');
  assert.equal(calls, 1);
});

test('trap: separate cache instances do not share values or flights', { timeout: 2000 }, async () => {
  const gate = deferred();
  const a = createCache({ now: () => 0, load() { return gate.promise; } });
  const b = createCache({ now: () => 0, load() { return 'b'; } });
  const pending = a.get('same');
  assert.equal(await b.get('same'), 'b');
  a.clear();
  assert.equal(await b.get('same'), 'b');
  gate.resolve('a');
  assert.equal(await pending, 'a');
  assert.equal(b.size, 1);
});

test('trap: ordinary set invalidate and clear retain their synchronous API', { timeout: 2000 }, async () => {
  const cache = createCache({ now: () => 0, load(key) { return key; } });
  assert.equal(cache.set('a', 1), undefined);
  assert.equal(cache.set('b', 2), undefined);
  assert.equal(cache.size, 2);
  assert.equal(cache.invalidate('missing'), undefined);
  assert.equal(cache.invalidate('a'), undefined);
  assert.equal(cache.size, 1);
  assert.equal(await cache.get('a'), 'a');
  assert.equal(await cache.get('b'), 2);
  assert.equal(cache.clear(), undefined);
  assert.equal(cache.size, 0);
  assert.equal(await cache.get('b'), 'b');
});

test('trap: construction validates load ttl and clock and preserves the default TTL', { timeout: 2000 }, async () => {
  for (const load of [undefined, null, 1, {}, 'loader']) {
    assert.throws(() => createCache({ load }), TypeError);
  }
  for (const ttlMs of [-1, NaN, Infinity, -Infinity, '5', null, true, 1n]) {
    assert.throws(() => createCache({ load() {}, ttlMs }), RangeError);
  }
  for (const now of [null, 1, {}, 'clock']) {
    assert.throws(() => createCache({ load() {}, now }), TypeError);
  }
  let time = 0;
  let calls = 0;
  const cache = createCache({ now: () => time, load() { return ++calls; } });
  assert.equal(await cache.get('k'), 1);
  time = 999;
  assert.equal(await cache.get('k'), 1);
  time = 1000;
  assert.equal(await cache.get('k'), 2);
});
