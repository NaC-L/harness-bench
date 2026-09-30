Fix `src/duration.js`, which exports `parseDuration(str)` as a CommonJS named export.
It must convert complete duration strings into milliseconds, not just one part.

The grammar is one or more adjacent amount-unit parts. An amount is one or more
ASCII digits, optionally followed by a decimal point and one or more digits.
Units are case-sensitive `ms`, `s`, `m`, `h`, and `d` (a day is exactly 24 hours).
Parts may repeat units and appear in any order; add their durations. Leading and
trailing whitespace is allowed, but whitespace between parts is not. Zero and
fractional millisecond results are valid. Use ordinary JavaScript Number arithmetic.
Examples: `1h30m` -> 5400000, `45s` -> 45000, `2d4h` -> 187200000,
`1.5h` -> 5400000, and `250ms` -> 250.

Throw `TypeError` for non-string inputs, empty strings, malformed input, unknown
units, or a non-finite result. Do not partially accept a malformed string.
Do not add dependencies or change the exported API.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify your fix with `node --test`.
