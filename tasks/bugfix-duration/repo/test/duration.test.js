'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { parseDuration } = require('../src/duration');

test('single-unit durations and decimals', () => {
  assert.equal(parseDuration('45s'), 45000);
  assert.equal(parseDuration('1.5h'), 5400000);
  assert.equal(parseDuration('250ms'), 250);
});

test('compound duration includes all parts', () => {
  assert.equal(parseDuration('1h30m'), 5400000);
});

test('invalid values are not silently accepted', () => {
  for (const value of ['', '10', '2weeks', '3s garbage', 42]) {
    assert.throws(() => parseDuration(value), TypeError);
  }
});
