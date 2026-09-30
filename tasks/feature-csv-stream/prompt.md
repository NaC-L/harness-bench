Implement the CommonJS named export `createParser(options)` in `src/csv.js`.
Keep `parse(text, options)` and the existing `src/rows.js` helper API working.
Do not add dependencies; use plain Node 22 CommonJS.

The parser returns `{ push(chunk), end() }`. Each push returns only newly completed
records; end returns an unfinished final record, if any. Do not defer completed
records until end. See the JSDoc in `src/csv.js` for the full contract, including
validation, lifecycle, and physical line numbers.

- Comma is the default delimiter; a configurable delimiter is one UTF-16 code
  unit other than a quote, CR, or LF.
- Double quotes open a quoted field only at its beginning; quotes within an
  unquoted field are literal. Inside quotes, `""` is one literal quote. Quoted
  fields preserve delimiters and all newline characters, including CRLF.
- LF, CRLF, and lone CR separate records outside quotes. A trailing separator
  creates no extra record; an empty line is `['']`. Empty input yields no records.
- After a closing quote, only a delimiter, record separator, or EOF is allowed.
  Other text (including spaces) throws `SyntaxError` with the 1-based physical
  line number. An unterminated quote is a `SyntaxError` at end. Count newlines
  inside quoted fields too; CRLF counts once, even across chunks.
- Strip a BOM only at the very start. Chunk boundaries may occur anywhere,
  including between CR/LF or the two quotes of an escape; empty chunks are valid.
- `createParser` always yields arrays. `parse` with `header: true` uses the existing
  `toObjects` helper, whose documented duplicate-header, padding, special-key,
  and non-mutation behavior must be preserved.

Work only in the current directory. Do not modify `test/` or `package.json`.
Verify with `node --test`.
