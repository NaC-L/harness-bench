'use strict';
const { parseInvoice } = require('./parse');
const { product, sum, difference } = require('./money');
const { applyDiscounts } = require('./discounts');
const { allocateDiscount } = require('./allocation');
const { calculateTaxes } = require('./tax');

/**
 * buildInvoice(input) -> a new invoice breakdown. See parse.js for the input
 * schema, discounts.js for sequential discounts, rounding.js for exact half-even
 * cents, allocation.js for remainder/tie rules, and tax.js for both tax modes.
 *
 * Pipeline: multiply unitCents by quantity; apply each line's discount list;
 * compute the invoice discount against the SUM OF POSITIVE remaining balances
 * (only when invoice discounts are present); apply the invoice discount list
 * to that basis; allocate the resulting aggregate reduction ONCE across those
 * positive balances; compute tax. Credits are excluded from invoice discounts
 * but still contribute to all signed totals and their tax-rate group.
 *
 * Output lines preserve input order and contain currency, unitCents, quantity,
 * grossCents, discountCents, netCents, taxBps, taxCents, totalCents. The returned
 * invoice contains currency, taxMode, lines, subtotalCents (sum of gross),
 * discountCents (sum of signed gross - net, including both discount levels),
 * netCents, taxCents and totalCents. Each total equals the sum of corresponding
 * line values. For credits discountCents may be negative. Empty invoices return
 * zero totals and no lines. Nothing is mutated and returned zero amounts are +0.
 *
 * All input amounts and stored calculated fields are safe integer Numbers;
 * exact arithmetic must precede safe-range checks. Reject unsafe line products,
 * discount bases, calculated fields or totals with RangeError, never silently
 * round an overflowing value. Intermediate products/sums may exceed the safe
 * range provided the stored final result is safe (e.g. cancelling credits).
 */
function buildInvoice(input) {
  const parsed = parseInvoice(input);
  const prepared = parsed.lines.map(line => {
    const grossCents = product(line.unitCents, line.quantity, 'line gross');
    return { ...line, grossCents, netCents: applyDiscounts(grossCents, line.discounts) };
  });
  const weights = prepared.map(line => Math.max(0, line.netCents));
  let invoiceReduction = 0;
  if (parsed.discounts.length > 0) {
    const basis = sum(weights, 'invoice discount basis');
    invoiceReduction = difference(basis, applyDiscounts(basis, parsed.discounts));
  }
  const shares = allocateDiscount(invoiceReduction, weights);
  prepared.forEach((line, index) => { line.netCents = difference(line.netCents, shares[index]); });
  const taxes = calculateTaxes(prepared, parsed.taxMode);
  const lines = prepared.map((line, index) => ({
    currency: line.currency,
    unitCents: line.unitCents,
    quantity: line.quantity,
    grossCents: line.grossCents,
    discountCents: difference(line.grossCents, line.netCents),
    netCents: line.netCents,
    taxBps: line.taxBps,
    taxCents: taxes[index],
    totalCents: sum([line.netCents, taxes[index]], 'line total'),
  }));
  const subtotalCents = sum(lines.map(line => line.grossCents), 'subtotal');
  const netCents = sum(lines.map(line => line.netCents), 'net total');
  const taxCents = sum(taxes, 'tax total');
  return {
    currency: parsed.currency,
    taxMode: parsed.taxMode,
    lines,
    subtotalCents,
    discountCents: difference(subtotalCents, netCents, 'discount total'),
    netCents,
    taxCents,
    totalCents: sum(lines.map(line => line.totalCents), 'invoice total'),
  };
}

module.exports = { buildInvoice };
