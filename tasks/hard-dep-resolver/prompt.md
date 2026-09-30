CI installs sometimes pick older versions, or report "no solution" for dependency
sets that a teammate resolved by hand. The visible reproduction covers one
install, but the root cause is unknown. Investigate `src/` and repair the resolver
against the contracts in `src/resolver.js` and `src/semver.js`, including its
specified first-found selection rule. Preserve the CommonJS named export
`resolve(registry, root)` in `src/index.js` and the semver helpers' API.
Do not add dependencies. Registries may contain cycles and long dependency
chains; resolution must terminate without relying on recursive call-stack depth
or enumerating a whole Cartesian product before checking constraints.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify the fix with `node --test`.
