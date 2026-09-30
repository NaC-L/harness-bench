'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { RangeTree } = require('../src/range-tree');

function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6D2B79F5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function oracleSum(values, l, r) {
  let sum = 0;
  for (let i = l; i < r; i++) sum += values[i];
  return sum;
}

function oracleMax(values, l, r) {
  let maximum = -Infinity;
  for (let i = l; i < r; i++) maximum = Math.max(maximum, values[i]);
  return maximum;
}

function oracleFirst(values, lo, x) {
  for (let i = lo; i < values.length; i++) {
    if (values[i] >= x) return i;
  }
  return -1;
}

test('hidden: assignments discard older deltas at nested lazy nodes', () => {
  const tree = new RangeTree(Array(16).fill(2));
  tree.add(0, 8, 11);
  tree.add(8, 16, -7);
  tree.assign(0, 16, -4);
  tree.add(4, 12, 6);
  tree.assign(6, 14, -3);
  assert.deepEqual(tree.toArray(), [-4, -4, -4, -4, 2, 2, -3, -3, -3, -3, -3, -3, -3, -3, -4, -4]);
  assert.equal(tree.sum(3, 16), -32);
});

test('hidden: threshold descent observes unpushed assignments and additions', () => {
  const assigned = new RangeTree([-8, -8, -8, -8, -8, -8, -8, -8]);
  assigned.assign(0, 8, 12);
  assert.equal(assigned.firstAtLeast(0, 12), 0);
  assert.equal(assigned.firstAtLeast(3, 12), 3);
  assert.equal(assigned.firstAtLeast(7, 12), 7);
  assert.equal(assigned.firstAtLeast(0, 13), -1);

  const added = new RangeTree([2, 2, 2, 2, 2, 2, 2, 2]);
  added.add(0, 8, 9);
  assert.equal(added.firstAtLeast(1, 11), 1);
  assert.equal(added.firstAtLeast(6, 11), 6);
  const lowered = new RangeTree([20, 20, -10, -10, -10, -10, -10, -10]);
  lowered.assign(0, 4, -6);
  assert.equal(lowered.firstAtLeast(0, 0), -1);
});

test('hidden: partial maxima preserve negative values instead of zero', () => {
  const tree = new RangeTree([-11, -7, -20, -3, -13, -8, -2]);
  assert.equal(tree.max(1, 3), -7);
  assert.equal(tree.max(3, 7), -2);
  assert.equal(tree.max(0, 1), -11);
  tree.assign(0, 7, -17);
  assert.equal(tree.max(2, 6), -17);
  tree.add(3, 7, 2);
  assert.equal(tree.max(1, 7), -15);
});

test('hidden: right-edge and empty suffix semantics survive pending updates', () => {
  const tree = new RangeTree([-3, -3, -3, -3, -3]);
  tree.assign(0, 5, 7);
  tree.add(2, 5, 4);
  assert.equal(tree.sum(2, 5), 33);
  assert.equal(tree.max(4, 5), 11);
  assert.equal(tree.get(4), 11);
  assert.equal(tree.firstAtLeast(4, 10), 4);
  assert.equal(tree.firstAtLeast(5, -Infinity), -1);
  for (let i = 0; i <= 5; i++) {
    tree.assign(i, i, -50);
    tree.add(i, i, 300);
    assert.equal(tree.sum(i, i), 0);
    assert.equal(tree.max(i, i), -Infinity);
  }
  assert.deepEqual(tree.toArray(), [7, 7, 11, 11, 11]);
});

test('trap: constructors reject nonarrays empty arrays holes and nonfinite values', () => {
  for (const values of [null, undefined, {}, new Float64Array([1]), [], new Array(3),
    [1, NaN], [Infinity], [-Infinity], ['1'], [null]]) {
    assert.throws(() => new RangeTree(values), RangeError);
  }
  assert.deepEqual(new RangeTree([0, -2.5, 4.25]).toArray(), [0, -2.5, 4.25]);
});

test('trap: invalid ranges and operands fail atomically with RangeError', () => {
  const tree = new RangeTree([2, 4, 6, 8]);
  for (const [l, r] of [[-1, 1], [0, 5], [3, 2], [0.5, 2], [0, 2.5],
    [NaN, 1], [0, Infinity], ['0', 1], [0, null]]) {
    for (const method of ['sum', 'max', 'assign', 'add']) {
      assert.throws(() => tree[method](l, r, 9), RangeError);
    }
  }
  for (const value of [NaN, Infinity, -Infinity, undefined, null, '3']) {
    assert.throws(() => tree.assign(0, 4, value), RangeError);
    assert.throws(() => tree.add(0, 4, value), RangeError);
    assert.throws(() => tree.assign(4, 4, value), RangeError);
    assert.throws(() => tree.add(0, 0, value), RangeError);
  }
  assert.deepEqual(tree.toArray(), [2, 4, 6, 8]);
});

test('trap: invalid indices and search arguments retain stored values', () => {
  const tree = new RangeTree([2, 4, 6, 8]);
  for (const index of [-1, 4, 0.5, NaN, Infinity, '1', null]) {
    assert.throws(() => tree.get(index), RangeError);
  }
  for (const lo of [-1, 5, 0.5, NaN, Infinity, '1', null]) {
    assert.throws(() => tree.firstAtLeast(lo, 3), RangeError);
  }
  for (const threshold of [NaN, undefined, null, '3']) {
    assert.throws(() => tree.firstAtLeast(0, threshold), RangeError);
  }
  assert.equal(tree.firstAtLeast(4, -Infinity), -1);
  assert.equal(tree.firstAtLeast(0, Infinity), -1);
  assert.equal(tree.firstAtLeast(2, -Infinity), 2);
  assert.deepEqual(tree.toArray(), [2, 4, 6, 8]);
});

