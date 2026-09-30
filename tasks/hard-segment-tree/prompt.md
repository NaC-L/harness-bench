Users report wrong sums, maxima, and threshold-search results after mixing range
updates in production. The root cause is unknown. The visible test reproduces
one sequence, but other workloads also disagree with the stored values.

Investigate and repair `src/range-tree.js`. Preserve the CommonJS named export
`RangeTree` and the complete API documented in its source comment, including
half-open ranges, error handling, and empty-range behavior. Keep O(log n) updates
and queries, O(n) construction and `toArray()`, and O(n) storage; a rewrite that
scans the affected range is not acceptable. Do not add dependencies.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify the fix with `node --test`.
