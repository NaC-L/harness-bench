'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { RangeTree } = require('../src/range-tree');

test('overwriting a lazily updated range preserves its subrange sum', () => {
  const tree = new RangeTree([1, 2, 3, 4, 5, 6, 7, 8]);
  tree.assign(0, 8, 4);
  tree.add(0, 8, 3);
  tree.assign(0, 8, 10);
  tree.add(0, 8, 2);
  assert.equal(tree.sum(2, 6), 48);
});
