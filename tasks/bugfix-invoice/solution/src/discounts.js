'use strict';
const { roundRatio } = require('./rounding');
const { difference } = require('./money');

/**
 * Apply an already-validated discount list strictly in its supplied order.
 * Each percent discount rounds CURRENT_AMOUNT * rateBps / 10000 to half-even
 * integer cents, then subtracts that rounded discount. Do not instead round the
 * remaining amount, combine percentages, or defer rounding until the end.
 * This also reduces the magnitude of a credit: percentage discount amounts are
 * signed. Fixed discounts affect only positive balances and cap at zero;
 * fixed discounts never change credits. A zero balance remains zero.
 * Called for both line discounts and the positive invoice-discount basis.
 */
function applyDiscounts(amountCents, discounts) {
  let current = amountCents;
  for (const discount of discounts) {
    if (discount.type === 'fixed') {
      if (current > 0) current -= Math.min(current, discount.amountCents);
    } else {
      const reduction = roundRatio(BigInt(current) * BigInt(discount.rateBps), 10000n);
      current = difference(current, reduction, 'discounted amount');
    }
  }
  return current === 0 ? 0 : current;
}

module.exports = { applyDiscounts };
