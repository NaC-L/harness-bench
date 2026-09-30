'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { buildInvoice } = require('../src');
const percent = rateBps => ({ type: 'percent', rateBps });
const fixed = amountCents => ({ type: 'fixed', amountCents });
const invoice = (lines, options = {}) => buildInvoice({ currency: 'USD', lines, ...options });

// Independent exact oracle for test expectations, not the library's helper.
function even(numerator, denominator = 10000n) {
  const sign = numerator < 0n ? -1n : 1n;
  const magnitude = numerator * sign;
  let result = magnitude / denominator;
  const remainder = magnitude % denominator;
  if (remainder * 2n > denominator ||
      (remainder * 2n === denominator && result % 2n !== 0n)) result += 1n;
  return Number(sign * result);
}
function conserved(result) {
  for (const [invoiceKey, lineKey] of [
    ['subtotalCents', 'grossCents'], ['discountCents', 'discountCents'],
    ['netCents', 'netCents'], ['taxCents', 'taxCents'], ['totalCents', 'totalCents'],
  ]) {
    assert.equal(BigInt(result[invoiceKey]), result.lines.reduce((sum, line) => sum + BigInt(line[lineKey]), 0n));
  }
  for (const line of result.lines) {
    assert.equal(line.grossCents - line.discountCents, line.netCents);
    assert.equal(line.netCents + line.taxCents, line.totalCents);
  }
}
function freeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

test('half-even line tax is symmetric for positive and credit half cents', () => {
  const amounts = [5, 15, 25, -5, -15, -25];
  const result = invoice(amounts.map(unitCents => ({ unitCents, taxBps: 1000 })));
  assert.deepEqual(result.lines.map(line => line.taxCents), [0, 2, 2, 0, -2, -2]);
  assert.equal(result.taxCents, 0);
  for (const line of result.lines) assert.equal(Object.is(line.taxCents, -0), false);
  conserved(result);
});

test('percent rounds the discount amount rather than the odd remaining balance', () => {
  const result = invoice([{ unitCents: 1, discounts: [percent(5000)] }]);
  assert.equal(result.lines[0].discountCents, 0);
  assert.equal(result.netCents, 1);
  assert.equal(result.totalCents, 1);
});

test('credit percentage discount preserves the signed halfway-even reduction', () => {
  const result = invoice([{ unitCents: -103, discounts: [percent(5000)] }]);
  assert.equal(result.discountCents, -52);
  assert.equal(result.netCents, -51);
  assert.equal(result.totalCents, -51);
});

test('interleaved fixed and percentage coupons keep all supplied positions', () => {
  const result = invoice([{ unitCents: 301, discounts: [fixed(1), percent(2500), fixed(10), percent(5000)] }]);
  assert.equal(result.netCents, 107);
  assert.equal(result.discountCents, 194);
  assert.equal(result.totalCents, 107);
});

test('repeated percentages are rounded separately at every stage', () => {
  const result = invoice([{ unitCents: 3, discounts: [percent(5000), percent(5000)] }]);
  assert.equal(result.netCents, 1);
  assert.equal(result.discountCents, 2);
});

test('invoice coupons use ordered positive-balance discounts and exclude credits', () => {
  const result = invoice([{ unitCents: 105 }, { unitCents: -20 }], {
    discounts: [percent(5000), fixed(10)],
  });
  assert.deepEqual(result.lines.map(line => line.netCents), [43, -20]);
  assert.deepEqual(result.lines.map(line => line.discountCents), [62, 0]);
  assert.equal(result.netCents, 23);
  conserved(result);
});

test('invoice percentage rounds once on the positive basis before allocating', () => {
  const result = invoice([{ unitCents: 1 }, { unitCents: 1 }], { discounts: [percent(2500)] });
  assert.deepEqual(result.lines.map(line => line.discountCents), [0, 0]);
  assert.equal(result.netCents, 2);
});

