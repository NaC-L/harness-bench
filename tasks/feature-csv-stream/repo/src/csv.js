'use strict';
const { toObjects } = require('./rows');

/**
 * Create an incremental CSV parser; options is an optional object.
 *
 * delimiter defaults to ',' when omitted or undefined. It must be a string of
 * length 1 (one UTF-16 code unit), other than '"', '\r', or '\n'; otherwise throw
 * RangeError at creation. No trimming, coercion, or delimiter auto-detection.
 *
 * push(chunk) accepts only strings (otherwise TypeError). It returns string[][]
 * containing ONLY the records completed by this call, in order, never records
 * returned by an earlier call. A record is completed immediately at an outside-
 * quote LF or CR, even if the LF of a CRLF has not arrived yet. An unfinished
 * record stays buffered. Empty chunks do nothing, including before a BOM.
 *
 * end() finishes input and returns the last record if input has an unfinished
 * one; otherwise returns []. Calling end again returns []. Any push after end,
 * even push(''), throws Error. Separate parsers have independent state.
 *
 * CSV grammar:
 * - A delimiter ends a field. Empty fields, including trailing ones, are kept.
 * - '"' opens a quoted field only as the FIRST character of a field. Quotes in
 *   an unquoted field are literal characters, not an error or a quoting toggle.
 * - In a quoted field, '""' produces one literal '"'. Delimiters, CR, LF, and
 *   CRLF inside quotes are preserved exactly, not normalized or treated as
 *   separators. The next '"' not part of a doubled quote closes the field.
 * - After a closing quote only delimiter, LF, CR, or EOF is legal. Any other
 *   character, including whitespace, throws SyntaxError during push().
 * - Outside quotes, LF, CRLF, and lone CR end records. CRLF is ONE separator,
 *   even across chunks. Every separator emits the current row, even if empty:
 *   '\n' is [['']], '\n\n' is [[''], ['']], and 'a\n' is [['a']]. EOF after a
 *   separator adds nothing. Empty input or BOM-only input produces [].
 * - Strip one U+FEFF BOM only if it is the first character of all input. Later
 *   BOMs are ordinary field data. A BOM is supplied as a whole character.
 *
 * Every SyntaxError message contains 'line N', where N is the 1-based PHYSICAL
 * line at the offending character, or the line at EOF for an unterminated quote.
 * Count CR and LF inside quoted fields too; each CRLF counts as one newline,
 * regardless of chunk boundaries. A lone CR or LF counts as one newline.
 * end() throws SyntaxError for an unterminated quoted field. No recovery behavior
 * is required after a SyntaxError. Chunk boundaries may otherwise fall anywhere,
 * including inside an escaped '""', CRLF, or a Unicode surrogate pair.
 *
 * options.header does not affect this streaming API: it always yields arrays.
 * @param {{ delimiter?: string, header?: boolean }} [options]
 * @returns {{ push(chunk: string): string[][], end(): string[][] }}
 */
function createParser(options = {}) {
  throw new Error('not implemented');
}

/**
 * Parse all text using the same grammar and validation as createParser.
 * With options.header === true, convert records with the existing
 * toObjects(records, { header: true }) helper; otherwise return string[][].
 * Empty input yields [] in either mode. Do not change the helper's contract.
 */
function parse(text, options = {}) {
  const parser = createParser(options);
  const records = parser.push(text).concat(parser.end());
  return options.header === true ? toObjects(records, { header: true }) : records;
}

module.exports = { createParser, parse };
