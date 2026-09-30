'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const { resolve } = require('../src');

test('long dependency chains resolve without a call-stack or iteration limit', () => {
  const registry = {};
  const expected = {};
  for (let i = 0; i < 12000; i += 1) {
    registry[`chain${i}`] = { '1.0.0': i === 11999 ? {} : { [`chain${i + 1}`]: '*' } };
    expected[`chain${i}`] = '1.0.0';
  }
  assert.deepEqual(resolve(registry, { chain0: '*' }), expected);
});

test('deep failures backtrack promptly through many rejected candidate branches', () => {
  const versions = { '1.0.0': { winner: '*' } };
  const registry = { app: versions, winner: { '1.0.0': {} }, gate: { '1.0.0': {} } };
  for (let i = 1; i <= 160; i += 1) {
    versions[`1.0.${i}`] = { [`probe${i}`]: '*' };
    registry[`probe${i}`] = { '1.0.0': { [`middle${i}`]: '*' } };
    registry[`middle${i}`] = { '1.0.0': { gate: '2.0.0' } };
  }
  assert.deepEqual(resolve(registry, { app: '*' }), { app: '1.0.0', winner: '1.0.0' });
});

test('trap: constrained installs prune discovered conflicts instead of enumerating products', () => {
  const registry = {};
  const root = {};
  const expected = {};
  for (let i = 0; i < 13; i += 1) {
    const name = `p${i}`;
    const deps = i === 12 ? {} : { [`p${i + 1}`]: '1.0.0' };
    registry[name] = { '1.0.0': { ...deps }, '1.0.1': { ...deps }, '1.0.2': { ...deps } };
    root[name] = '*';
    expected[name] = i === 0 ? '1.0.2' : '1.0.0';
  }
  const budgetMs = 1000;
  const started = performance.now();
  for (let op = 0; op < 128; op += 1) {
    const actual = resolve(registry, root);
    assert.deepEqual(actual, expected, `install op=${op}`);
    // Check each install: a full-product rewrite has 531,441 leaf assignments
    // per install, so even a short batch must abort rather than run for minutes.
    assert.ok(performance.now() - started < budgetMs, `search exceeded ${budgetMs}ms at install op=${op}`);
  }
});