test('trap: constructor and materialized arrays are independent copies', () => {
  const input = [3, 6, 9, 12];
  const tree = new RangeTree(input);
  input[0] = 99;
  input.push(77);
  const materialized = tree.toArray();
  materialized[1] = -100;
  materialized.pop();
  assert.equal(tree.length, 4);
  assert.throws(() => { tree.length = 1; }, TypeError);
  tree.add(0, 4, 2);
  assert.deepEqual(tree.toArray(), [5, 8, 11, 14]);
  assert.equal(tree.sum(0, 4), 38);
  assert.equal(tree.get(3), 14);
  assert.deepEqual(input, [99, 6, 9, 12, 77]);
});

test('trap: singleton updates and empty boundaries preserve the API', () => {
  const tree = new RangeTree([-5]);
  assert.equal(tree.assign(0, 1, -3), undefined);
  assert.equal(tree.add(0, 1, 2), undefined);
  assert.equal(tree.assign(0, 1, -8), undefined);
  assert.equal(tree.add(0, 1, 0.5), undefined);
  tree.assign(1, 1, 50);
  tree.add(0, 0, 90);
  assert.equal(tree.get(0), -7.5);
  assert.equal(tree.sum(0, 1), -7.5);
  assert.equal(tree.max(0, 1), -7.5);
  assert.equal(tree.sum(1, 1), 0);
  assert.equal(tree.max(0, 0), -Infinity);
  assert.equal(tree.firstAtLeast(0, -7.5), 0);
  assert.equal(tree.firstAtLeast(0, -7), -1);
  assert.equal(tree.firstAtLeast(1, -Infinity), -1);
  assert.deepEqual(tree.toArray(), [-7.5]);
});

test('trap: overlapping additions retain positive range aggregates', () => {
  const tree = new RangeTree([3, 4, 5, 6, 7, 8, 9]);
  tree.add(0, 7, 2);
  tree.add(1, 6, 3);
  tree.add(4, 7, -1);
  assert.equal(tree.sum(2, 7), 54);
  assert.equal(tree.max(1, 7), 12);
  assert.deepEqual(tree.toArray(), [5, 9, 10, 11, 11, 12, 10]);
});

test('trap: threshold search returns the earliest qualifying suffix index', () => {
  const tree = new RangeTree([2, 9, 1, 9, 3]);
  assert.equal(tree.firstAtLeast(0, 9), 1);
  assert.equal(tree.firstAtLeast(2, 9), 3);
  assert.equal(tree.firstAtLeast(3, 9), 3);
  assert.equal(tree.firstAtLeast(4, 9), -1);
  assert.equal(tree.firstAtLeast(0, -Infinity), 0);
  assert.equal(tree.firstAtLeast(5, -Infinity), -1);
});

const cases = [
  [0x10203040, 1], [0x31415926, 2], [0xA11CE55, 3], [0xDEADBEEF, 7],
  [0xC001CAFE, 16], [0xBADC0DE, 31], [0x98765432, 63], [0xF00DBABE, 64],
];
for (const [seed, n] of cases) {
  test(`hidden: seeded differential operations seed=${seed} n=${n}`, () => {
    const random = mulberry32(seed);
    const integer = (bound) => Math.floor(random() * bound);
    const values = Array.from({ length: n }, () => integer(81) - 40);
    const tree = new RangeTree(values);
    for (let op = 0; op < 2500; op++) {
      let l = integer(n + 1);
      let r = integer(n + 1);
      if (l > r) [l, r] = [r, l];
      if (op % 11 === 0) { l = 0; r = n; }
      const message = `seed=${seed} op=${op} n=${n} range=[${l},${r})`;
      switch (integer(8)) {
        case 0: {
          const value = integer(81) - 40;
          tree.assign(l, r, value);
          for (let i = l; i < r; i++) values[i] = value;
          break;
        }
        case 1: {
          const value = integer(21) - 10;
          tree.add(l, r, value);
          for (let i = l; i < r; i++) values[i] += value;
          break;
        }
        case 2:
          assert.equal(tree.sum(l, r), oracleSum(values, l, r), message);
          break;
        case 3:
          assert.equal(tree.max(l, r), oracleMax(values, l, r), message);
          break;
        case 4: {
          const lo = integer(n + 1);
          const x = op % 17 === 0 ? -Infinity : op % 19 === 0 ? Infinity : integer(101) - 50;
          assert.equal(tree.firstAtLeast(lo, x), oracleFirst(values, lo, x), `${message} lo=${lo} x=${x}`);
          break;
        }
        case 5: {
          const index = integer(n);
          assert.equal(tree.get(index), values[index], `${message} index=${index}`);
          break;
        }
        case 6:
          assert.deepEqual(tree.toArray(), values, message);
          break;
        case 7:
          assert.equal(tree.sum(0, n), oracleSum(values, 0, n), message);
          assert.equal(tree.firstAtLeast(l, 0), oracleFirst(values, l, 0), message);
          break;
      }
      assert.equal(tree.length, n, message);
    }
  });
}
