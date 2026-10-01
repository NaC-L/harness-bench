'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { makeEngine, recoverEngine } = require('../src');

async function drainMicrotasks() {
  for (let i = 0; i < 8; i += 1) await Promise.resolve();
}

test('reported WAL bug: a later successful flush must not publish across a pending LSN', async () => {
  const releases = [];
  const engine = makeEngine({ flush: () => new Promise(resolve => releases.push(resolve)) });
  const settled = [];
  const first = engine.commitUpdate('balance', 10).then(entry => { settled.push(entry.lsn); return entry; });
  const second = engine.commitUpdate('balance', 20).then(entry => { settled.push(entry.lsn); return entry; });
  try {
    assert.equal(releases.length, 2, 'both flushes start without waiting for either acknowledgment');
    releases[1]();
    await drainMicrotasks();
    assert.deepEqual(engine.runtimeState(), {}, 'LSN 2 must remain invisible until LSN 1 is durable');
    assert.deepEqual(engine.committedEntries(), []);
    assert.deepEqual(settled, []);
  } finally {
    for (let round = 0; round < 2; round += 1) {
      for (const release of releases) release();
      await drainMicrotasks();
    }
    await Promise.all([first, second]);
  }
  assert.deepEqual(engine.runtimeState(), { balance: 20 });
  assert.deepEqual(engine.committedEntries().map(entry => entry.lsn), [1, 2]);
});

test('WAL sequential regression: rotation, overwrite, and recovery agree on committed data', async () => {
  const engine = makeEngine({ segmentCapacity: 2 });
  assert.deepEqual(engine.crashSnapshot(), { segments: [] });
  assert.deepEqual(recoverEngine(engine.crashSnapshot()), {
    state: {}, replayed: [], stats: { segmentsScanned: 0, replayedEntries: 0, lastLsn: 0 },
  });
  assert.deepEqual(await engine.commitUpdate('account', 11), { lsn: 1, key: 'account', value: 11 });
  await engine.commitUpdate('other', false);
  await engine.commitUpdate('account', 22);
  const snapshot = engine.crashSnapshot();
  assert.deepEqual(snapshot, { segments: [
    { segmentId: 1, closed: true, durableCount: 2, entries: [
      { lsn: 1, key: 'account', value: 11 }, { lsn: 2, key: 'other', value: false },
    ] },
    { segmentId: 2, closed: false, durableCount: 1, entries: [
      { lsn: 3, key: 'account', value: 22 },
    ] },
  ] });
  assert.deepEqual(engine.runtimeState(), { account: 22, other: false });
  assert.deepEqual(recoverEngine(snapshot), {
    state: { account: 22, other: false },
    replayed: [
      { segmentId: 1, lsn: 1, key: 'account', value: 11 },
      { segmentId: 1, lsn: 2, key: 'other', value: false },
      { segmentId: 2, lsn: 3, key: 'account', value: 22 },
    ],
    stats: { segmentsScanned: 2, replayedEntries: 3, lastLsn: 3 },
  });
});
