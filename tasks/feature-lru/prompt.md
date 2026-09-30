Implement the CommonJS named export `LRUCache` in `src/lru.js`.

`new LRUCache(capacity)` accepts only a positive integer Number. Throw `RangeError`
for all other capacities (including zero, negatives, fractions, Infinity, NaN,
strings, and omitted values).

The cache supports arbitrary JavaScript keys and values using Map key semantics.
- `get(key)`: return the stored value, or `undefined` if absent. A successful get
  refreshes that entry to most recently used, including when its value is undefined.
- `set(key, value)`: insert or update and mark most recently used. If capacity is
  exceeded, evict the least recently used entry. Updating an existing entry must
  not evict an unrelated entry or increase size. Return this cache for chaining.
- `has(key)`: return a boolean without changing recency.
- `delete(key)`: remove the entry and return true if it existed, otherwise false.
  Deletion does not change the relative recency of surviving entries.
- `size`: a getter returning the current number of entries.

Caches are independent. Do not add dependencies or change the exported API.
Work only in the current directory. Do not modify `test/` or `package.json`.
Verify with `node --test`.
