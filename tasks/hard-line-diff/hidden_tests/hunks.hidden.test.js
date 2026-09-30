'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { unifiedHunks, applyHunks } = require('../src/diff');

function mulberry32(seed) {
  return () => {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

test('hidden: GNU zero-length headers at top end and empty inputs', () => {
  const cases = [
    [[], [], 0, []],
    [[], ['x', 'y'], 3, [{ oldStart: 0, oldLines: 0, newStart: 1, newLines: 2, lines: ['+x', '+y'] }]],
    [['x', 'y'], [], 3, [{ oldStart: 1, oldLines: 2, newStart: 0, newLines: 0, lines: ['-x', '-y'] }]],
    [['a', 'b'], ['x', 'a', 'b'], 0, [{ oldStart: 0, oldLines: 0, newStart: 1, newLines: 1, lines: ['+x'] }]],
    [['a', 'b'], ['a', 'b', 'x'], 0, [{ oldStart: 2, oldLines: 0, newStart: 3, newLines: 1, lines: ['+x'] }]],
    [['a', 'b'], ['b'], 0, [{ oldStart: 1, oldLines: 1, newStart: 0, newLines: 0, lines: ['-a'] }]],
    [['a', 'b'], ['a'], 0, [{ oldStart: 2, oldLines: 1, newStart: 1, newLines: 0, lines: ['-b'] }]],
    [['a', 'b'], ['x', 'a', 'b'], 1, [{ oldStart: 1, oldLines: 1, newStart: 1, newLines: 2, lines: ['+x', ' a'] }]],
    [['a', 'b'], ['a'], 1, [{ oldStart: 1, oldLines: 2, newStart: 1, newLines: 1, lines: [' a', '-b'] }]],
  ];
  for (const [a, b, context, expected] of cases) {
    const label = `header ${JSON.stringify([a, b, context])}`;
    assert.deepEqual(unifiedHunks(a, b, { context }), expected, label);
    assert.deepEqual(applyHunks(a, expected), b, label);
  }
});

test('hidden: touching contexts merge but one extra unchanged line splits', () => {
  for (const context of [0, 1, 2, 3]) {
    for (const extra of [0, 1]) {
      const middle = Array.from({ length: 2 * context + extra }, (_, i) => `gap${i}`);
      const a = ['old-left', ...middle, 'old-right'];
      const b = ['new-left', ...middle, 'new-right'];
      const expected = extra === 0 ? [{
        oldStart: 1, oldLines: a.length, newStart: 1, newLines: b.length,
        lines: middle.length === 0 ? ['-old-left', '-old-right', '+new-left', '+new-right'] :
          ['-old-left', '+new-left', ...middle.map(x => ' ' + x), '-old-right', '+new-right'],
      }] : [{
        oldStart: 1, oldLines: 1 + context, newStart: 1, newLines: 1 + context,
        lines: ['-old-left', '+new-left', ...middle.slice(0, context).map(x => ' ' + x)],
      }, {
        oldStart: context + 3, oldLines: context + 1, newStart: context + 3, newLines: context + 1,
        lines: [...middle.slice(context + 1).map(x => ' ' + x), '-old-right', '+new-right'],
      }];
      assert.deepEqual(unifiedHunks(a, b, { context }), expected, `context=${context} extra=${extra}`);
    }
  }
});

test('hidden: default context clips to file boundaries without losing blank prefixes', () => {
  const a = ['0', '1', '2', '3', '', '+old', '6', '7', '8', '9', '10'];
  const b = ['0', '1', '2', '3', '', '-new', '6', '7', '8', '9', '10'];
  assert.deepEqual(unifiedHunks(a, b), [{
    oldStart: 3, oldLines: 7, newStart: 3, newLines: 7,
    lines: [' 2', ' 3', ' ', '-+old', '+-new', ' 6', ' 7', ' 8'],
  }]);
  assert.deepEqual(unifiedHunks(a, a), []);
});

test('hidden: seeded hunk roundtrips preserve originals for contexts zero through three', () => {
  const seed = 0xADDA9911;
  const random = mulberry32(seed);
  const alphabet = ['', 'one', 'two', 'three', '-minus', '+plus', ' space'];
  const make = () => Array.from({ length: Math.floor(random() * 20) },
    () => alphabet[Math.floor(random() * alphabet.length)]);
  for (let op = 0; op < 250; op++) {
    const a = Object.freeze(make());
    const b = Object.freeze(make());
    for (let context = 0; context <= 3; context++) {
      const label = `seed=${seed} op=${op} context=${context}`;
      const hunks = unifiedHunks(a, b, { context });
      for (const hunk of hunks) {
        Object.freeze(hunk.lines);
        Object.freeze(hunk);
      }
      Object.freeze(hunks);
      assert.deepEqual(applyHunks(a, hunks), b, label);
    }
  }
});

test('hidden: apply original-coordinate hunks after positive and negative offsets', () => {
  const a = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const hunks = [
    { oldStart: 0, oldLines: 0, newStart: 1, newLines: 2, lines: ['+front1', '+front2'] },
    { oldStart: 3, oldLines: 2, newStart: 4, newLines: 0, lines: ['-c', '-d'] },
    { oldStart: 7, oldLines: 1, newStart: 7, newLines: 2, lines: [' g', '+near-end'] },
  ];
  assert.deepEqual(applyHunks(a, hunks), ['front1', 'front2', 'a', 'b', 'e', 'f', 'g', 'near-end', 'h']);
  const unchanged = applyHunks(a, []);
  assert.deepEqual(unchanged, a);
  assert.notEqual(unchanged, a);
});

test('hidden: context deletion and later-hunk mismatches identify their hunk index', () => {
  const a = ['a', 'b', 'c', 'd', 'e'];
  const first = { oldStart: 1, oldLines: 1, newStart: 1, newLines: 1, lines: ['-a', '+A'] };
  const last = { oldStart: 4, oldLines: 2, newStart: 4, newLines: 2, lines: [' d', '-e', '+E'] };
  const badContext = { ...last, lines: [' D', '-e', '+E'] };
  const badDelete = { ...last, lines: [' d', '-E', '+E'] };
  for (const hunks of [[badContext], [badDelete]]) {
    assert.throws(() => applyHunks(a, hunks), /hunk 0 does not apply/);
  }
  for (const second of [badContext, badDelete]) {
    assert.throws(() => applyHunks(a, [first, second]), /hunk 1 does not apply/);
  }
  assert.deepEqual(a, ['a', 'b', 'c', 'd', 'e']);
});

test('hidden: invalid ranges counts prefixes and hunk ordering reject applicability', () => {
  const a = ['a', 'b', 'c'];
  const valid = { oldStart: 2, oldLines: 1, newStart: 2, newLines: 1, lines: ['-b', '+B'] };
  for (const bad of [
    { ...valid, oldStart: 0 }, { ...valid, oldStart: 8 },
    { ...valid, newStart: 1 }, { ...valid, oldLines: 2 },
    { ...valid, newLines: 2 }, { ...valid, lines: ['?b'] },
  ]) assert.throws(() => applyHunks(a, [bad]), /hunk 0 does not apply/);
  assert.throws(() => applyHunks(a, [valid, valid]), /hunk 1 does not apply/);
});
