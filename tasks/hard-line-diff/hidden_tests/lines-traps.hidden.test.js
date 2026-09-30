'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { splitLines, joinLines } = require('../src/lines');

test('trap: preserve literal LF splitting trailing blanks and CR characters', () => {
  for (const text of ['', '\n', '\n\n', 'a\n', 'a\r\nb\n', ' a\n+b\n-c']) {
    assert.equal(joinLines(splitLines(text)), text);
  }
  assert.deepEqual(splitLines('a\n\n'), ['a', '', '']);
  assert.deepEqual(splitLines(''), ['']);
  assert.equal(joinLines([]), '');
});
