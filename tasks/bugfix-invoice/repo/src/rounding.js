'use strict';
const { integer } = require('./money');

/**
 * Round the exact rational numerator / denominator to the nearest integer cent.
 * Inputs are BigInts and denominator must be positive. Exact halfway cases
 * choose the even integer, symmetrically for either sign (0.5 -> 0, 1.5 -> 2,
 * -0.5 -> 0, -1.5 -> -2). No intermediate floating-point precision loss is
 * allowed, even when the numerator exceeds Number.MAX_SAFE_INTEGER. Return a
 * safe integer Number and normalize negative zero; reject unsafe results.
 */
function roundRatio(numerator, denominator) {
  if (typeof numerator !== 'bigint' || typeof denominator !== 'bigint') {
    throw new TypeError('A ratio requires BigInts');
  }
  if (denominator <= 0n) throw new RangeError('Denominator must be positive');
  return integer(Math.round(Number(numerator) / Number(denominator)), 'rounded cents');
}

module.exports = { roundRatio };
