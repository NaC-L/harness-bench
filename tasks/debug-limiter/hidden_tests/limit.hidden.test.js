'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createLimiter } = require('../src/limit');
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test('validates concurrency and rejects invalid tasks without poisoning the queue', { timeout: 2000 }, async () => {
  for (const value of [undefined, null, 0, -1, 1.5, NaN, Infinity, '2', true, 2n]) {
    assert.throws(() => createLimiter(value), RangeError);
  }
  const run = createLimiter(1);
  for (const value of [undefined, null, 1, {}, Promise.resolve(1)]) {
    const promise = run(value);
    assert.ok(promise instanceof Promise);
    await assert.rejects(promise, TypeError);
  }
  assert.equal(await run(() => 7), 7);
});

test('synchronous throws, rejected promises, and thrown non-Errors release slots', { timeout: 2000 }, async () => {
  const run = createLimiter(1);
  const failures = [new Error('sync'), new Error('async'), 'plain rejection'];
  const first = run(() => { throw failures[0]; });
  const firstChecked = assert.rejects(first, error => error === failures[0]);
  const second = run(() => Promise.reject(failures[1]));
  const secondChecked = assert.rejects(second, error => error === failures[1]);
  const third = run(() => { throw failures[2]; });
  const thirdChecked = assert.rejects(third, error => error === failures[2]);
  const fourth = run(() => 99);
  await Promise.all([firstChecked, secondChecked, thirdChecked]);
  assert.equal(await fourth, 99);
});

test('each rejected task frees one slot while other work remains pending', { timeout: 2000 }, async () => {
  const run = createLimiter(2);
  const gates = [deferred(), deferred(), deferred(), deferred()];
  const started = [];
  const jobs = gates.map((gate, index) => run(() => {
    started.push(index);
    return gate.promise;
  }));
  const rejected = assert.rejects(jobs[0], /first failure/);
  await tick();
  assert.deepEqual(started, [0, 1]);
  gates[0].reject(new Error('first failure'));
  await rejected;
  await tick();
  assert.deepEqual(started, [0, 1, 2]);
  gates[2].resolve('third');
  await tick();
  assert.deepEqual(started, [0, 1, 2, 3]);
  gates[1].resolve('second');
  gates[3].resolve('fourth');
  assert.deepEqual(await Promise.all(jobs.slice(1)), ['second', 'third', 'fourth']);
});

test('ordinary values, thenables, and invocation counts are preserved', { timeout: 2000 }, async () => {
  const run = createLimiter(3);
  let calls = 0;
  const jobs = Array.from({ length: 30 }, (_, index) => run(function () {
    calls += 1;
    assert.equal(arguments.length, 0);
    return index % 2 ? { then(resolve) { resolve(index); } } : index;
  }));
  assert.deepEqual(await Promise.all(jobs), Array.from({ length: 30 }, (_, i) => i));
  assert.equal(calls, 30);
  assert.equal(await run(() => undefined), undefined);
});

test('separate limiter instances do not share slots', { timeout: 2000 }, async () => {
  const gate = deferred();
  const a = createLimiter(1);
  const b = createLimiter(1);
  const pending = a(() => gate.promise);
  assert.equal(await b(() => 'independent'), 'independent');
  gate.resolve('done');
  assert.equal(await pending, 'done');
});
