'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createLimiter } = require('../src/limit');
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

test('enforces the concurrency limit and starts queued work in order', { timeout: 2000 }, async () => {
  const run = createLimiter(2);
  const gates = Array.from({ length: 4 }, deferred);
  const started = [];
  const results = gates.map((gate, index) => run(async () => {
    started.push(index);
    await gate.promise;
    return index * 10;
  }));
  await tick();
  assert.deepEqual(started, [0, 1]);
  gates[1].resolve();
  await tick();
  assert.deepEqual(started, [0, 1, 2]);
  gates[0].resolve();
  await tick();
  assert.deepEqual(started, [0, 1, 2, 3]);
  gates[2].resolve();
  gates[3].resolve();
  assert.deepEqual(await Promise.all(results), [0, 10, 20, 30]);
});

test('queued work still completes when a task rejects', { timeout: 2000 }, async () => {
  const run = createLimiter(1);
  const error = new Error('task failed');
  const rejected = run(async () => { throw error; });
  const rejection = assert.rejects(rejected, actual => actual === error);
  const next = run(() => 42);
  await rejection;
  assert.equal(await next, 42);
  assert.equal(await run(() => 'still usable'), 'still usable');
});
