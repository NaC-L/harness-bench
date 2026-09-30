'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { evaluate, ExprError } = require('../src/index');

function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

/** Python integer floor division/modulo via exact BigInt arithmetic. */
function pythonDivmod(a, b) {
  const x = BigInt(a);
  const y = BigInt(b);
  let quotient = x / y;
  if (x % y !== 0n && (x < 0n) !== (y < 0n)) quotient -= 1n;
  return [Number(quotient), Number(x - quotient * y)];
}

test('randomized floored division and modulo match Python integers', () => {
  for (const seed of [7, 1234, 98765]) {
    const random = mulberry32(seed);
    const int = (low, high) => low + Math.floor(random() * (high - low + 1));
    for (let op = 0; op < 1500; op += 1) {
      const wide = op % 3 === 0;
      const a = wide ? int(-1e9, 1e9) : int(-40, 40);
      let b = wide ? int(-1e6, 1e6) : int(-12, 12);
      if (b === 0) b = op % 2 ? 1 : -1;
      const [quotient, remainder] = pythonDivmod(a, b);
      const label = `seed ${seed}, op ${op}: a=${a}, b=${b}`;
      assert.equal(evaluate(`${a} // ${b}`), quotient, `literal // for ${label}`);
      assert.equal(evaluate(`${a} % ${b}`), remainder, `literal % for ${label}`);
      assert.equal(evaluate('a // b', { a, b }), quotient, `variable // for ${label}`);
      assert.equal(evaluate('a % b', { a, b }), remainder, `variable % for ${label}`);
      assert.equal(evaluate('(a // b) * b + a % b', { a, b }), a, `identity for ${label}`);
    }
  }
});

test('floored operators return positive zero and handle decimals', () => {
  assert.ok(Object.is(evaluate('-4 % 2'), 0));
  assert.ok(Object.is(evaluate('0 // -3'), 0));
  assert.ok(Object.is(evaluate('6 % -3'), 0));
  assert.equal(evaluate('-1 // 5'), -1);
  assert.equal(evaluate('1 // -5'), -1);
  assert.equal(evaluate('-1 % 5'), 4);
  assert.equal(evaluate('5.5 % -2'), -0.5);
  assert.equal(evaluate('-7.5 // 2'), -4);
  assert.equal(evaluate('-7.5 % 2'), 0.5);
  assert.equal(evaluate('7.5 % 2'), 1.5);
  assert.equal(evaluate('-0.5 // 1'), -1);
});

test('floored operators combine with power and unary precedence', () => {
  assert.equal(evaluate('-2 ** 3 // 3'), -3);
  assert.equal(evaluate('-7 // 2 ** 1'), -4);
  assert.equal(evaluate('2 ** 3 % -5'), -2);
  assert.equal(evaluate('-a % b', { a: 7, b: 3 }), 2);
  assert.equal(evaluate('min(-7 // 2, 7 // -2)'), -4);
});

test('division by zero raises at the operator column', () => {
  const cases = [
    ['1 / 0', 3],
    ['1 // 0', 3],
    ['10 %  0', 4],
    ['  8 // 0.0', 5],
    ['1 + 2 / -0', 7],
    ['x % (y - y)', 3, { x: 4, y: 2 }],
    ['(1)//(0)', 4],
    ['4   /   (2 - 2)', 5],
  ];
  for (const [source, column, variables] of cases) {
    assert.throws(
      () => evaluate(source, variables),
      error => error instanceof ExprError && error.column === column,
      `${JSON.stringify(source)} should fail at column ${column}`,
    );
  }
});