test('line coupons precede aggregate invoice coupons and proportional tax bases', () => {
  const result = invoice([
    { unitCents: 105, discounts: [percent(5000), fixed(10)], taxBps: 1000 },
    { unitCents: 57, taxBps: 1000 },
    { unitCents: -20, taxBps: 1000 },
  ], { discounts: [percent(1000), fixed(5)] });
  // Line nets 43,57,-20. Invoice discount 10+5 allocates 6,9,0.
  assert.deepEqual(result.lines.map(line => line.netCents), [37, 48, -20]);
  assert.deepEqual(result.lines.map(line => line.discountCents), [68, 9, 0]);
  assert.deepEqual(result.lines.map(line => line.taxCents), [4, 5, -2]);
  assert.equal(result.totalCents, 72);
  conserved(result);
});

test('invoice-tax groups round half-even independently for distinct rates', () => {
  const result = invoice([
    { unitCents: 5, taxBps: 1000 }, { unitCents: 20, taxBps: 1000 },
    { unitCents: 5, taxBps: 2000 }, { unitCents: 20, taxBps: 2000 },
  ], { taxMode: 'invoice' });
  assert.deepEqual(result.lines.map(line => line.taxCents), [0, 2, 1, 4]);
  assert.equal(result.taxCents, 7);
  assert.equal(result.totalCents, 57);
  conserved(result);
});

test('negative invoice-tax groups round signed half cents before allocation', () => {
  const result = invoice([{ unitCents: -5, taxBps: 1000 }, { unitCents: -10, taxBps: 1000 }], { taxMode: 'invoice' });
  assert.deepEqual(result.lines.map(line => line.taxCents), [-1, -1]);
  assert.equal(result.taxCents, -2);
  assert.equal(result.totalCents, -17);
  conserved(result);
});

test('large discount products retain exact cents beyond floating-point precision', () => {
  const cases = [
    [9007199254740940, 101], [9007199254740988, 3333],
    [9007199254740987, 4999], [9007199254740991, 5001],
    [9007199254740991, 9999],
  ];
  for (const [unitCents, rateBps] of cases) {
    const discount = even(BigInt(unitCents) * BigInt(rateBps));
    const result = invoice([{ unitCents, discounts: [percent(rateBps)] }]);
    assert.equal(result.discountCents, discount, `${unitCents} @ ${rateBps}`);
    assert.equal(result.netCents, Number(BigInt(unitCents) - BigInt(discount)));
    conserved(result);
  }
});

test('large tax products stay exact when the final line total is still safe', () => {
  const cases = [
    [8917136179329555, 101], [6755568330263890, 3333],
    [6005199849817214, 4999], [6004399209879899, 5001],
    [4503824818611324, 9999],
  ];
  for (const [unitCents, taxBps] of cases) {
    const result = invoice([{ unitCents, taxBps }]);
    const expected = even(BigInt(unitCents) * BigInt(taxBps));
    assert.equal(result.taxCents, expected, `${unitCents} @ ${taxBps}`);
    assert.equal(result.totalCents, Number(BigInt(unitCents) + BigInt(expected)));
    conserved(result);
  }
});

test('canceling large tax numerators preserve a small halfway-even group result', () => {
  const result = invoice([
    { unitCents: 4000000000000000, taxBps: 1000 },
    { unitCents: -4000000000000000, taxBps: 1000 },
    { unitCents: 5, taxBps: 1000 },
  ], { taxMode: 'invoice' });
  assert.deepEqual(result.lines.map(line => line.taxCents), [400000000000000, -400000000000000, 0]);
  assert.equal(result.taxCents, 0);
  assert.equal(result.totalCents, 5);
  conserved(result);
});

test('small signed percentage lattice follows exact discount-amount rounding', () => {
  for (let unitCents = -32; unitCents <= 32; unitCents += 1) {
    for (const rateBps of [0, 500, 1000, 1250, 2500, 3333, 5000, 7500, 9999, 10000]) {
      const result = invoice([{ unitCents, discounts: [percent(rateBps)] }]);
      const reduction = even(BigInt(unitCents) * BigInt(rateBps));
      assert.equal(result.discountCents, reduction, `${unitCents} @ ${rateBps}`);
      assert.equal(result.netCents, unitCents - reduction || 0);
      assert.equal(Object.is(result.netCents, -0), false);
    }
  }
});

