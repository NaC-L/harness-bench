'use strict';
const { roundRatio } = require('./rounding');
const { distribute } = require('./allocation');

/**
 * Tax is applied after ALL line and invoice discounts.
 * 'line': independently half-even round each netCents * taxBps / 10000.
 * 'invoice': group lines by taxBps; independently half-even round each group's
 * signed exact tax sum, then distribute that group tax using signed largest
 * remainders (see allocation.js). Credit lines belong to their rate's group,
 * even if the group's net basis is zero or negative. Do not group different
 * rates together or allocate group tax proportionally to a net group total.
 * Return taxes in original line order. Invoice tax is the sum of line taxes.
 */
function calculateTaxes(lines, taxMode) {
  const numerators = lines.map(line => BigInt(line.netCents) * BigInt(line.taxBps));
  if (taxMode === 'line') return numerators.map(value => roundRatio(value, 10000n));
  const groups = new Map();
  lines.forEach((line, index) => {
    if (!groups.has(line.taxBps)) groups.set(line.taxBps, []);
    groups.get(line.taxBps).push(index);
  });
  const taxes = lines.map(() => 0);
  for (const indexes of groups.values()) {
    const ideals = indexes.map(index => numerators[index]);
    const groupTax = roundRatio(ideals.reduce((sum, value) => sum + value, 0n), 10000n);
    const allocated = distribute(groupTax, ideals, 10000n);
    indexes.forEach((index, offset) => { taxes[index] = allocated[offset]; });
  }
  return taxes;
}

module.exports = { calculateTaxes };
