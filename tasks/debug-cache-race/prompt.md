Production occasionally serves an old value after a cache key was invalidated.
The visible test reproduces one ordering, but the problem is intermittent and its
root cause is unknown. Investigate `src/`, fix the race, and check the related
failure and mutation paths against the contract in `src/cache.js`. Preserve the
CommonJS named export `createCache`, its API, and concurrent load deduplication.
Do not add dependencies. The cache uses an injectable clock; do not introduce
real timers or sleeps.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify the fix with `node --test`.
