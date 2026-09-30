'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { Worker } = require('node:worker_threads');

// The deadline runs on the parent event loop, not the synchronous diff's loop.
// Even a quadratic implementation cannot block grading for more than 15 s.
// Only algorithm execution is timed: worker startup does not spend the budget.
const BUDGET_MS = 1000;
const DEADLINE_MS = 15000;

test('hidden: sparse twenty-thousand-line reviews avoid quadratic work', { timeout: 20000 }, async t => {
  const worker = new Worker(`
    'use strict';
    const { parentPort, workerData } = require('node:worker_threads');
    const { performance } = require('node:perf_hooks');
    const assert = require('node:assert/strict');
    const { diffLines, unifiedHunks, applyHunks } = require(workerData);
    const a = Array.from({ length: 20000 }, (_, i) => 'line:' + i);
    const actions = new Map(Array.from({ length: 10 }, (_, i) => [1200 + i * 1700, i % 3]));
    const b = [];
    for (let i = 0; i < a.length; i++) {
      if (actions.get(i) === 0) b.push('replacement:' + i);
      else if (actions.get(i) === 1) b.push('inserted:' + i, a[i]);
      else if (actions.get(i) !== 2) b.push(a[i]);
    }
    const started = performance.now();
    const script = diffLines(a, b);
    const diffMs = performance.now() - started;
    assert.deepEqual(script.filter(x => x.op !== 'insert').map(x => x.line), a);
    assert.deepEqual(script.filter(x => x.op !== 'delete').map(x => x.line), b);
    assert.equal(script.filter(x => x.op !== 'equal').length, 14);
    const hunkStarted = performance.now();
    const hunks = unifiedHunks(a, b, { context: 3 });
    const result = applyHunks(a, hunks);
    const hunksMs = performance.now() - hunkStarted;
    assert.deepEqual(result, b);
    parentPort.postMessage({ diffMs, hunksMs, elapsedMs: diffMs + hunksMs });
  `, { eval: true, workerData: require.resolve('../src/diff') });

  let deadline;
  try {
    const result = await new Promise((resolve, reject) => {
      deadline = setTimeout(() => reject(new Error(
        `performance guard: exceeded ${DEADLINE_MS} ms worker deadline (budget ${BUDGET_MS} ms)`
      )), DEADLINE_MS);
      worker.once('message', resolve);
      worker.once('error', reject);
      worker.once('exit', code => {
        if (code !== 0) reject(new Error(`performance worker exited with code ${code}`));
      });
    });
    t.diagnostic(`diff=${result.diffMs.toFixed(3)}ms hunks=${result.hunksMs.toFixed(3)}ms total=${result.elapsedMs.toFixed(3)}ms budget=${BUDGET_MS}ms`);
    assert.ok(result.elapsedMs < BUDGET_MS,
      `performance guard: ${result.elapsedMs.toFixed(3)} ms exceeds ${BUDGET_MS} ms budget`);
  } finally {
    clearTimeout(deadline);
    await worker.terminate();
  }
});
