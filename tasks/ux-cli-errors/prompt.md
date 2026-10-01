Repair this dependency-free unit conversion CLI so users get correct conversions and useful, predictable help and errors. Use Node.js 22 and the existing ESM layout: `bin/convert.js` is the executable entrypoint, `src/cli.js` exports `main(argv, io)`, and `src/units.js` supplies conversions. Do not modify `test/**/*` or `package.json`, install dependencies, or use the network.

`main(argv, io)` receives only the user arguments (not the Node executable or script path). `io.stdout` and `io.stderr` are writable streams exposing `write(text)`. It must return a numeric exit code, not call `process.exit`, and not throw for any usage error. The executable must pass through that code and use the real stdout/stderr streams.

Supported commands:
- `node bin/convert.js convert <value> <from> <to> [--precision N]`
- `node bin/convert.js units`
- `node bin/convert.js --help` or `node bin/convert.js -h`
- `node bin/convert.js --version`

Help/version/units are standalone commands; additional arguments are errors. Help goes only to stdout, exits 0, includes usage for all commands and runnable `node bin/convert.js ...` examples for conversion and explicit precision. Every example shown must work. Version prints `1.0.0\n` only to stdout and exits 0. Units prints the supported canonical symbols grouped into length, mass, and temperature only to stdout and exits 0; exact list formatting is otherwise your choice.

Conversion rules:
- Value is one complete finite decimal number: optional `+`/`-`, digits with an optional decimal point (including `1.` and `.5`), and an optional signed `e`/`E` exponent. Reject empty/whitespace-containing values, trailing junk, hexadecimal/binary forms, underscores, NaN, Infinity, and exponents that overflow to infinity. Do not partially parse a token.
- Units are case-insensitive but output uses lowercase canonical symbols. Length table order: `m`, `km`, `cm`, `mm`, `mi`, `ft`, `in`; mass: `kg`, `g`, `lb`, `oz`; temperature: `c`, `f`, `k`. No aliases beyond these symbols. Reject conversion across dimensions.
- Length factors in meters are 1, 1000, 0.01, 0.001, 1609.344, 0.3048, and 0.0254 respectively. Mass factors in grams are 1000, 1, 453.59237, and 28.349523125 respectively. Temperature uses ordinary affine formulas: F = C * 9 / 5 + 32 and K = C + 273.15. Negative values, including negative temperatures, must retain their sign and are allowed even below absolute zero; no physical-range validation is required.
- Precision defaults to 2. The only conversion option is a single trailing `--precision N`, where N consists of decimal digits and its numeric value is an integer from 0 through 6 inclusive (leading zeros are allowed). Reject missing values, fractions, signed values, exponent/hex notation, and out-of-range precision. Neither `--precision=N` nor option placement before the three operands is supported.
- Successful conversion exits 0, writes exactly `${converted.toFixed(precision)} ${canonicalTarget}\n` to stdout, and leaves stderr empty. Preserve working conversions and rounding; use normal JavaScript Number/toFixed behavior.

All usage errors exit 2, leave stdout empty, and write a readable message to stderr only, with no exception stack or internal source path. Include the offending argument and a useful reason (for absent arguments, name what is missing), plus a `--help` hint. This includes no command, unknown commands, extra/missing operands, unknown flags, missing precision, invalid numbers/precision, unknown units, and incompatible dimensions. A negative numeric operand is a value, not a flag.

For an unknown source or target unit, also suggest the closest supported canonical symbol if its case-insensitive Levenshtein edit distance is at most 2. Choose the lowest distance, breaking ties by the full table order given above; if none qualifies, do not suggest a unit. For the misspelled flag `--precison`, suggest `--precision`. Error wording is otherwise flexible: clarity and the stream/exit-code contract matter, not one exact sentence.

The visible tests are intentionally incomplete. Hidden checks cover the same stated contract, including error handling and regressions in already working conversions. Repair the implementation rather than changing tests or weakening checks.
