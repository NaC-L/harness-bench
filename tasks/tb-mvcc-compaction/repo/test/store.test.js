'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { makeStore } = require('../src');

test('mvcc visible: compaction cannot replace published state with a prepared update', () => {
  const store = makeStore();
  assert.equal(store.put('invoice', { total: 41 }), 1);
  const update = store.prepare([{ type: 'put', key: 'invoice', value: { total: 42 } }]);
  assert.deepEqual(store.get('invoice'), { total: 41 });
  store.compact();
  assert.deepEqual(store.get('invoice'), { total: 41 });
  assert.equal(store.versionCount(), 2);
  assert.equal(store.publish(update), 2);
  assert.deepEqual(store.get('invoice'), { total: 42 });
  assert.equal(store.compact(), 1);
  assert.equal(store.versionCount(), 1);
});

test('mvcc visible: ordinary overwrite delete and independent key reads remain correct', () => {
  const store = makeStore();
  assert.equal(store.put('a', 1), 1);
  assert.equal(store.put('a', 2), 2);
  assert.equal(store.put('b', false), 3);
  assert.equal(store.get('a'), 2);
  assert.equal(store.delete('a'), 4);
  assert.equal(store.get('a'), undefined);
  assert.equal(store.get('b'), false);
  assert.equal(store.get('absent'), undefined);
  store.compact();
  assert.equal(store.get('a'), undefined);
  assert.equal(store.get('b'), false);
  assert.equal(store.put('a', null), 5);
  assert.equal(store.get('a'), null);
});
