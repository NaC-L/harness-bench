'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { diffLines } = require('../src/diff');

function mulberry32(seed) {
  return () => {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function lcsLength(a, b) {
  const table = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      table[i][j] = a[i] === b[j] ? 1 + table[i + 1][j + 1] :
        Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }
  return table[0][0];
}

function checkScript(a, b, label) {
  const script = diffLines(Object.freeze(a.slice()), Object.freeze(b.slice()));
  assert.ok(Array.isArray(script), label);
  const old = [];
  const fresh = [];
  let edits = 0;
  let inserted = false;
  for (const entry of script) {
    assert.ok(entry && ['equal', 'delete', 'insert'].includes(entry.op), label);
    assert.equal(typeof entry.line, 'string', label);
    if (entry.op === 'equal') inserted = false;
    else {
      edits++;
      if (entry.op === 'insert') inserted = true;
      else assert.equal(inserted, false, `${label}: delete follows insert in changed region`);
    }
    if (entry.op !== 'insert') old.push(entry.line);
    if (entry.op !== 'delete') fresh.push(entry.line);
  }
  assert.deepEqual(old, a, `${label}: source reconstruction`);
  assert.deepEqual(fresh, b, `${label}: target reconstruction`);
  assert.equal(edits, a.length + b.length - 2 * lcsLength(a, b), `${label}: nonminimal script`);
  return script;
}

test('hidden: minimal scripts match seeded repetitive-line LCS oracle', () => {
  const alphabet = ['', 'a', 'b', 'c', '-prefix', '+prefix', ' space'];
  for (const seed of [0x17A39B2D, 0xC0FFEE, 0x89123456]) {
    const random = mulberry32(seed);
    const make = () => Array.from({ length: Math.floor(random() * 15) },
      () => alphabet[Math.floor(random() * alphabet.length)]);
    for (let op = 0; op < 300; op++) {
      const a = make();
      const b = make();
      const label = `seed=${seed} op=${op}`;
      const script = checkScript(a, b, label);
      if (op % 30 === 0) assert.deepEqual(diffLines(a, b), script, `${label}: nondeterministic`);
    }
  }
});

test('hidden: empty and tied scripts retain deletion-first order', () => {
  for (const [a, b] of [
    [[], []], [[], ['', '+x']], [['-x', ''], []],
    [['a', 'b', 'a'], ['b', 'a', 'b']],
    [['a', 'a', 'b', 'b'], ['b', 'b', 'a', 'a']],
    [['old1', 'old2'], ['new1', 'new2']],
    [['same', '', 'same'], ['same', '', 'same']],
  ]) checkScript(a, b, `edge ${JSON.stringify([a, b])}`);
});
