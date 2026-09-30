'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { evaluate, ExprError } = require('../src/index');

function assertColumn(source, column, variables) {
  assert.throws(
    () => evaluate(source, variables),
    error => error instanceof ExprError && error.column === column,
    `${JSON.stringify(source)} should fail at column ${column}`,
  );
}

test('syntax errors report the column of the offending token after whitespace', () => {
  assertColumn('1 + $', 5);
  assertColumn('   @', 4);
  assertColumn('1 2', 3);
  assertColumn('  )', 3);
  assertColumn('1 + )', 5);
  assertColumn('1 ** ** 2', 6);
  assertColumn('min(1 2)', 7);
  assertColumn('1 +\t\t*', 6);
  assertColumn('(1 + 2)  3', 10);
  assertColumn('max(1,  )', 9);
});

test('unexpected end of input reports length plus one', () => {
  assertColumn('', 1);
  assertColumn('   ', 4);
  assertColumn('1 +', 4);
  assertColumn('1 +   ', 7);
  assertColumn('(1 + 2', 7);
  assertColumn('abs(', 5);
});

test('call and variable errors point at the identifier', () => {
  assertColumn('max()', 1);
  assertColumn('abs(1, 2)', 1);
  assertColumn('  foo(1)', 3);
  assertColumn('1 + sqrt(4)', 5);
  assertColumn('a + missing', 5, { a: 1 });
  assertColumn('  missing', 3);
  assertColumn('2x', 2);
});

test('inherited properties are not variables', () => {
  assertColumn('1 + toString', 5, {});
  assertColumn('x +  y', 6, Object.assign(Object.create({ y: 2 }), { x: 1 }));
});
