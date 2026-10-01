'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { makeEngine, recoverEngine } = require('../src');

async function drainMicrotasks() {
  for (let i = 0; i < 8; i += 1) await Promise.resolve();
}

function controlled(capacity) {
  const requests = [];
  const engine = makeEngine({
    segmentCapacity: capacity,
    flush: entry => new Promise(resolve => requests.push({ entry, resolve })),
  });
  return { engine, requests };
}

test('hidden WAL concurrency: seven writers preserve local durability and the global acknowledgment frontier', async () => {
  const { engine, requests } = controlled(2);
  const entries = Array.from({ length: 7 }, (_, i) => ({ lsn: i + 1, key: `k${i % 3}`, value: { n: i + 1 } }));
  const settled = Array(7).fill(false);
  const commits = entries.map(entry => engine.commitUpdate(entry.key, entry.value).then(result => {
    settled[result.lsn - 1] = true;
    return result;
  }));
  try {
    assert.equal(requests.length, 7, 'flush concurrency cannot be replaced by serialized writers');
    assert.deepEqual(requests.map(request => request.entry), entries);
    assert.deepEqual(engine.crashSnapshot(), { segments: [
      { segmentId: 1, closed: true, durableCount: 0, entries: entries.slice(0, 2) },
      { segmentId: 2, closed: true, durableCount: 0, entries: entries.slice(2, 4) },
      { segmentId: 3, closed: true, durableCount: 0, entries: entries.slice(4, 6) },
      { segmentId: 4, closed: false, durableCount: 0, entries: entries.slice(6) },
    ] }, 'append and rotation must already have happened before any flush fulfills');

    for (const index of [6, 4, 2]) requests[index].resolve();
    await drainMicrotasks();
    assert.deepEqual(engine.crashSnapshot().segments.map(segment => segment.durableCount), [0, 1, 1, 1]);
    assert.deepEqual(settled, Array(7).fill(false));
    assert.deepEqual(engine.runtimeState(), {});
    assert.deepEqual(engine.committedEntries(), []);
    assert.deepEqual(recoverEngine(engine.crashSnapshot()), {
      state: {}, replayed: [], stats: { segmentsScanned: 4, replayedEntries: 0, lastLsn: 0 },
    }, 'locally durable rotated segments cannot bridge the absent first LSN');

    for (const [released, frontier, counts] of [
      [0, 1, [1, 1, 1, 1]],
      [1, 3, [2, 1, 1, 1]],
      [3, 5, [2, 2, 1, 1]],
      [5, 7, [2, 2, 2, 1]],
    ]) {
      requests[released].resolve();
      await drainMicrotasks();
      assert.deepEqual(settled, entries.map(entry => entry.lsn <= frontier));
      assert.deepEqual(engine.committedEntries(), entries.slice(0, frontier));
      const expectedState = Object.fromEntries(entries.slice(0, frontier).map(entry => [entry.key, entry.value]));
      assert.deepEqual(engine.runtimeState(), expectedState);
      assert.deepEqual(engine.crashSnapshot().segments.map(segment => segment.durableCount), counts);
      assert.deepEqual(recoverEngine(engine.crashSnapshot()).state, expectedState);
    }
    assert.deepEqual(await Promise.all(commits), entries);
  } finally {
    for (let round = 0; round < commits.length; round += 1) {
      for (const request of requests) request.resolve();
      await drainMicrotasks();
    }
    await Promise.all(commits);
  }
});

