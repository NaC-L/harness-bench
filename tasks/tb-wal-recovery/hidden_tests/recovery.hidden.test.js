'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { recoverEngine } = require('../src');

function freezeDeep(value) {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) freezeDeep(child);
    Object.freeze(value);
  }
  return value;
}

function random(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function shuffle(items, rng) {
  const result = items.slice();
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rng() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

// Independent oracle: flatten durable slices, sort by LSN/containing ID, then
// consume one sorted group at a time. No per-LSN candidate map is used.
function oracle(snapshot) {
  const rows = [];
  for (const segment of snapshot.segments) {
    for (const entry of segment.entries.slice(0, segment.durableCount ?? 0)) {
      rows.push({ segmentId: segment.segmentId, lsn: entry.lsn, key: entry.key, value: entry.value });
    }
  }
  rows.sort((a, b) => a.lsn - b.lsn || a.segmentId - b.segmentId);
  const replayed = [];
  const state = {};
  let expected = 1;
  for (let i = 0; i < rows.length;) {
    const row = rows[i];
    if (row.lsn !== expected) break;
    replayed.push(JSON.parse(JSON.stringify(row)));
    Object.defineProperty(state, row.key, {
      value: JSON.parse(JSON.stringify(row.value)), writable: true, enumerable: true, configurable: true,
    });
    expected += 1;
    do { i += 1; } while (i < rows.length && rows[i].lsn === row.lsn);
  }
  return { state, replayed, stats: {
    segmentsScanned: snapshot.segments.length, replayedEntries: replayed.length, lastLsn: expected - 1,
  } };
}

test('hidden WAL recovery: durable slices, gap stopping, authoritative IDs and permutations interact', () => {
  const snapshot = { segments: [
    { segmentId: 9, closed: false, durableCount: 2, entries: [
      { lsn: 6, key: 'ignoredAfterGap', value: 60 },
      { lsn: 1, key: 'winner', value: { picked: 'high-id' }, segmentId: -999 },
    ] },
    { segmentId: 2, closed: true, durableCount: 1, entries: [
      { lsn: 1, key: 'winner', value: { picked: 'low-id' }, segmentId: 900, extra: 'drop' },
    ] },
    { segmentId: 7, closed: false, durableCount: 1, entries: [
      { lsn: 4, key: 'last', value: [4] }, { lsn: 5, key: 'tail', value: 50 },
    ] },
    { segmentId: 4, closed: true, durableCount: 2, entries: [
      { lsn: 3, key: 'winner', value: { picked: 'overwrite' }, extra: true },
      { lsn: 2, key: 'second', value: false },
    ] },
    { segmentId: 1, closed: true, entries: [
      { lsn: 1, key: 'notDurable', value: 'missing-count' }, { lsn: 5, key: 'notDurable', value: 'gap-filler' },
    ] },
    { segmentId: 12, closed: false, durableCount: 0, entries: [] },
  ] };
  const expected = {
    state: { winner: { picked: 'overwrite' }, second: false, last: [4] },
    replayed: [
      { segmentId: 2, lsn: 1, key: 'winner', value: { picked: 'low-id' } },
      { segmentId: 4, lsn: 2, key: 'second', value: false },
      { segmentId: 4, lsn: 3, key: 'winner', value: { picked: 'overwrite' } },
      { segmentId: 7, lsn: 4, key: 'last', value: [4] },
    ],
    stats: { segmentsScanned: 6, replayedEntries: 4, lastLsn: 4 },
  };
  const rng = random(0x51ac);
  for (let i = 0; i < 20; i += 1) {
    const variant = { segments: shuffle(snapshot.segments, rng).map(segment => ({
      ...segment,
      entries: [
        ...shuffle(segment.entries.slice(0, segment.durableCount ?? 0), rng),
        ...segment.entries.slice(segment.durableCount ?? 0),
      ],
    })) };
    const before = structuredClone(variant);
    assert.deepEqual(recoverEngine(freezeDeep(variant)), expected, `permutation ${i}`);
    assert.deepEqual(variant, before, 'recovery cannot change any caller-owned snapshot data');
  }
});

test('hidden WAL recovery boundaries: absent LSN one and omitted durability replay nothing', () => {
  for (const snapshot of [
    { segments: [] },
    { segments: [{ segmentId: 4, closed: false, durableCount: 2, entries: [
      { lsn: 2, key: 'x', value: 1 }, { lsn: 3, key: 'x', value: 2 },
    ] }] },
    { segments: [{ segmentId: 1, closed: false, entries: [{ lsn: 1, key: 'x', value: 1 }] }] },
    { segments: [{ segmentId: 1, closed: true, durableCount: 0, entries: [{ lsn: 1, key: 'x', value: 1 }] }] },
  ]) {
    assert.deepEqual(recoverEngine(snapshot), {
      state: {}, replayed: [], stats: { segmentsScanned: snapshot.segments.length, replayedEntries: 0, lastLsn: 0 },
    });
  }
});

test('hidden WAL recovery ownership: repeated calls and state/replay values never share mutable storage', () => {
  const shared = { layers: [{ n: 1, tags: ['original'] }] };
  const snapshot = { segments: [{ segmentId: 3, closed: true, durableCount: 2, entries: [
    { lsn: 1, key: 'a', value: shared }, { lsn: 2, key: 'b', value: shared },
  ] }] };
  const original = structuredClone(snapshot);
  const expected = oracle(snapshot);
  const first = recoverEngine(snapshot);
  const second = recoverEngine(snapshot);
  assert.deepEqual(first, expected);
  assert.deepEqual(second, expected);
  first.state.a.layers[0].n = 101;
  first.replayed[0].value.layers[0].tags.push('first-replay');
  first.stats.lastLsn = 800;
  first.replayed[0].segmentId = 900;
  assert.deepEqual(first.state.b, shared);
  assert.deepEqual(first.replayed[1].value, shared);
  assert.equal(first.replayed[0].value.layers[0].n, 1, 'state and replay values are independent');
  assert.deepEqual(first.state.a.layers[0].tags, ['original']);
  assert.deepEqual(second, expected);
  assert.deepEqual(snapshot, original);
  assert.deepEqual(recoverEngine(snapshot), expected);
  shared.layers[0].n = 202;
  shared.layers[0].tags.push('input-later');
  assert.deepEqual(second, expected, 'old results do not follow subsequent input mutation');
  assert.equal(first.state.b.layers[0].n, 1);
  assert.equal(first.replayed[1].value.layers[0].n, 1);
  assert.deepEqual(recoverEngine(snapshot).state, { a: shared, b: shared });
});

test('hidden WAL differential recovery: seeded durable prefixes match a sorted-group oracle', () => {
  const keys = ['a', 'b', 'c', '__proto__', 'constructor'];
  for (let seed = 1; seed <= 96; seed += 1) {
    const rng = random(seed * 919);
    const limit = 10 + Math.floor(rng() * 32);
    const count = 3 + Math.floor(rng() * 12);
    const segments = [];
    for (let s = 0; s < count; s += 1) {
      const lsns = shuffle(Array.from({ length: limit }, (_, i) => i + 1), rng)
        .slice(0, 3 + Math.floor(rng() * (limit - 2)));
      const entries = lsns.map(lsn => ({
        lsn, key: keys[Math.floor(rng() * keys.length)],
        value: { seed, source: s, lsn, nested: [null, { flag: rng() < 0.5, text: `v${lsn}` }] },
        segmentId: 10000 - s, metadata: 'not replayed',
      }));
      const segment = { segmentId: s + 1, closed: rng() < 0.5, entries };
      if (rng() >= 0.2) segment.durableCount = Math.floor(rng() * (entries.length + 1));
      segments.push(segment);
    }
    const snapshot = { segments: shuffle(segments, rng) };
    const before = structuredClone(snapshot);
    const expected = oracle(snapshot);
    assert.deepEqual(recoverEngine(snapshot), expected, `seed ${seed}`);
    assert.deepEqual(snapshot, before, `seed ${seed} must not mutate input`);
    const reordered = { segments: shuffle(segments, rng).map(segment => ({
      ...segment,
      entries: [
        ...shuffle(segment.entries.slice(0, segment.durableCount ?? 0), rng),
        ...segment.entries.slice(segment.durableCount ?? 0),
      ],
    })) };
    assert.deepEqual(recoverEngine(reordered), expected, `seed ${seed} reordered`);
  }
});

test('hidden WAL moderate recovery: interleaved reversed segments produce all 48000 contiguous entries', { timeout: 30000 }, () => {
  const segmentCount = 192;
  const entriesPerSegment = 250;
  const total = segmentCount * entriesPerSegment;
  const segments = Array.from({ length: segmentCount }, (_, s) => ({
    segmentId: s + 1, closed: true, durableCount: entriesPerSegment,
    entries: Array.from({ length: entriesPerSegment }, (_, i) => {
      const lsn = i * segmentCount + s + 1;
      return { lsn, key: `bucket${lsn % 113}`, value: { lsn, pair: [lsn, null] } };
    }).reverse(),
  })).reverse();
  const started = performance.now();
  const result = recoverEngine({ segments });
  const elapsed = performance.now() - started;
  assert.deepEqual(result.stats, { segmentsScanned: segmentCount, replayedEntries: total, lastLsn: total });
  assert.equal(result.replayed.length, total);
  for (let i = 0; i < total; i += 1) {
    const lsn = i + 1;
    assert.deepEqual(result.replayed[i], {
      segmentId: i % segmentCount + 1, lsn, key: `bucket${lsn % 113}`, value: { lsn, pair: [lsn, null] },
    });
  }
  const expectedState = {};
  for (let lsn = 1; lsn <= total; lsn += 1) expectedState[`bucket${lsn % 113}`] = { lsn, pair: [lsn, null] };
  assert.deepEqual(result.state, expectedState);
  assert.ok(elapsed < 20000, `moderate recovery took ${Math.round(elapsed)}ms; allowance is deliberately 20 seconds`);
});
