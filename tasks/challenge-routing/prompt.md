The gateway sometimes selects the wrong endpoint or applies another tenant's policy. A visible request reproduces one symptom. Repair the request dispatch path in `src/` against the public contract in `src/index.js`, preserving the existing CommonJS API and documented response shape. The router is used repeatedly by several tenants, not reconstructed for every request. Keep the fix bounded to this gateway; do not add dependencies or replace it with a framework.

Work only in the current directory. Do not modify `test/` or `package.json`. Verify with `node --test`.
