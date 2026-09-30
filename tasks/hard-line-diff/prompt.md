Implement the documented line-diff module in `src/diff.js` for a code-review tool.
It needs minimal edit scripts, unified review hunks, and reliable application of
those hunks to the original lines. Preserve the three CommonJS named exports and
follow the detailed contract in the source comments, including its coordinate
and ordering rules. The already implemented `src/lines.js` provides text helpers.

Do not add dependencies. Small changes to 20,000-line files must be processed in
well under a second; use an O((N + M) · D) edit-distance algorithm rather than a
quadratic LCS table. Hidden checks include repetitive lines and patch roundtrips.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify with `node --test`.
