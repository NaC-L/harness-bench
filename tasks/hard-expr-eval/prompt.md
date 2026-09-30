The finance team's spreadsheet formulas are supposed to give the same answers as
Python, but several results differ from what Python prints, and some error
reports point at the wrong place in the formula. The visible test captures one
reported mismatch; the full language contract is documented in `src/index.js`.

Fix the evaluator so it matches that contract. Keep the public API
(`evaluate(source, variables)` and `ExprError` exported from `src/index.js`) and
do not add dependencies. Some formulas are very long, so evaluation must stay fast.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify the fix with `node --test`.
