'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { parseDuration } = require('../src/duration');

test('all units, arbitrary ordering, and repeated parts', () => {
  for (const [input, expected] of [
    ['2d4h', 187200000], ['1d2h3m4s5ms', 93784005],
    ['10ms2s3ms', 2013], ['1m1m1m', 180000], ['30s1h', 3630000],
    ['0h2m0s', 120000], ['0002s', 2000],
  ]) assert.equal(parseDuration(input), expected, input);
});

test('decimal parts, zero, and exterior whitespace', () => {
  for (const [input, expected] of [
    ['1.5h0.5m', 5430000], ['0.25s0.5ms', 250.5],
    ['1.25d', 108000000], ['0ms', 0], ['0.0h0s', 0],
    [' \t2m5s\r\n', 125000],
  ]) assert.equal(parseDuration(input), expected, input);
});

test('rejects malformed strings and every non-string input', () => {
  for (const value of [
    undefined, null, true, 0, NaN, {}, [], new String('1s'),
    '', ' ', '-1s', '+1s', '.5h', '1.h', '1..5h', '1e3s',
    '1H', '1S', '1mo', '1sec', '1h 30m', '1h\n30m', 's',
    'prefix1s', '1s!', '1s2', '1s2bad', '1s\n!', 'Infinitys',
  ]) assert.throws(() => parseDuration(value), TypeError, String(value));
});

test('rejects non-finite components and accumulated overflow', () => {
  assert.throws(() => parseDuration('9'.repeat(400) + 'ms'), TypeError);
  const nearLimit = '8' + '0'.repeat(307) + 'ms';
  assert.equal(parseDuration(nearLimit), 8e307);
  assert.throws(() => parseDuration(nearLimit.repeat(3)), TypeError);
});