// Regression traps: every test below already passes the untouched repository.
test('trap: line tax boundaries remain distinct from invoice tax rounding', () => {
  const lines = [{ unitCents: 104, taxBps: 1000 }, { unitCents: 104, taxBps: 1000 }];
  const perLine = invoice(lines);
  const grouped = invoice(lines, { taxMode: 'invoice' });
  assert.deepEqual(perLine.lines.map(line => line.taxCents), [10, 10]);
  assert.equal(perLine.taxCents, 20);
  assert.deepEqual(grouped.lines.map(line => line.taxCents), [11, 10]);
  assert.equal(grouped.taxCents, 21);
  conserved(perLine);
  conserved(grouped);
});

test('trap: fixed coupons cap positive amounts at zero and leave credits untouched', () => {
  const result = invoice([
    { unitCents: 7, discounts: [fixed(100), percent(10000)], taxBps: 1000 },
    { unitCents: -200, discounts: [fixed(500), percent(2500)], taxBps: 1000 },
  ], { discounts: [fixed(999)] });
  assert.deepEqual(result.lines.map(line => line.netCents), [0, -150]);
  assert.deepEqual(result.lines.map(line => line.discountCents), [7, -50]);
  assert.equal(result.taxCents, -15);
  assert.equal(result.totalCents, -165);
  conserved(result);
});

test('trap: mixed currencies are rejected even on a zero-quantity line', () => {
  assert.throws(() => invoice([{ unitCents: 100, quantity: 0, currency: 'EUR' }]), RangeError);
  assert.throws(() => invoice([{ unitCents: 0, currency: 'EUR' }], { discounts: [fixed(999)] }), RangeError);
});

test('trap: zero quantity never charges but still validates every line field', () => {
  const result = invoice([{ unitCents: Number.MAX_SAFE_INTEGER, quantity: 0, taxBps: 10000, discounts: [fixed(100)] }]);
  assert.equal(result.totalCents, 0);
  assert.equal(result.lines[0].grossCents, 0);
  assert.equal(result.lines[0].quantity, 0);
  assert.throws(() => invoice([{ unitCents: 1, quantity: 0, taxBps: 10001 }]), RangeError);
  assert.throws(() => invoice([{ unitCents: 1, quantity: 0, discounts: [percent(-1)] }]), RangeError);
  assert.throws(() => invoice([{ unitCents: 1, quantity: 0, discounts: [{ type: 'mystery' }] }]), TypeError);
  conserved(result);
});

test('trap: discount largest-remainder shares respect line index and exclude credits', () => {
  const result = invoice([{ unitCents: 101 }, { unitCents: 100 }, { unitCents: 100 }, { unitCents: -7 }], { discounts: [fixed(2)] });
  assert.deepEqual(result.lines.map(line => line.discountCents), [1, 1, 0, 0]);
  assert.deepEqual(result.lines.map(line => line.netCents), [100, 99, 100, -7]);
  assert.equal(result.totalCents, 292);
  const tied = invoice([{ unitCents: 1 }, { unitCents: 1 }, { unitCents: 1 }], { discounts: [fixed(1)] });
  assert.deepEqual(tied.lines.map(line => line.discountCents), [1, 0, 0]);
  conserved(result);
});

test('trap: signed invoice-tax allocation works when the group basis cancels to zero', () => {
  const result = invoice([{ unitCents: 5, taxBps: 1000 }, { unitCents: -5, taxBps: 1000 }], { taxMode: 'invoice' });
  assert.deepEqual(result.lines.map(line => line.taxCents), [1, -1]);
  assert.deepEqual(result.lines.map(line => line.totalCents), [6, -6]);
  assert.equal(result.taxCents, 0);
  assert.equal(result.totalCents, 0);
  conserved(result);
});

