import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const entry = fileURLToPath(new URL('../bin/convert.js', import.meta.url));
function run(args) {
  const result = spawnSync(process.execPath, [entry, ...args], { encoding: 'utf8', timeout: 10000 });
  assert.ifError(result.error);
  return result;
}
function success(args, output) {
  const result = run(args);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, output);
  assert.equal(result.stderr, '');
}
function error(args, reason, offending) {
  const result = run(args);
  assert.equal(result.status, 2, result.stderr);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, reason);
  assert.ok(result.stderr.includes('--help'), result.stderr);
  if (offending !== undefined) assert.ok(result.stderr.includes(offending), result.stderr);
  assert.doesNotMatch(result.stderr, /\n\s+at\s|file:\/\/|(?:src|bin)[\\/].*\.js:\d/);
  return result.stderr;
}

for (const [value, expected] of [
  ['+.5', '0.50'], ['1.', '1.00'], ['-2.5e1', '-25.00'],
  ['1E+3', '1000.00'], ['5e-3', '0.01'], ['-5e-2', '-0.05'],
]) {
  test(`complete signed decimal and exponent input ${value}`, () => {
    success(['convert', value, 'm', 'm'], `${expected} m\n`);
  });
}

for (const value of [
  '', ' ', ' 1', '1 ', '2\n', '1\t2', '.', '+', '1e', '1e+', '12cm', '1_000', '1,2',
  '0x10', '0b11', 'NaN', 'Infinity', '-Infinity', '1e309', '-1e309',
]) {
  test(`rejects non-finite or incomplete number ${JSON.stringify(value)}`, () => {
    error(['convert', value, 'm', 'cm'], /value|number|decimal|numeric|finite/i, value);
  });
}

for (const precision of ['0', '1', '2', '3', '4', '5', '6', '00', '06']) {
  test(`precision ${precision} controls actual rounding`, () => {
    success(['convert', '1', 'm', 'ft', '--precision', precision], `${(1 / 0.3048).toFixed(Number(precision))} ft\n`);
  });
}

for (const precision of ['-1', '+1', '7', '99', '1.5', '2x', '1e0', '0x2', '', ' ', '2\n']) {
  test(`rejects invalid precision ${JSON.stringify(precision)}`, () => {
    error(['convert', '1', 'm', 'ft', '--precision', precision], /precision|integer|range/i, precision);
  });
}

for (const [args, reason, offending] of [
  [[], /command|usage|required|missing/i],
  [['convert'], /value|missing|required/i],
  [['convert', '1'], /source|from|unit|missing|required/i],
  [['convert', '1', 'm'], /target|to|unit|missing|required/i],
  [['frobnicate'], /command|unknown/i, 'frobnicate'],
  [['--wat'], /flag|option|unknown/i, '--wat'],
  [['convert', '1', 'm', 'cm', 'spare'], /extra|unexpected|argument/i, 'spare'],
  [['convert', '1', 'm', 'cm', '--bogus'], /flag|option|unknown/i, '--bogus'],
  [['convert', '1', 'm', 'cm', '-q'], /flag|option|unknown/i, '-q'],
  [['convert', '1', 'm', 'cm', '--precision=3'], /flag|option|unknown/i, '--precision=3'],
  [['convert', '1', 'm', 'cm', '--precision', '2', 'tail'], /extra|unexpected|argument/i, 'tail'],
  [['convert', '1', 'm', 'cm', '--precision', '2', '--precision', '3'], /extra|duplicate|unexpected|argument/i, '--precision'],
  [['convert', '--precision', '2', 'm', 'cm'], /value|number|flag|argument/i, '--precision'],
]) {
  test(`usage error for ${JSON.stringify(args)}`, () => error(args, reason, offending));
}

for (const command of ['--help', '-h', '--version', 'units']) {
  test(`${command} rejects trailing operands`, () => {
    error([command, 'extra'], /extra|unexpected|argument/i, 'extra');
  });
}

for (const [source, target] of [['m', 'kg'], ['oz', 'c'], ['f', 'km']]) {
  test(`incompatible dimensions ${source} to ${target}`, () => {
    const message = error(['convert', '1', source, target], /dimension|incompatible|cannot|length|mass|temperature/i, source);
    assert.ok(message.includes(target), message);
  });
}

for (const [unknown, suggestion] of [['cmm', 'cm'], ['KGs', 'kg'], ['mt', 'm'], ['fa', 'ft'], ['zz', 'oz']]) {
  for (const side of ['source', 'target']) {
    test(`${side} typo ${unknown} suggests the closest unit with ordered ties`, () => {
      const args = side === 'source' ? ['convert', '1', unknown, 'in'] : ['convert', '1', 'in', unknown];
      const message = error(args, /unit/i, unknown);
      assert.match(message, /suggest|did you mean|perhaps|try|instead/i);
      assert.match(message, new RegExp(`\\b${suggestion}\\b`));
    });
  }
}

test('distant unit name is rejected without a made-up suggestion', () => {
  const message = error(['convert', '1', 'astronomical', 'm'], /unit/i, 'astronomical');
  assert.doesNotMatch(message, /did you mean|suggest|perhaps/i);
});

test('main returns codes and routes injected streams without terminating or throwing', () => {
  const cli = new URL('../src/cli.js', import.meta.url).href;
  const script = `
    import { main } from ${JSON.stringify(cli)};
    const results = [];
    for (const argv of [[], ['convert', '1', 'm', 'kg'], ['convert', '1', 'km', 'm']]) {
      let stdout = '', stderr = '';
      try {
        const code = main(argv, { stdout: { write(text) { stdout += text; } }, stderr: { write(text) { stderr += text; } } });
        results.push({ code, stdout, stderr });
      } catch (error) { results.push({ thrown: error.message }); }
    }
    process.stdout.write(JSON.stringify(results));
  `;
  const child = spawnSync(process.execPath, ['--input-type=module', '-e', script], { encoding: 'utf8', timeout: 10000 });
  assert.ifError(child.error);
  assert.equal(child.status, 0, child.stderr);
  assert.equal(child.stderr, '');
  const [missing, incompatible, valid] = JSON.parse(child.stdout);
  for (const result of [missing, incompatible]) {
    assert.equal(result.code, 2);
    assert.equal(result.stdout, '');
    assert.match(result.stderr, /--help/);
    assert.doesNotMatch(result.stderr, /\n\s+at\s/);
  }
  assert.match(missing.stderr, /command|missing|required/i);
  assert.match(incompatible.stderr, /dimension|incompatible|cannot/i);
  assert.deepEqual(valid, { code: 0, stdout: '1000.00 m\n', stderr: '' });
});
