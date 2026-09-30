'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
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

test('hidden: large mixed workload retains logarithmic updates and queries', (t) => {
  const seed = 0x5E6A3E17;
  const random = mulberry32(seed);
  const integer = (bound) => Math.floor(random() * bound);
  const n = 200000;
  const half = n / 2;
  const operations = 200000;
  const budgetMs = 3000;
  const started = performance.now();
  const tree = new RangeTree(Array(n).fill(0));
  // Updates preserve two constant regions, giving an O(1) independent oracle.
  // Wide sums/maxima and unsuccessful searches force a scan-based rewrite to
  // touch billions of elements without making this oracle do the same work.
  let leftValue = 0;
  let rightValue = 0;
  for (let op = 0; op < operations; op++) {
    const message = `seed=${seed} op=${op}`;
    switch (op % 10) {
      case 0: {
        const value = integer(201) - 100;
        tree.assign(0, n, value);
        leftValue = rightValue = value;
        break;
      }
      case 1: {
        const value = integer(21) - 10;
        tree.add(0, n, value);
        leftValue += value;
        rightValue += value;
        break;
      }
      case 2:
        leftValue = integer(201) - 100;
        tree.assign(0, half, leftValue);
        break;
      case 3: {
        const value = integer(21) - 10;
        tree.add(half, n, value);
        rightValue += value;
        break;
      }
      case 4: {
        const kind = integer(3);
        const l = kind === 2 ? half : 0;
        const r = kind === 1 ? half : n;
        const expected = (l === 0 ? half * leftValue : 0) + (r === n ? half * rightValue : 0);
        assert.equal(tree.sum(l, r), expected, message);
        break;
      }
      case 5: {
        const kind = integer(3);
        const l = kind === 2 ? half : 0;
        const r = kind === 1 ? half : n;
        const expected = kind === 0 ? Math.max(leftValue, rightValue) : kind === 1 ? leftValue : rightValue;
        assert.equal(tree.max(l, r), expected, message);
        break;
      }
      case 6: {
        const lo = integer(n + 1);
        const x = integer(221) - 110;
        const expected = lo < half && leftValue >= x ? lo :
          lo < n && rightValue >= x ? Math.max(lo, half) : -1;
        assert.equal(tree.firstAtLeast(lo, x), expected, `${message} lo=${lo} x=${x}`);
        break;
      }
      case 7: {
        const index = integer(n);
        assert.equal(tree.get(index), index < half ? leftValue : rightValue, message);
        break;
      }
      case 8:
        assert.equal(tree.sum(0, n), half * (leftValue + rightValue), message);
        break;
      case 9:
        assert.equal(tree.firstAtLeast(0, Math.max(leftValue, rightValue) + 1), -1, message);
        break;
    }
    if ((op + 1) % 1000 === 0) {
      assert.ok(performance.now() - started < budgetMs,
        `${message}: range operations exceeded ${budgetMs}ms; preserve O(log n)`);
    }
  }
  const elapsed = performance.now() - started;
  assert.ok(elapsed < budgetMs, `seed=${seed} op=${operations}: exceeded ${budgetMs}ms`);
  t.diagnostic(`seed=${seed} operations=${operations} elapsed_ms=${elapsed.toFixed(3)} budget_ms=${budgetMs}`);
  assert.equal(tree.length, n);
});
