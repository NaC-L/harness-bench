'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { buildInvoice } = require('../src');

test('reported preview rounds a 10.5-cent line tax to 10 cents', () => {
  const result = buildInvoice({ currency: 'USD', lines: [{ unitCents: 105, taxBps: 1000 }] });
  assert.deepEqual(result, {
    currency: 'USD', taxMode: 'line',
    lines: [{ currency: 'USD', unitCents: 105, quantity: 1, grossCents: 105,
      discountCents: 0, netCents: 105, taxBps: 1000, taxCents: 10, totalCents: 115 }],
    subtotalCents: 105, discountCents: 0, netCents: 105, taxCents: 10, totalCents: 115,
  });
});

test('reported preview applies 50 percent before the ten-cent coupon', () => {
  const result = buildInvoice({ currency: 'USD', lines: [{
    unitCents: 105, taxBps: 1000,
    discounts: [{ type: 'percent', rateBps: 5000 }, { type: 'fixed', amountCents: 10 }],
  }] });
  assert.deepEqual(result, {
    currency: 'USD', taxMode: 'line',
    lines: [{ currency: 'USD', unitCents: 105, quantity: 1, grossCents: 105,
      discountCents: 62, netCents: 43, taxBps: 1000, taxCents: 4, totalCents: 47 }],
    subtotalCents: 105, discountCents: 62, netCents: 43, taxCents: 4, totalCents: 47,
  });
});
