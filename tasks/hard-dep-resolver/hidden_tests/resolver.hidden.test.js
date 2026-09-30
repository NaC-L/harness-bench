'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { resolve } = require('../src');

function freezeTree(value) {
  for (const child of Object.values(value)) if (child && typeof child === 'object') freezeTree(child);
  return Object.freeze(value);
}

test('zero-major install constraints reject unrelated minor and patch versions', () => {
  assert.deepEqual(resolve({ p: { '0.2.3': {}, '0.2.7': {}, '0.9.0': {} } },
    { p: '^0.2.3' }), { p: '0.2.7' });
  assert.deepEqual(resolve({ p: { '0.0.3': {}, '0.0.4': {}, '0.1.0': {} } },
    { p: '^0.0.3' }), { p: '0.0.3' });
});

test('numeric ordering applies to major minor and patch candidate choices', () => {
  for (const [low, high] of [['2.0.0', '10.0.0'], ['1.9.0', '1.10.0'], ['1.0.9', '1.0.10']]) {
    assert.deepEqual(resolve({ app: { '1.0.0': { lib: '*' } }, lib: { [low]: {}, [high]: {} } },
      { app: '*' }), { app: '1.0.0', lib: high });
  }
});

test('abandoned branches undo transitive constraints before trying an older parent', () => {
  const registry = {
    app: { '2.0.0': { bridge: '2.0.0' }, '1.0.0': { bridge: '1.0.0' } },
    bridge: { '2.0.0': { core: '2.0.0', unavailable: '*' }, '1.0.0': { core: '1.0.0' } },
    core: { '2.0.0': {}, '1.0.0': {} },
  };
  assert.deepEqual(resolve(registry, { app: '*' }), { app: '1.0.0', bridge: '1.0.0', core: '1.0.0' });
});

test('abandoned branches remove queued dependencies and unreachable selections', () => {
  const registry = {
    app: { '2.0.0': { orphan: '*', unavailable: '*' }, '1.0.0': {} },
    orphan: { '1.0.0': { descendant: '*' } },
    descendant: { '1.0.0': {} },
  };
  assert.deepEqual(resolve(registry, { app: '*' }), { app: '1.0.0' });
});

test('legal self and mutual dependency cycles terminate with a reachable assignment', () => {
  for (const registry of [
    { a: { '1.0.0': { a: '^1.0.0' } } },
    { a: { '1.0.0': { b: '*' } }, b: { '1.0.0': { a: '*' } } },
    { a: { '1.0.0': { b: '*' } }, b: { '1.0.0': { c: '*' } }, c: { '1.0.0': { a: '*' } } },
  ]) {
    const expected = Object.fromEntries(Object.keys(registry).map(name => [name, '1.0.0']));
    assert.deepEqual(resolve(registry, { a: '*' }), expected);
  }
});

test('cyclic conflicts can backtrack to an earlier consistent version', () => {
  assert.deepEqual(resolve({
    a: { '2.0.0': { b: '*' }, '1.0.0': { b: '*' } },
    b: { '1.0.0': { a: '1.0.0' } },
  }, { a: '*' }), { a: '1.0.0', b: '1.0.0' });
});

test('FIFO root discovery and recent-choice backtracking determine the first solution', () => {
  const registry = {
    alpha: { '2.0.0': { shared: '2.0.0' }, '1.0.0': { shared: '1.0.0' } },
    beta: { '2.0.0': { shared: '1.0.0' }, '1.0.0': { shared: '2.0.0' } },
    shared: { '2.0.0': {}, '1.0.0': {} },
  };
  assert.deepEqual(resolve(registry, { alpha: '*', beta: '*' }),
    { alpha: '2.0.0', beta: '1.0.0', shared: '2.0.0' });
  assert.deepEqual(resolve(registry, { beta: '*', alpha: '*' }),
    { beta: '2.0.0', alpha: '1.0.0', shared: '1.0.0' });
});

test('FIFO selected-version dependency key order determines the first solution', () => {
  const registry = {
    app: { '1.0.0': { left: '*', right: '*' } },
    left: { '2.0.0': { shared: '2.0.0' }, '1.0.0': { shared: '1.0.0' } },
    right: { '2.0.0': { shared: '1.0.0' }, '1.0.0': { shared: '2.0.0' } },
    shared: { '2.0.0': {}, '1.0.0': {} },
  };
  assert.deepEqual(resolve(registry, { app: '*' }),
    { app: '1.0.0', left: '2.0.0', right: '1.0.0', shared: '2.0.0' });
  registry.app['1.0.0'] = { right: '*', left: '*' };
  assert.deepEqual(resolve(registry, { app: '*' }),
    { app: '1.0.0', right: '2.0.0', left: '1.0.0', shared: '1.0.0' });
});

test('trap: missing versions and inconsistent requirements remain unsatisfiable', () => {
  assert.equal(resolve({}, { absent: '*' }), null);
  assert.equal(resolve({ empty: {} }, { empty: '*' }), null);
  assert.equal(resolve({ p: { '1.0.0': {} } }, { p: '>1.0.0' }), null);
  assert.equal(resolve({ a: { '1.0.0': { p: '2.0.0' } }, p: { '1.0.0': {} } },
    { a: '*', p: '1.0.0' }), null);
});

test('trap: empty roots ignore unreachable packages without changing the input', () => {
  const registry = freezeTree({ unused: { '1.0.0': { missing: '*' } } });
  assert.deepEqual(resolve(registry, Object.freeze({})), {});
});

test('trap: reachable noncyclic dependencies and frozen inputs retain their contract', () => {
  const registry = freezeTree({
    app: { '1.0.0': { lib: '>=1.0.0 <2.0.0' } },
    lib: { '1.0.0': {}, '2.0.0': {} },
    unreachable: { '3.0.0': {} },
  });
  const root = Object.freeze({ app: '*' });
  const before = JSON.stringify(registry);
  assert.deepEqual(resolve(registry, root), { app: '1.0.0', lib: '1.0.0' });
  assert.equal(JSON.stringify(registry), before);
  assert.deepEqual(resolve(registry, root), { app: '1.0.0', lib: '1.0.0' });
});

test('trap: own prototype-like package names are data in a plain result object', () => {
  const registry = JSON.parse('{"__proto__":{"1.0.0":{}},"constructor":{"1.0.0":{}},"toString":{"1.0.0":{}}}');
  const root = JSON.parse('{"__proto__":"*","constructor":"*","toString":"*"}');
  const result = resolve(registry, root);
  assert.equal(Object.getPrototypeOf(result), Object.prototype);
  assert.deepEqual(result, JSON.parse('{"__proto__":"1.0.0","constructor":"1.0.0","toString":"1.0.0"}'));
  const nullRegistry = Object.assign(Object.create(null), { p: Object.assign(Object.create(null), { '1.0.0': Object.create(null) }) });
  assert.deepEqual(resolve(nullRegistry, Object.assign(Object.create(null), { p: '*' })), { p: '1.0.0' });
});
