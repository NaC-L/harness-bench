'use strict';

// Public money fields are safe integer Numbers in cents. Intermediate sums and
// products must be exact even when they temporarily exceed Number's safe range.
// Each stored result (including line totals and positive discount bases) must be
// safe; otherwise throw RangeError. Always return ordinary +0 rather than -0.
const LIMIT = BigInt(Number.MAX_SAFE_INTEGER);

function integer(value, label, min = -Number.MAX_SAFE_INTEGER, max = Number.MAX_SAFE_INTEGER) {
  if (!Number.isSafeInteger(value) || value < min || value > max) {
    throw new RangeError(`${label} must be a safe integer in [${min}, ${max}]`);
  }
  return value === 0 ? 0 : value;
}

function cents(value, label = 'amount') {
  if (value < -LIMIT || value > LIMIT) throw new RangeError(`${label} exceeds safe cents`);
  return Number(value);
}

function sum(values, label = 'sum') {
  return cents(values.reduce((total, value) => total + BigInt(value), 0n), label);
}

function product(a, b, label = 'product') {
  return cents(BigInt(a) * BigInt(b), label);
}

function difference(a, b, label = 'difference') {
  return cents(BigInt(a) - BigInt(b), label);
}

module.exports = { integer, cents, sum, product, difference };