test('hidden WAL holes: a completed second entry is not a segment durable prefix', async () => {
  const { engine, requests } = controlled(3);
  const first = engine.commitUpdate('x', 1);
  const second = engine.commitUpdate('x', 2);
  const third = engine.commitUpdate('y', 3);
  try {
    assert.equal(requests.length, 3);
    requests[1].resolve();
    requests[2].resolve();
    await drainMicrotasks();
    const snapshot = engine.crashSnapshot();
    assert.equal(snapshot.segments[0].durableCount, 0);
    assert.deepEqual(snapshot.segments[0].entries.map(entry => entry.lsn), [1, 2, 3]);
    assert.deepEqual(engine.runtimeState(), {});
    assert.deepEqual(engine.committedEntries(), []);
    assert.deepEqual(recoverEngine(snapshot).replayed, []);
    requests[0].resolve();
    assert.deepEqual(await Promise.all([first, second, third]), [
      { lsn: 1, key: 'x', value: 1 }, { lsn: 2, key: 'x', value: 2 }, { lsn: 3, key: 'y', value: 3 },
    ]);
    assert.equal(engine.crashSnapshot().segments[0].durableCount, 3);
    assert.deepEqual(engine.runtimeState(), { x: 2, y: 3 });
  } finally {
    for (let round = 0; round < 3; round += 1) {
      for (const request of requests) request.resolve();
      await drainMicrotasks();
    }
    await Promise.all([first, second, third]);
  }
});

test('hidden WAL ownership: input, flush, pending snapshots, acknowledgments and accessors are detached', async () => {
  const { engine, requests } = controlled(1);
  const value = { rows: [{ n: 7, labels: ['a', 'b'] }], flag: null };
  const original = structuredClone(value);
  const commit = engine.commitUpdate('data', value);
  try {
    assert.equal(requests.length, 1);
    value.rows[0].n = 900;
    value.rows[0].labels.push('caller');
    assert.deepEqual(requests[0].entry.value, original, 'capture input before the first await');
    const pending = engine.crashSnapshot();
    assert.deepEqual(pending.segments[0].entries, [{ lsn: 1, key: 'data', value: original }]);
    pending.segments[0].entries[0].value.rows[0].n = 901;
    pending.segments[0].entries.length = 0;
    requests[0].entry.value.rows[0].n = 902;
    requests[0].entry.value.rows[0].labels.push('flush');
    requests[0].entry.key = 'forged';
    requests[0].entry.lsn = 99;
    assert.deepEqual(engine.crashSnapshot().segments[0].entries, [{ lsn: 1, key: 'data', value: original }]);
    requests[0].resolve();
    const acknowledged = await commit;
    assert.deepEqual(acknowledged, { lsn: 1, key: 'data', value: original });
    const state = engine.runtimeState();
    const committed = engine.committedEntries();
    const snapshot = engine.crashSnapshot();
    acknowledged.value.rows[0].n = 903;
    state.data.rows[0].labels.push('state');
    committed[0].value.rows[0].n = 904;
    snapshot.segments[0].entries[0].value.rows[0].n = 905;
    assert.deepEqual(engine.runtimeState(), { data: original });
    assert.deepEqual(engine.committedEntries(), [{ lsn: 1, key: 'data', value: original }]);
    assert.deepEqual(engine.crashSnapshot().segments[0].entries, [{ lsn: 1, key: 'data', value: original }]);
    assert.equal(state.data.rows[0].n, 7, 'other output mutation must not leak into this state result');
    assert.deepEqual(committed[0].value.rows[0].labels, ['a', 'b']);
    const recovered = recoverEngine(engine.crashSnapshot());
    assert.deepEqual(recovered.state, { data: original });
    assert.deepEqual(recovered.replayed, [{ segmentId: 1, lsn: 1, key: 'data', value: original }]);
  } finally {
    for (const request of requests) request.resolve();
    await commit;
  }
});

test('hidden WAL regression: special string keys and separate default engines keep independent state', async () => {
  const a = makeEngine();
  const b = makeEngine();
  await a.commitUpdate('__proto__', { ok: true });
  await a.commitUpdate('constructor', 17);
  await a.commitUpdate('toString', null);
  await b.commitUpdate('onlyB', ['b']);
  const expected = Object.fromEntries([['__proto__', { ok: true }], ['constructor', 17], ['toString', null]]);
  assert.deepEqual(a.runtimeState(), expected);
  assert.deepEqual(recoverEngine(a.crashSnapshot()).state, expected);
  assert.deepEqual(b.runtimeState(), { onlyB: ['b'] });
  assert.deepEqual(b.committedEntries(), [{ lsn: 1, key: 'onlyB', value: ['b'] }]);
});
