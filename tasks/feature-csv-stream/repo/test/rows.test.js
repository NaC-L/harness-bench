'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { toObjects } = require('../src/rows');

test('rows helper keeps duplicate columns with suffixes', () => {
  assert.deepEqual(toObjects([['name', 'name'], ['Ada', 'Lovelace']]), [
    { name: 'Ada', name_2: 'Lovelace' },
  ]);
});

test('rows helper pads short records and ignores surplus cells', () => {
  assert.deepEqual(toObjects([['a', 'b'], ['one'], ['two', 'three', 'extra']]), [
    { a: 'one', b: '' },
    { a: 'two', b: 'three' },
  ]);
});
