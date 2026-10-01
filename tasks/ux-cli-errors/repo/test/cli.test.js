import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const entry = fileURLToPath(new URL('../bin/convert.js', import.meta.url));
function run(...args) {
  const result = spawnSync(process.execPath, [entry, ...args], { encoding: 'utf8', timeout: 10000 });
  assert.ifError(result.error);
  return result;
}
function succeeds(args, output) {
  const result = run(...args);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, output);
  assert.equal(result.stderr, '');
}
function rejects(args, words, offending) {
  const result = run(...args);
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, words);
  assert.ok(result.stderr.includes('--help'), result.stderr);
  if (offending !== undefined) assert.ok(result.stderr.includes(offending), result.stderr);
  assert.doesNotMatch(result.stderr, /\n\s+at\s|file:\/\/|(?:src|bin)[\\/].*\.js:\d/);
  return result.stderr;
}

test('working length conversion retains its exact successful output', () => {
  succeeds(['convert', '1', 'km', 'm'], '1000.00 m\n');
});

test('working mass conversion honors explicit precision', () => {
  succeeds(['convert', '1', 'lb', 'kg', '--precision', '3'], '0.454 kg\n');
});

test('negative temperature is not converted as an absolute value', () => {
  succeeds(['convert', '-40', 'c', 'f'], '-40.00 f\n');
});

for (const flag of ['--help', '-h']) {
  test(`help ${flag} is successful stdout with usage and runnable examples`, () => {
    const result = run(flag);
    assert.equal(result.status, 0);
    assert.equal(result.stderr, '');
    assert.match(result.stdout, /usage/i);
    assert.match(result.stdout, /units/);
    assert.match(result.stdout, /--version/);
    assert.match(result.stdout, /--precision/);
    const examples = result.stdout.split('\n').map(line => line.trim())
      .filter(line => line.startsWith('node bin/convert.js convert ') && !/[<>]/.test(line));
    assert.ok(examples.some(line => line.includes('--precision')), result.stdout);
    assert.ok(examples.some(line => !line.includes('--precision')), result.stdout);
    for (const example of examples) {
      const converted = run(...example.split(/\s+/).slice(2));
      assert.equal(converted.status, 0, example);
      assert.equal(converted.stderr, '');
      assert.match(converted.stdout, /^-?\d+(?:\.\d+)? [a-z]+\n$/);
    }
  });
}

test('version is printed without diagnostics', () => {
  succeeds(['--version'], '1.0.0\n');
});

test('units lists all three conversion dimensions', () => {
  const result = run('units');
  assert.equal(result.status, 0);
  assert.equal(result.stderr, '');
  for (const dimension of ['length', 'mass', 'temperature']) assert.match(result.stdout, new RegExp(dimension, 'i'));
  for (const symbol of ['m', 'km', 'cm', 'mm', 'mi', 'ft', 'in', 'kg', 'g', 'lb', 'oz', 'c', 'f', 'k']) {
    assert.match(result.stdout, new RegExp(`\\b${symbol}\\b`));
  }
});

test('partially numeric input is a useful usage error', () => {
  rejects(['convert', '12oops', 'm', 'cm'], /value|number|decimal|numeric/i, '12oops');
});

test('unknown units are a useful usage error rather than a stack trace', () => {
  rejects(['convert', '1', 'meterz', 'cm'], /unit/i, 'meterz');
});

test('a missing precision value is rejected instead of silently defaulted', () => {
  rejects(['convert', '1', 'm', 'cm', '--precision'], /precision|missing|required/i, '--precision');
});

test('a misspelled precision flag suggests its correction', () => {
  const message = rejects(['convert', '1', 'm', 'cm', '--precison', '3'], /flag|option|unknown/i, '--precison');
  assert.ok(message.includes('--precision'), message);
});
