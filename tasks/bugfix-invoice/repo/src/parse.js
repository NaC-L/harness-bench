'use strict';
const { integer } = require('./money');

function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
}

function currency(value) {
  if (typeof value !== 'string' || !/^[A-Z]{3}$/.test(value)) {
    throw new TypeError('Currency must be three uppercase ASCII letters');
  }
  return value;
}

/**
 * Missing discount arrays mean []; present arrays must contain discount objects.
 * A percent discount is { type: 'percent', rateBps: integer in [0, 10000] }.
 * A fixed discount is { type: 'fixed', amountCents: nonnegative safe integer }.
 * Basis points are hundredths of one percent: 5000 is 50%, 1000 is 10%.
 * Unknown types/invalid structures throw TypeError; invalid numbers throw
 * RangeError. Extra object properties are ignored. Parse every entry even if
 * the amount being discounted is zero. Return copies, not input references.
 */
function parseDiscounts(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) throw new TypeError('Discounts must be an array');
  return value.map(discount => {
    object(discount, 'Discount');
    if (discount.type === 'percent') {
      return { type: 'percent', rateBps: integer(discount.rateBps, 'rateBps', 0, 10000) };
    }
    if (discount.type === 'fixed') {
      return { type: 'fixed', amountCents: integer(discount.amountCents, 'amountCents', 0) };
    }
    throw new TypeError('Unknown discount type');
  });
}

/**
 * An invoice needs currency and a lines array (which may be empty). taxMode is
 * 'line' by default, or 'invoice'; invalid modes throw RangeError. Each line
 * needs signed safe-integer unitCents; quantity defaults to 1 and must be a
 * nonnegative safe integer. taxBps defaults to 0 and is in [0, 10000]. A missing
 * line currency inherits the invoice currency. All currencies must match;
 * mismatches throw RangeError, including on zero-quantity/zero-price lines.
 * Validate all fields on zero lines too. Null is not a missing/default value.
 * Structural/currency-format errors throw TypeError, numeric errors RangeError.
 * Parsing and subsequent calculations never mutate the caller's objects.
 */
function parseInvoice(input) {
  object(input, 'Invoice');
  const code = currency(input.currency);
  const taxMode = input.taxMode === undefined ? 'line' : input.taxMode;
  if (taxMode !== 'line' && taxMode !== 'invoice') throw new RangeError('Unknown tax mode');
  if (!Array.isArray(input.lines)) throw new TypeError('Lines must be an array');
  const discounts = parseDiscounts(input.discounts);
  const lines = input.lines.map(line => {
    object(line, 'Line');
    const lineCurrency = line.currency === undefined ? code : currency(line.currency);
    if (lineCurrency !== code) throw new RangeError('Mixed currencies are not supported');
    return {
      currency: lineCurrency,
      unitCents: integer(line.unitCents, 'unitCents'),
      quantity: integer(line.quantity === undefined ? 1 : line.quantity, 'quantity', 0),
      taxBps: integer(line.taxBps === undefined ? 0 : line.taxBps, 'taxBps', 0, 10000),
      discounts: parseDiscounts(line.discounts),
    };
  });
  return { currency: code, taxMode, discounts, lines };
}

module.exports = { parseDiscounts, parseInvoice };
