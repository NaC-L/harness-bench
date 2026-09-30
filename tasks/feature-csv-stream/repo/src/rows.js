'use strict';

/**
 * Convert string[][] records into ordinary objects without mutating any input.
 * options.header omitted, undefined, or true: consume the first record as names;
 * an empty input or header-only input returns []. An array header supplies the
 * names explicitly instead, consuming no records. Other header values throw
 * TypeError. Header entries are strings; records and options must not be null.
 *
 * Names are made unique left-to-right. Keep a name if unused; otherwise append
 * '_2', '_3', ... to that original name until the first unused name is found.
 * Example: ['x', 'x', 'x_2', 'x'] -> ['x', 'x_2', 'x_2_2', 'x_3'].
 * An empty name is valid. All names (including '__proto__', 'constructor', and
 * 'toString') are own enumerable writable data properties; output objects still
 * have Object.prototype as their prototype.
 *
 * Pad missing cells with ''. Ignore cells beyond the number of header names.
 * Explicit [] headers produce one empty object per input record. Never alter
 * the records, rows, explicit header array, or options, including frozen inputs.
 */
function toObjects(records, options = {}) {
  const header = options.header;
  if (header !== undefined && header !== true && !Array.isArray(header)) {
    throw new TypeError('header must be true or an array');
  }
  const explicit = Array.isArray(header);
  if (!explicit && records.length === 0) return [];
  const names = explicit ? header : records[0];
  const used = new Set();
  const keys = names.map(name => {
    let key = name;
    let suffix = 2;
    while (used.has(key)) key = `${name}_${suffix++}`;
    used.add(key);
    return key;
  });
  return records.slice(explicit ? 0 : 1).map(cells => {
    const object = {};
    keys.forEach((key, index) => {
      Object.defineProperty(object, key, {
        value: index < cells.length ? cells[index] : '',
        enumerable: true,
        configurable: true,
        writable: true,
      });
    });
    return object;
  });
}

module.exports = { toObjects };
