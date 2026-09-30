'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { resolve } = require('../src');

function mulberry32(seed) {
  return () => {
    let value = seed += 0x6D2B79F5;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

// Independent, deliberately small oracle; it never calls the source helpers.
function order(a, b) {
  const x = a.split('.').map(Number);
  const y = b.split('.').map(Number);
  for (let i = 0; i < 3; i += 1) if (x[i] !== y[i]) return Math.sign(x[i] - y[i]);
  return 0;
}

function accepts(version, range) {
  return range.trim().split(/\s+/).every(term => {
    if (term === '*') return true;
    const [, operator = '', base] = /^(>=|<=|>|<|\^|~)?(.+)$/.exec(term);
    const comparison = order(version, base);
    if (operator === '') return comparison === 0;
    if (operator === '>=') return comparison >= 0;
    if (operator === '>') return comparison > 0;
    if (operator === '<=') return comparison <= 0;
    if (operator === '<') return comparison < 0;
    const [major, minor, patch] = base.split('.').map(Number);
    let ceiling;
    if (operator === '~') ceiling = `${major}.${minor + 1}.0`;
    else if (major > 0) ceiling = `${major + 1}.0.0`;
    else if (minor > 0) ceiling = `0.${minor + 1}.0`;
    else ceiling = `0.0.${patch + 1}`;
    return comparison >= 0 && order(version, ceiling) < 0;
  });
}

function valid(registry, root, assignment) {
  if (assignment === null || typeof assignment !== 'object' || Array.isArray(assignment)) return false;
  const reached = new Set();
  const pending = Object.entries(root);
  for (let cursor = 0; cursor < pending.length; cursor += 1) {
    const [name, range] = pending[cursor];
    if (!Object.hasOwn(assignment, name)) return false;
    const version = assignment[name];
    if (typeof version !== 'string' || !Object.hasOwn(registry[name] || {}, version) || !accepts(version, range)) return false;
    if (reached.has(name)) continue;
    reached.add(name);
    pending.push(...Object.entries(registry[name][version]));
  }
  return reached.size === Object.keys(assignment).length;
}

function bruteForce(registry, root) {
  const names = Object.keys(registry);
  const assignment = {};
  function enumerate(index) {
    if (index === names.length) return valid(registry, root, assignment) ? { ...assignment } : null;
    const name = names[index];
    // Absence is essential: versions in unreachable registry entries must not
    // accidentally be accepted as part of an otherwise valid assignment.
    const absent = enumerate(index + 1);
    if (absent !== null) return absent;
    for (const version of Object.keys(registry[name])) {
      assignment[name] = version;
      const answer = enumerate(index + 1);
      if (answer !== null) return answer;
    }
    delete assignment[name];
    return null;
  }
  return enumerate(0);
}

const VERSION_POOL = ['0.0.1', '0.0.2', '0.0.3', '0.1.0', '0.1.2', '0.2.0',
  '0.2.3', '0.2.4', '0.9.0', '1.0.0', '1.2.0', '1.9.0', '1.10.0', '2.0.0'];
const RANGE_POOL = ['*', '*', '*', '^0.0.1', '^0.2.3', '^1.0.0', '~0.1.0',
  '>=0.0.2 <1.0.0', '>1.0.0 <=1.10.0', '<=0.2.4', '>=0.2.3'];

for (const seed of [0xA11CE, 0xC0FFEE, 0x5EED123, 0xF00DBABE]) {
  test(`seeded exhaustive registry oracle seed=${seed}`, () => {
    const random = mulberry32(seed);
    const pick = values => values[Math.floor(random() * values.length)];
    for (let op = 0; op < 40; op += 1) {
      const names = Array.from({ length: 4 + Math.floor(random() * 2) }, (_, i) => `p${i}`);
      const registry = {};
      for (const name of names) {
        const pool = [...VERSION_POOL];
        for (let i = pool.length - 1; i > 0; i -= 1) {
          const j = Math.floor(random() * (i + 1));
          [pool[i], pool[j]] = [pool[j], pool[i]];
        }
        const versions = {};
        for (const version of pool.slice(0, 3 + Math.floor(random() * 3))) {
          const deps = {};
          for (const dependency of names) {
            if (random() < 0.19) deps[dependency] = random() < 0.15 ? pick(VERSION_POOL) : pick(RANGE_POOL);
          }
          versions[version] = deps;
        }
        registry[name] = versions;
      }
      const root = {};
      for (const name of names) if (random() < 0.45) root[name] = pick(RANGE_POOL);
      if (Object.keys(root).length === 0) root[pick(names)] = '*';
      const expected = bruteForce(registry, root);
      const actual = resolve(registry, root);
      const context = `seed=${seed} op=${op} registry=${JSON.stringify(registry)} root=${JSON.stringify(root)}`;
      assert.equal(actual === null, expected === null, `existence: ${context}`);
      if (actual !== null) assert.equal(valid(registry, root, actual), true, `validity/reachability: ${context}`);
    }
  });
}
