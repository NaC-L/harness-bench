'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { makeStore } = require('../src');

test('mvcc hidden ownership: ordinary and prepared JSON values detach on every write and read', () => {
  const store = makeStore();
  const input = { rows: [{ scores: [1, 2] }], flags: { active: true }, nullable: null };
  store.put('k', input);
  const original = store.snapshot();
  input.rows[0].scores.push(99);
  input.flags.active = false;
  const expectedOld = { rows: [{ scores: [1, 2] }], flags: { active: true }, nullable: null };
  assert.deepEqual(store.get('k'), expectedOld);
  const read = store.get('k');
  read.rows[0].scores[0] = 500;
  read.flags.active = false;
  assert.deepEqual(store.get('k'), expectedOld);
  const preparedValue = { list: [{ payload: { label: 'new' } }] };
  const batch = store.prepare([{ type: 'put', key: 'k', value: preparedValue }]);
  preparedValue.list[0].payload.label = 'mutated';
  preparedValue.list.push({ extra: true });
  assert.deepEqual(store.get('k'), expectedOld);
  store.publish(batch);
  const expectedNew = { list: [{ payload: { label: 'new' } }] };
  assert.deepEqual(store.get('k'), expectedNew);
  const historical = store.get('k', original);
  historical.rows[0].scores.pop();
  assert.deepEqual(store.get('k', original), expectedOld);
  const current = store.get('k');
  current.list[0].payload.label = 'read mutation';
  assert.equal(store.compact(), 0);
  assert.deepEqual(store.get('k'), expectedNew);
  assert.deepEqual(store.get('k', original), expectedOld);
  store.releaseSnapshot(original);
  assert.equal(store.compact(), 1);
  assert.deepEqual(store.get('k'), expectedNew);
});

test('mvcc hidden ownership: keys and falsy JSON data do not share state between stores', () => {
  const store = makeStore();
  const other = makeStore();
  const entries = [['', null], ['__proto__', false], ['constructor', 0], ['toString', '']];
  for (const [key, value] of entries) store.put(key, value);
  for (const [key, value] of entries) {
    assert.equal(store.get(key), value);
    assert.equal(other.get(key), undefined);
  }
  other.put('', 'separate');
  assert.equal(store.get(''), null);
  assert.equal(other.get(''), 'separate');
  assert.equal(store.compact(), 0);
  assert.equal(store.versionCount(), 4);
});
