import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const entry = fileURLToPath(new URL('../bin/convert.js', import.meta.url));
function converts(value, from, to, expected, precision) {
  const args = ['convert', value, from, to];
  if (precision !== undefined) args.push('--precision', precision);
  const result = spawnSync(process.execPath, [entry, ...args], { encoding: 'utf8', timeout: 10000 });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, `${expected} ${to.toLowerCase()}\n`);
  assert.equal(result.stderr, '');
}

// These supported conversions already work in the starter. Parser repairs must not regress them.
for (const [value, from, to, expected, precision] of [
  ['1000', 'm', 'km', '1.00'],
  ['2.5', 'km', 'm', '2500.00'],
  ['1', 'cm', 'mm', '10.00'],
  ['1', 'mm', 'cm', '0.10'],
  ['1', 'mi', 'km', '1.6093', '4'],
  ['1', 'ft', 'in', '12.00'],
  ['1', 'in', 'cm', '2.54'],
  ['-2', 'm', 'cm', '-200.00'],
  ['2.5', 'kg', 'g', '2500.00'],
  ['250', 'g', 'kg', '0.25'],
  ['1', 'lb', 'oz', '16.00'],
  ['1', 'oz', 'g', '28.349523', '6'],
  ['0', 'c', 'f', '32.00'],
  ['20', 'c', 'k', '293.15'],
  ['212', 'f', 'c', '100.00'],
  ['32', 'f', 'k', '273.15'],
  ['273.15', 'k', 'c', '0.00'],
  ['373.15', 'k', 'f', '212.00'],
  ['0', 'kg', 'lb', '0.00'],
]) {
  test(`regression: ${value} ${from} to ${to} at ${precision ?? 'default'} precision`, () => {
    converts(value, from, to, expected, precision);
  });
}

for (const [value, from, to, expected] of [
  ['-40', 'f', 'c', '-40.00'],
  ['-10', 'c', 'k', '263.15'],
  ['-300', 'c', 'f', '-508.00'],
  ['-1', 'k', 'c', '-274.15'],
  ['0', 'k', 'f', '-459.67'],
  ['-12.25', 'c', 'c', '-12.25'],
]) {
  test(`negative and affine temperature behavior: ${value} ${from} to ${to}`, () => {
    converts(value, from, to, expected);
  });
}

for (const [value, from, to, expected] of [
  ['1', 'KM', 'M', '1000.00'],
  ['1', 'Lb', 'kG', '0.45'],
  ['-40', 'C', 'F', '-40.00'],
]) {
  test(`mixed case ${from} to ${to} normalizes output`, () => {
    converts(value, from, to, expected);
  });
}
