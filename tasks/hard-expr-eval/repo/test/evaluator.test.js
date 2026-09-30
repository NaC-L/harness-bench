'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { evaluate } = require('../src/index');

test('floor division and modulo follow Python for negative operands', () => {
  assert.equal(evaluate('-7 // 2'), -4);
  assert.equal(evaluate('-7 % 3'), 2);
  assert.equal(evaluate('7 % -3'), -2);
  assert.equal(evaluate('7 // 2'), 3);
});
