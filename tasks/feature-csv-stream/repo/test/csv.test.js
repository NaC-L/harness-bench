'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createParser, parse } = require('../src/csv');

test('single push emits complete comma-separated records', () => {
  const parser = createParser();
  assert.deepEqual(parser.push('name,age\nAda,37\n'), [['name', 'age'], ['Ada', '37']]);
  assert.deepEqual(parser.end(), []);
});

test('single push parses quoted commas and doubled quotes', () => {
  assert.deepEqual(parse('"a,b","say ""hi"""\n'), [['a,b', 'say "hi"']]);
});

test('end flushes one unfinished record including empty fields', () => {
  const parser = createParser();
  assert.deepEqual(parser.push('left,,right,'), []);
  assert.deepEqual(parser.end(), [['left', '', 'right', '']]);
});

test('single push preserves a newline inside a quoted field', () => {
  assert.deepEqual(parse('"first\nsecond",tail\n'), [['first\nsecond', 'tail']]);
});

test('parse header mode uses the first record as object keys', () => {
  assert.deepEqual(parse('name,age\nAda,37\n', { header: true }), [{ name: 'Ada', age: '37' }]);
});
