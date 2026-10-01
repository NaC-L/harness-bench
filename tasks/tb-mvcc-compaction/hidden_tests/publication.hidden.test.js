'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { makeStore } = require('../src');

test('mvcc hidden publication: an unpublished deletion retains the last committed value and tombstone', () => {
  const store = makeStore();
  store.put('record', 'old');
  const deletion = store.prepare([{ type: 'delete', key: 'record' }]);
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 2);
  assert.equal(store.get('record'), 'old');
  assert.equal(store.publish(deletion), 2);
  assert.equal(store.get('record'), undefined);
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 1);
  assert.equal(store.compact(), 0);
});

test('mvcc hidden publication: all installed versions survive above the frontier across keys', () => {
  const store = makeStore();
  store.put('x', 'committed');
  store.put('y', 'stable');
  const batch = store.prepare([
    { type: 'put', key: 'x', value: 'intermediate' },
    { type: 'put', key: 'x', value: 'final' },
    { type: 'delete', key: 'y' },
    { type: 'put', key: 'z', value: 0 },
  ]);
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 6);
  assert.equal(store.get('x'), 'committed');
  assert.equal(store.get('y'), 'stable');
  assert.equal(store.get('z'), undefined);
  assert.equal(store.publish(batch), 6);
  assert.equal(store.get('x'), 'final');
  assert.equal(store.get('y'), undefined);
  assert.equal(store.get('z'), 0);
  assert.equal(store.compact(), 3);
  assert.equal(store.versionCount(), 3);
  assert.equal(store.compact(), 0);
});

test('mvcc hidden publication: out-of-order readiness and ordinary writes cannot cross an unready batch', () => {
  const store = makeStore();
  store.put('k', 'A');
  const lower = store.prepare([{ type: 'put', key: 'k', value: 'B' }]);
  const higher = store.prepare([
    { type: 'put', key: 'k', value: 'C' },
    { type: 'put', key: 'y', value: 'new' },
  ]);
  assert.equal(store.put('k', 'D'), 5);
  assert.equal(store.delete('y'), 6);
  assert.equal(store.publish(higher), 1);
  assert.equal(store.publish(higher), 1);
  const snapshot = store.snapshot();
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 6);
  assert.equal(store.get('k'), 'A');
  assert.equal(store.get('y'), undefined);
  assert.equal(store.publish(lower), 6);
  assert.equal(store.publish(higher), 6);
  assert.equal(store.get('k'), 'D');
  assert.equal(store.get('y'), undefined);
  assert.equal(store.get('k', snapshot), 'A');
  assert.equal(store.compact(), 3);
  assert.equal(store.versionCount(), 3);
  assert.equal(store.get('k', snapshot), 'A');
  store.releaseSnapshot(snapshot);
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 2);
});

test('mvcc hidden publication: sequence zero snapshots see none of an installed first batch', () => {
  const store = makeStore();
  const first = store.prepare([
    { type: 'delete', key: 'ghost' },
    { type: 'put', key: 'x', value: 'future' },
  ]);
  assert.equal(store.put('y', 'also future'), 3);
  const zero = store.snapshot();
  assert.equal(store.get('x'), undefined);
  assert.equal(store.get('y'), undefined);
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 3);
  assert.equal(store.publish(first), 3);
  assert.equal(store.get('x'), 'future');
  assert.equal(store.get('y'), 'also future');
  assert.equal(store.get('x', zero), undefined);
  assert.equal(store.get('y', zero), undefined);
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 3);
});

test('mvcc hidden publication: repeated keys reserve distinct sequences and publish atomically', () => {
  const store = makeStore();
  const batch = store.prepare([
    { type: 'put', key: '', value: 1 },
    { type: 'delete', key: '' },
    { type: 'put', key: '', value: 3 },
  ]);
  assert.equal(store.get(''), undefined);
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 3);
  assert.equal(store.publish(batch), 3);
  assert.equal(store.get(''), 3);
  assert.equal(store.compact(), 2);
  assert.equal(store.versionCount(), 1);
});
