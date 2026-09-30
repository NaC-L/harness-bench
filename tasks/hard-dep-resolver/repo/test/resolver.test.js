'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { resolve } = require('../src');

test('CI install selects the newest compatible numeric version', () => {
  const registry = { widget: { '1.9.0': {}, '1.10.0': {} } };
  assert.deepEqual(resolve(registry, { widget: '^1.0.0' }), { widget: '1.10.0' });
});
