The tests for `src/limit.js` fail or hang, and nobody knows why. Investigate the
implementation, find the root cause, and fix it. Keep the CommonJS named export
`createLimiter` and its intended behavior described in the source and tests.
Do not add dependencies.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify the fix with `node --test`.
