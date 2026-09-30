'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { parse, compare, satisfies } = require('../src/semver');
const { resolve } = require('../src');

test('zero-major caret bounds follow the first nonzero component', () => {
  for (const [version, range, expected] of [
    ['0.2.3', '^0.2.3', true], ['0.2.99', '^0.2.3', true],
    ['0.2.2', '^0.2.3', false], ['0.3.0', '^0.2.3', false],
    ['0.9.0', '^0.2.3', false], ['0.0.3', '^0.0.3', true],
    ['0.0.4', '^0.0.3', false], ['0.0.0', '^0.0.0', true],
    ['0.0.1', '^0.0.0', false], ['0.1.0', '^0.0.3', false],
  ]) assert.equal(satisfies(version, range), expected, `${version} ${range}`);
});

test('trap: semver comparison is numeric without weakening canonical version parsing', () => {
  assert.deepEqual(parse('12.34.56'), [12, 34, 56]);
  assert.equal(compare('1.10.0', '1.9.999'), 1);
  assert.equal(compare('1.0.10', '1.0.9'), 1);
  assert.equal(compare('2.0.0', '10.0.0'), -1);
  assert.equal(compare('1.2.3', '1.2.3'), 0);
  assert.equal(compare('9007199254740991.0.0', '9007199254740990.99.99'), 1);
});

test('trap: positive-major ranges and comparator conjunctions preserve endpoints', () => {
  for (const [version, range, expected] of [
    ['9.8.7', '*', true], ['1.2.3', '1.2.3', true], ['1.2.4', '1.2.3', false],
    ['1.99.99', '^1.2.3', true], ['2.0.0', '^1.2.3', false],
    ['1.2.9', '~1.2.3', true], ['1.3.0', '~1.2.3', false],
    ['0.2.99', '~0.2.3', true], ['0.3.0', '~0.2.3', false],
    ['1.0.0', '>=1.0.0 <2.0.0', true], ['2.0.0', '>=1.0.0 <2.0.0', false],
    ['1.0.0', '>1.0.0 <=2.0.0', false], ['2.0.0', '>1.0.0 <=2.0.0', true],
    ['1.2.3', '  >=1.2.0\t<=1.2.3 *  ', true],
  ]) assert.equal(satisfies(version, range), expected, `${version} ${range}`);
});

test('trap: invalid versions and ranges always raise TypeError', () => {
  for (const version of [null, 3, '', '1.2', '1.2.3.4', '01.2.3', '-1.2.3',
    '1.2.3-beta', ' 1.2.3', '1.2.3 ', '9007199254740992.0.0']) {
    assert.throws(() => parse(version), TypeError, String(version));
    assert.throws(() => compare('1.0.0', version), TypeError, String(version));
    assert.throws(() => satisfies(version, '*'), TypeError, String(version));
  }
  for (const range of [null, 1, '', '   ', '^1.2', '>= 1.2.3', '=1.2.3',
    '1.x', '1.2.3 || 2.0.0', '* rubbish', '!=1.2.3', '^01.2.3', '<=NaN.0.0']) {
    assert.throws(() => satisfies('1.0.0', range), TypeError, String(range));
  }
});

test('trap: resolver eagerly validates malformed maps and unreachable metadata', () => {
  for (const registry of [null, [], 4, new Date(), { unused: null },
    { unused: { 'bad': {} } }, { unused: { '1.0.0': [] } },
    { unused: { '1.0.0': { dependency: 'bad range' } } }]) {
    assert.throws(() => resolve(registry, {}), TypeError);
  }
  for (const root of [null, [], 'root', { x: 'bad range' }]) {
    assert.throws(() => resolve({}, root), TypeError);
  }
});
