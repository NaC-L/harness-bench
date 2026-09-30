'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { evaluate, ExprError } = require('../src/index');

// Cumulative budget for the evaluate() calls of each scale test (formula
// construction is not timed). It is checked after every size, and sizes double,
// so quadratic token/AST handling exceeds it partway through and fails in
// seconds instead of running the largest formulas.
const SCALE_BUDGET_MS = 5000;
const SIZES = [10000, 20000, 40000, 80000, 160000];

function runScaled(label, build) {
  let elapsed = 0;
  for (const size of SIZES) {
    const run = build(size);
    const started = performance.now();
    run();
    elapsed += performance.now() - started;
    assert.ok(
      elapsed < SCALE_BUDGET_MS,
      `${label}: ${Math.round(elapsed)} ms spent by size ${size} (budget ${SCALE_BUDGET_MS} ms)`,
    );
  }
}

test('trap: basic precedence and left associativity', () => {
  const rows = [
    ['1 + 2 * 3', 7],
    ['(1 + 2) * 3', 9],
    ['10 - 4 - 3', 3],
    ['100 / 10 / 5', 2],
    ['2 * 3 + 4 * 5', 26],
    ['7 - -3', 10],
    ['+5', 5],
    ['8 / 4 * 2', 4],
    ['9 / 2', 4.5],
    ['7 % 3 + 7 // 2', 4],
    ['2 ** 10', 1024],
    ['1 < 2', true],
    ['2 != 2', false],
    ['1 + 2 >= 3', true],
  ];
  for (const [source, expected] of rows) assert.equal(evaluate(source), expected, source);
});

test('trap: decimals and exponents', () => {
  const rows = [
    ['1.5e-3 * 2', 0.003],
    ['.5 + 5.', 5.5],
    ['2E3', 2000],
    ['1.25e+2', 125],
    ['0.1 + 0.2', 0.30000000000000004],
    ['3.0 // 2', 1],
  ];
  for (const [source, expected] of rows) assert.equal(evaluate(source), expected, source);
});

test('trap: built-in calls and variables', () => {
  assert.equal(evaluate('min(3, 1, 2)'), 1);
  assert.equal(evaluate('max(-1)'), -1);
  assert.equal(evaluate('abs(-2.5)'), 2.5);
  assert.equal(evaluate('max(1, min(4, 2) * 3)'), 6);
  assert.equal(evaluate('abs(x-y)', { x: 2, y: 9 }), 7);
  assert.equal(evaluate('rate*qty+fee', { rate: 1.5, qty: 4, fee: 0.25 }), 6.25);
  assert.equal(evaluate('(1)'), 1);
  assert.throws(() => evaluate('1/0'), error => error instanceof ExprError && error.column === 2);
  assert.throws(() => evaluate('1+'), error => error instanceof ExprError && error.column === 3);
});

test('trap: long flat arithmetic stays linear', () => {
  runScaled('flat sum', size => {
    let reads = 0;
    const variables = { get x() { reads += 1; return 1; } };
    const source = new Array(size).fill('x').join(' + ');
    return () => {
      assert.equal(evaluate(source, variables), size, `sum of ${size}`);
      assert.equal(reads, size, `reads for ${size}`);
    };
  });
});

test('long comparison chains stay linear and chain correctly', () => {
  runScaled('comparison chain', size => {
    const terms = [];
    for (let value = size; value >= 1; value -= 1) terms.push(`-${value}`);
    const source = terms.join(' < ');
    return () => assert.equal(evaluate(source), true, `ascending chain of ${size}`);
  });
  let reads = 0;
  const variables = { get v() { reads += 1; return 3; } };
  const source = new Array(50000).fill('v').join(' <= ') + ' > 3 < 9';
  assert.equal(evaluate(source, variables), false);
  assert.equal(reads, 50000);
});
