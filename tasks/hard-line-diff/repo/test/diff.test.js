'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { diffLines, unifiedHunks } = require('../src/diff');
const { splitLines } = require('../src/lines');

test('visible: implement the review diff for one replaced line', () => {
  const a = splitLines('header\nold value\nfooter');
  const b = splitLines('header\nnew value\nfooter');
  assert.deepEqual(diffLines(a, b), [
    { op: 'equal', line: 'header' },
    { op: 'delete', line: 'old value' },
    { op: 'insert', line: 'new value' },
    { op: 'equal', line: 'footer' },
  ]);
  assert.deepEqual(unifiedHunks(a, b, { context: 1 }), [{
    oldStart: 1,
    oldLines: 3,
    newStart: 1,
    newLines: 3,
    lines: [' header', '-old value', '+new value', ' footer'],
  }]);
});
