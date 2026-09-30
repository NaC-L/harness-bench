'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { LRUCache } = require('../src/lru');

test('rejects invalid capacities', () => {
  for (const capacity of [undefined, null, 0, -1, 1.5, NaN, Infinity, -Infinity, '2', true, {}, 2n]) {
    assert.throws(() => new LRUCache(capacity), RangeError);
  }
});

test('updates refresh without growing or evicting unrelated entries', () => {
  const cache = new LRUCache(2);
  cache.set('a', 1).set('b', 2).set('a', 10);
  assert.equal(cache.size, 2);
  assert.equal(cache.has('b'), true);
  cache.set('c', 3);
  assert.equal(cache.has('b'), false);
  assert.equal(cache.get('a'), 10);
});

test('has, missing get, and deletion do not refresh remaining entries', () => {
  const cache = new LRUCache(3);
  cache.set('a', 1).set('b', 2).set('c', 3);
  assert.equal(cache.has('a'), true);
  assert.equal(cache.get('missing'), undefined);
  assert.equal(cache.delete('missing'), false);
  assert.equal(cache.delete('b'), true);
  cache.set('d', 4).set('e', 5);
  assert.equal(cache.has('a'), false);
  assert.equal(cache.has('c'), true);
  assert.equal(cache.size, 3);
});

test('undefined is a stored value and successful get still refreshes it', () => {
  const cache = new LRUCache(2);
  cache.set('a', undefined).set('b', null);
  assert.equal(cache.get('a'), undefined);
  assert.equal(cache.has('a'), true);
  cache.set('c', false);
  assert.equal(cache.has('b'), false);
  assert.equal(cache.has('a'), true);
  assert.equal(cache.delete('a'), true);
});

test('Map key semantics support identities, NaN, undefined, and symbols', () => {
  const cache = new LRUCache(6);
  const first = {};
  const second = {};
  const symbol = Symbol('key');
  cache.set(first, 'first').set(second, 'second').set(NaN, 'nan')
    .set(undefined, 'undefined').set(symbol, 'symbol').set(-0, 'zero');
  assert.equal(cache.get(first), 'first');
  assert.equal(cache.get(second), 'second');
  assert.equal(cache.get({}), undefined);
  assert.equal(cache.get(NaN), 'nan');
  assert.equal(cache.get(undefined), 'undefined');
  assert.equal(cache.get(symbol), 'symbol');
  assert.equal(cache.get(0), 'zero');
  cache.set(+0, 'updated');
  assert.equal(cache.size, 6);
  assert.equal(cache.get(-0), 'updated');
  cache.set('__proto__', 'ordinary key');
  assert.equal(cache.has(first), false);
  assert.equal(cache.get('__proto__'), 'ordinary key');
});

test('capacity one and independent caches', () => {
  const a = new LRUCache(1);
  const b = new LRUCache(1);
  a.set('x', 1).set('x', 2);
  b.set('x', 3);
  assert.equal(a.get('x'), 2);
  assert.equal(b.get('x'), 3);
  a.set('y', 4);
  assert.equal(a.has('x'), false);
  assert.equal(a.size, 1);
  assert.equal(b.get('x'), 3);
});