test('trap: tax allocation tie order is original index across interleaved rate groups', () => {
  const result = invoice([
    { unitCents: 14, taxBps: 1000 }, { unitCents: 7, taxBps: 2000 },
    { unitCents: 14, taxBps: 1000 }, { unitCents: 7, taxBps: 2000 },
  ], { taxMode: 'invoice' });
  assert.deepEqual(result.lines.map(line => line.taxCents), [2, 2, 1, 1]);
  assert.equal(result.taxCents, 6);
  conserved(result);
});

test('trap: frozen input graphs stay unchanged and results own fresh objects', () => {
  const input = freeze({ currency: 'USD', lines: [
    { unitCents: 100, quantity: 2, discounts: [fixed(20), percent(5000)], taxBps: 1000 },
  ], discounts: [fixed(10)] });
  const snapshot = JSON.stringify(input);
  const result = buildInvoice(input);
  assert.equal(result.totalCents, 88);
  assert.equal(JSON.stringify(input), snapshot);
  assert.notEqual(result.lines, input.lines);
  assert.notEqual(result.lines[0], input.lines[0]);
  result.lines[0].netCents = 1;
  assert.equal(input.lines[0].unitCents, 100);
});

test('trap: empty and all-credit invoices do not invent invoice discount charges', () => {
  const empty = invoice([], { taxMode: 'invoice', discounts: [fixed(999), percent(10000)] });
  assert.deepEqual(empty, { currency: 'USD', taxMode: 'invoice', lines: [], subtotalCents: 0,
    discountCents: 0, netCents: 0, taxCents: 0, totalCents: 0 });
  const credits = invoice([{ unitCents: -20 }, { unitCents: 0 }], { discounts: [percent(2500), fixed(999)] });
  assert.deepEqual(credits.lines.map(line => line.netCents), [-20, 0]);
  assert.equal(credits.discountCents, 0);
  assert.equal(credits.totalCents, -20);
});

test('trap: unsafe computed fields throw rather than silently clamp or round', () => {
  const max = Number.MAX_SAFE_INTEGER;
  assert.throws(() => invoice([{ unitCents: max, quantity: 2 }]), RangeError);
  assert.throws(() => invoice([{ unitCents: max, taxBps: 1 }]), RangeError);
  assert.throws(() => invoice([{ unitCents: max }, { unitCents: 1 }]), RangeError);
  assert.throws(() => invoice([{ unitCents: max }, { unitCents: 1 }, { unitCents: -1 }], { discounts: [fixed(0)] }), RangeError);
});

test('trap: exact signed subtotal sums may cancel an unsafe intermediate sum', () => {
  const max = Number.MAX_SAFE_INTEGER;
  const result = invoice([{ unitCents: max }, { unitCents: 2 }, { unitCents: -2 }]);
  assert.equal(result.subtotalCents, max);
  assert.equal(result.netCents, max);
  assert.equal(result.totalCents, max);
  conserved(result);
});

test('trap: malformed schemas and numeric fields keep documented error types', () => {
  for (const bad of [null, undefined, [], 1, 'invoice']) assert.throws(() => buildInvoice(bad), TypeError);
  for (const code of ['usd', 'US', 'USDD', '', 42, null]) assert.throws(() => invoice([], { currency: code }), TypeError);
  for (const taxMode of ['total', '', null, 1]) assert.throws(() => invoice([], { taxMode }), RangeError);
  assert.throws(() => invoice([], { lines: null }), TypeError);
  assert.throws(() => invoice([null]), TypeError);
  for (const bad of [null, 1.5, NaN, Infinity, '1', 1n, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => invoice([{ unitCents: bad }]), RangeError);
    assert.throws(() => invoice([{ unitCents: 1, quantity: bad }]), RangeError);
  }
  assert.throws(() => invoice([{ unitCents: 1, quantity: -1 }]), RangeError);
  assert.throws(() => invoice([{ unitCents: 1, discounts: null }]), TypeError);
  assert.throws(() => invoice([], { discounts: [fixed(-1)] }), RangeError);
  assert.throws(() => invoice([], { discounts: [percent(10001)] }), RangeError);
  assert.throws(() => invoice([], { discounts: [null] }), TypeError);
});
