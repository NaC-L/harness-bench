'use strict';
const { cents } = require('./money');

// Floor division, including negative numerators; the remainder is in [0, d).
function floorParts(numerator, denominator) {
  let quotient = numerator / denominator;
  let remainder = numerator % denominator;
  if (remainder < 0n) {
    quotient -= 1n;
    remainder += denominator;
  }
  return { quotient, remainder };
}

/**
 * Given exact ideal numerators over a common positive denominator, distribute
 * targetCents using largest remainders: floor EVERY signed ideal, then add one
 * cent to entries with the greatest fractional remainders until the target is
 * reached. Equal remainders favor the original line index, not line value,
 * currency, sign, or tax-group traversal order. No caller arrays are mutated.
 * The target is the rounded sum of the ideals (tax) or their exact sum (discount).
 */
function distribute(targetCents, numerators, denominator) {
  const parts = numerators.map((numerator, index) => ({ ...floorParts(numerator, denominator), index }));
  const floorSum = parts.reduce((sum, part) => sum + part.quotient, 0n);
  const extras = Number(BigInt(targetCents) - floorSum);
  const ranked = parts.slice().sort((a, b) => {
    if (a.remainder !== b.remainder) return a.remainder > b.remainder ? -1 : 1;
    return a.index - b.index;
  });
  for (let i = 0; i < extras; i += 1) ranked[i].quotient += 1n;
  return parts.map(part => cents(part.quotient, 'allocated cents'));
}

/**
 * Allocate a capped nonnegative invoice discount proportionally across positive
 * post-line-discount balances. Credits/zero balances have weight zero and get
 * no share. A zero discount returns zeros, even if all weights are zero.
 */
function allocateDiscount(amountCents, weights) {
  if (amountCents === 0) return weights.map(() => 0);
  const denominator = weights.reduce((sum, weight) => sum + BigInt(weight), 0n);
  return distribute(amountCents, weights.map(weight => BigInt(amountCents) * BigInt(weight)), denominator);
}

module.exports = { distribute, allocateDiscount };
