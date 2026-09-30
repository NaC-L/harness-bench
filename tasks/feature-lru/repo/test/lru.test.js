'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { LRUCache } = require('../src/lru');

test('stores entries, chains sets, and reports size', () => {
  const cache = new LRUCache(2);
  assert.equal(cache.size, 0);
  assert.equal(cache.set('a', 1), cache);
  assert.equal(cache.get('a'), 1);
  assert.equal(cache.has('a'), true);
  assert.equal(cache.get('missing'), undefined);
  assert.equal(cache.size, 1);
});

test('get refreshes recency before eviction', () => {
  const cache = new LRUCache(2);
  cache.set('a', 1).set('b', 2);
  cache.get('a');
  cache.set('c', 3);
  assert.equal(cache.has('a'), true);
  assert.equal(cache.has('b'), false);
  assert.equal(cache.get('c'), 3);
  assert.equal(cache.size, 2);
});

test('delete reports whether a key existed', () => {
  const cache = new LRUCache(2);
  cache.set('a', 1);
  assert.equal(cache.delete('a'), true);
  assert.equal(cache.delete('a'), false);
  assert.equal(cache.size, 0);
});
