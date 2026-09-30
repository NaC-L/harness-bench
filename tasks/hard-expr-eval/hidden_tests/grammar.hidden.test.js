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

function checkTable(rows) {
  for (const [source, expected, variables] of rows) {
    assert.equal(evaluate(source, variables), expected, `evaluate(${JSON.stringify(source)})`);
  }
}

/** Variables object whose getters log every read, in order. */
function recording(values) {
  const reads = [];
  const variables = {};
  for (const [name, value] of Object.entries(values)) {
    Object.defineProperty(variables, name, {
      enumerable: true,
      get() {
        reads.push(name);
        return value;
      },
    });
  }
  return { variables, reads };
}

test('power is right-associative', () => {
  checkTable([
    ['2 ** 3 ** 2', 512],
    ['2 ** 3 ** 0', 2],
    ['(2 ** 3) ** 2', 64],
    ['2 ** 2 ** 3 // 7', 36],
    ['10 - 2 ** 3 ** 2 // 100', 5],
    ['4 ** 0.5 ** 2', 4 ** 0.25],
    ['3 ** 1 ** 4 ** 2', 3],
    ['2**2**2**2', 65536],
  ]);
});

test('unary minus binds looser than power on its left', () => {
  checkTable([
    ['-2 ** 2', -4],
    ['- 2 ** 2', -4],
    ['-3 ** 2', -9],
    ['+-3 ** 2', -9],
    ['--2 ** 2', 4],
    ['3 * -2 ** 2', -12],
    ['1 - -2 ** 2', 5],
    ['(-2) ** 2', 4],
    ['-x ** 2', -9, { x: 3 }],
    ['-abs(-3) ** 2', -9],
    ['-(2) ** 2', -4],
  ]);
});

test('power accepts a signed right operand', () => {
  checkTable([
    ['2 ** -1', 0.5],
    ['2 ** -2', 0.25],
    ['-2 ** -2', -0.25],
    ['2 ** -1 ** 2', 0.5],
    ['2 ** - 2 ** 2', 0.0625],
    ['2 ** +3', 8],
    ['10 ** -x * 4', 0.04, { x: 2 }],
    ['2 ** -1 * 8', 4],
  ]);
});

test('comparison operators chain instead of comparing booleans', () => {
  checkTable([
    ['1 < 2 < 3', true],
    ['3 > 2 > 1', true],
    ['1 < 3 < 2', false],
    ['-3 < -2 < -1', true],
    ['2 == 2 == 2', true],
    ['0 < 0 == 0', false],
    ['5 >= 5 > 4 >= 4', true],
    ['1 < 2 == 1', false],
    ['1 + 1 == 2 < 3', true],
    ['1 != 2 != 1', true],
    ['3 <= 3 < 3', false],
    ['4 > 3 < 5 > 0', true],
  ]);
});

test('trap: parenthesized comparisons behave as 0/1 numbers', () => {
  checkTable([
    ['(1 < 2) < 2', true],
    ['(3 > 2) > 1', false],
    ['(1 < 2) + (2 < 3)', 2],
    ['(2 == 2) == 1', true],
    ['-(5 > 4)', -1],
  ]);
});

test('trap: chained comparison reads each shared operand exactly once', () => {
  const inside = recording({ x: 2 });
  assert.equal(evaluate('1 < x < 3', inside.variables), true);
  assert.deepEqual(inside.reads, ['x']);

  const all = recording({ a: 1, b: 2, c: 3, d: 4 });
  assert.equal(evaluate('a < b <= c < d', all.variables), true);
  assert.deepEqual(all.reads, ['a', 'b', 'c', 'd']);

  const exprs = recording({ x: 5, y: 1 });
  assert.equal(evaluate('0 <= x - y <= x * 2 >= y', exprs.variables), true);
  assert.deepEqual(exprs.reads, ['x', 'y', 'x', 'y']);
});

test('false chained comparison short-circuits the remaining operands', () => {
  const stops = recording({ x: 2, y: 9 });
  assert.equal(evaluate('3 < x < y', stops.variables), false);
  assert.deepEqual(stops.reads, ['x']);

  const middle = recording({ a: 1, b: 5, c: 2, d: 7 });
  assert.equal(evaluate('a < b < c < d', middle.variables), false);
  assert.deepEqual(middle.reads, ['a', 'b', 'c']);

  assert.equal(evaluate('1 > 2 < missing'), false);
  assert.equal(evaluate('1 > 2 < 1 / 0'), false);
  assert.equal(evaluate('2 > 1 > 0 > 5 == 1 // 0'), false);
});

test('chain short-circuit happens only after the whole formula parses', () => {
  assert.throws(
    () => evaluate('1 > 2 < foo(1)'),
    error => error instanceof ExprError && error.column === 9,
  );
  assert.throws(
    () => evaluate('1 > 2 < abs(1, 2)'),
    error => error instanceof ExprError && error.column === 9,
  );
  assert.throws(
    () => evaluate('1 > 2 < (3'),
    error => error instanceof ExprError && error.column === 11,
  );
});

test('randomized chained comparisons match a short-circuit oracle', () => {
  const operators = ['<', '<=', '>', '>=', '==', '!='];
  const compare = {
    '<': (a, b) => a < b,
    '<=': (a, b) => a <= b,
    '>': (a, b) => a > b,
    '>=': (a, b) => a >= b,
    '==': (a, b) => a === b,
    '!=': (a, b) => a !== b,
  };
  for (const seed of [11, 29, 404, 9001]) {
    const random = mulberry32(seed);
    const int = (low, high) => low + Math.floor(random() * (high - low + 1));
    for (let op = 0; op < 400; op += 1) {
      const names = ['p', 'q', 'r', 's'];
      const values = {};
      for (const name of names) values[name] = int(-2, 2);
      const operands = [];
      const count = int(2, 6);
      for (let i = 0; i < count; i += 1) {
        const name = names[int(0, names.length - 1)];
        const shape = int(0, 3);
        if (shape === 0) operands.push({ text: name, value: values[name], reads: [name] });
        else if (shape === 1) operands.push({ text: `-${name}`, value: -values[name], reads: [name] });
        else if (shape === 2) {
          operands.push({ text: `${name} * 2 - 1`, value: values[name] * 2 - 1, reads: [name] });
        } else {
          const literal = int(-3, 3);
          operands.push({ text: String(literal), value: literal, reads: [] });
        }
      }
      const chosen = [];
      for (let i = 1; i < count; i += 1) chosen.push(operators[int(0, operators.length - 1)]);
      let source = operands[0].text;
      for (let i = 1; i < count; i += 1) source += ` ${chosen[i - 1]} ${operands[i].text}`;

      const expectedReads = [...operands[0].reads];
      let expected = true;
      for (let i = 1; i < count; i += 1) {
        expectedReads.push(...operands[i].reads);
        if (!compare[chosen[i - 1]](operands[i - 1].value, operands[i].value)) {
          expected = false;
          break;
        }
      }
      const recorder = recording(values);
      const label = `seed ${seed}, op ${op}: ${source} with ${JSON.stringify(values)}`;
      assert.equal(evaluate(source, recorder.variables), expected, label);
      assert.deepEqual(recorder.reads, expectedReads, `reads for ${label}`);
    }
  }
});
