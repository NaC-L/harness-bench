Our invoice previews have two billing discrepancies. A USD line for 105 cents
with 10% tax in line-tax mode currently returns 11 cents tax / 116 cents total;
it should return 10 / 115. Another 105-cent line with discounts of 50%, then
10 cents off, and 10% tax returns 47 cents net / 5 cents tax / 52 cents total;
it should return 43 / 4 / 47. The second discrepancy is not just a final-total
rounding issue.

Investigate and repair the pricing library behind `src/index.js`'s CommonJS
named export `buildInvoice`. Keep its existing API and the full contract in the
source JSDoc, including ordered discounts, exact integer-cent arithmetic,
half-even rounding, credits, allocation, both tax modes, and input validation.
Preserve behavior outside the reported cases. Do not add dependencies.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify the fix with `node --test`.
