'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { makeStore } = require('../src');

test('mvcc hidden snapshots: equal-sequence handles have independent lifetimes and zero is valid', () => {
  const store = makeStore();
  const zero = store.snapshot();
  store.put('k', 1);
  const first = store.snapshot();
  const twin = store.snapshot();
  store.put('k', 2);
  const middle = store.snapshot();
  store.put('k', 3);
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 3);
  assert.equal(store.get('k', zero), undefined);
  assert.equal(store.get('k', first), 1);
  assert.equal(store.get('k', twin), 1);
  assert.equal(store.get('k', middle), 2);
  assert.equal(store.releaseSnapshot(first), undefined);
  assert.equal(store.compact(), 0);
  assert.equal(store.get('k', twin), 1);
  store.releaseSnapshot(twin);
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 2);
  assert.equal(store.get('k', middle), 2);
  store.releaseSnapshot(middle);
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 1);
  assert.equal(store.get('k', zero), undefined);
  store.releaseSnapshot(zero);
  assert.equal(store.compact(), 0);
});

test('mvcc hidden snapshots: sparse read points retain their own predecessors, not an interval', () => {
  const store = makeStore();
  const snapshots = [];
  for (let value = 1; value <= 9; value++) {
    store.put('k', value);
    if ([1, 4, 7].includes(value)) snapshots.push(store.snapshot());
  }
  assert.equal(store.compact(), 5);
  assert.equal(store.versionCount(), 4);
  assert.deepEqual(snapshots.map(token => store.get('k', token)), [1, 4, 7]);
  assert.equal(store.get('k'), 9);
  assert.equal(store.compact(), 0);
  store.releaseSnapshot(snapshots[1]);
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 3);
  assert.equal(store.get('k', snapshots[2]), 7);
  store.releaseSnapshot(snapshots[0]);
  store.releaseSnapshot(snapshots[2]);
  assert.equal(store.compact(), 2);
  assert.equal(store.versionCount(), 1);
});

test('mvcc hidden snapshots: tombstones at snapshot and latest bounds prevent resurrection', () => {
  const store = makeStore();
  store.put('k', 'old');
  const old = store.snapshot();
  store.delete('k');
  const deleted = store.snapshot();
  store.put('k', 'middle');
  store.delete('k');
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 3);
  assert.equal(store.get('k'), undefined);
  assert.equal(store.get('k', old), 'old');
  assert.equal(store.get('k', deleted), undefined);
  assert.equal(store.compact(), 0);
  store.releaseSnapshot(old);
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 2);
  assert.equal(store.get('k', deleted), undefined);
  store.releaseSnapshot(deleted);
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 1);
  assert.equal(store.get('k'), undefined);
  store.put('k', 'reborn');
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 1);
  assert.equal(store.get('k'), 'reborn');
});

test('mvcc hidden snapshots: per-key predecessors and future tombstones coexist during compaction', () => {
  const store = makeStore();
  store.put('a', 1);
  const early = store.snapshot();
  store.put('b', 2);
  store.put('a', 3);
  const middle = store.snapshot();
  store.delete('b');
  store.put('a', 5);
  const pending = store.prepare([
    { type: 'delete', key: 'a' },
    { type: 'put', key: 'b', value: 7 },
  ]);
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 7);
  assert.equal(store.get('a'), 5);
  assert.equal(store.get('b'), undefined);
  assert.equal(store.get('a', early), 1);
  assert.equal(store.get('b', early), undefined);
  assert.equal(store.get('a', middle), 3);
  assert.equal(store.get('b', middle), 2);
  assert.equal(store.publish(pending), 7);
  assert.equal(store.compact(), 2);
  assert.equal(store.versionCount(), 5);
  assert.equal(store.get('a'), undefined);
  assert.equal(store.get('b'), 7);
  assert.equal(store.get('a', early), 1);
  assert.equal(store.get('b', middle), 2);
  store.releaseSnapshot(early);
  store.releaseSnapshot(middle);
  assert.equal(store.compact(), 3);
  assert.equal(store.versionCount(), 2);
});

test('mvcc hidden snapshots: released foreign and fabricated snapshot tokens throw TypeError', () => {
  const store = makeStore();
  const other = makeStore();
  store.put('k', 'value');
  const token = store.snapshot();
  assert.equal(store.get('k', undefined), 'value');
  store.releaseSnapshot(token);
  assert.throws(() => store.get('k', token), TypeError);
  assert.throws(() => store.releaseSnapshot(token), TypeError);
  assert.throws(() => store.get('k', other.snapshot()), TypeError);
  assert.throws(() => store.get('missing', {}), TypeError);
  assert.throws(() => store.releaseSnapshot({}), TypeError);
  const batch = store.prepare([{ type: 'delete', key: 'k' }]);
  assert.throws(() => other.publish(batch), TypeError);
  assert.throws(() => store.publish({}), TypeError);
  assert.throws(() => store.publish(token), TypeError);
  assert.equal(store.publish(batch), 2);
});
