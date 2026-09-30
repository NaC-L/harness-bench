'use strict';

/**
 * Versions are canonical MAJOR.MINOR.PATCH strings: three non-negative safe
 * integers with no leading zeroes, suffixes, or whitespace. parse returns their
 * numeric triple; compare accepts version strings and returns -1, 0, or 1.
 *
 * Ranges are strings containing one or more whitespace-separated AND terms:
 * exact versions, *, ^version, ~version, >=version, >version, <=version, or
 * <version. Surrounding whitespace is ignored; empty ranges are invalid.
 * Caret is >= the base and < the next major, except that a zero major uses the
 * next minor, or the next patch when both major and minor are zero. Tilde is
 * >= the base and < the next minor. Invalid versions/ranges throw TypeError.
 */
function parse(version) {
  if (typeof version !== 'string' || !/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version)) {
    throw new TypeError('Invalid version');
  }
  const parts = version.split('.').map(Number);
  if (!parts.every(Number.isSafeInteger)) throw new TypeError('Invalid version');
  return parts;
}

function compareParts(left, right) {
  for (let i = 0; i < 3; i += 1) {
    if (left[i] !== right[i]) return left[i] < right[i] ? -1 : 1;
  }
  return 0;
}

function compare(left, right) {
  return compareParts(parse(left), parse(right));
}

// Internal compiled predicates also let the resolver validate every range once.
function compileRange(range) {
  if (typeof range !== 'string' || range.trim() === '') throw new TypeError('Invalid range');
  const terms = range.trim().split(/\s+/).map(term => {
    if (term === '*') return () => true;
    const match = /^(\^|~|>=|<=|>|<)?(.+)$/.exec(term);
    if (!match) throw new TypeError('Invalid range');
    const operator = match[1] || '';
    const base = parse(match[2]);
    if (operator === '^' || operator === '~') {
      const upper = operator === '~' ? [base[0], base[1] + 1, 0]
        : base[0] !== 0 ? [base[0] + 1, 0, 0]
          : base[1] !== 0 ? [0, base[1] + 1, 0] : [0, 0, base[2] + 1];
      return version => compareParts(version, base) >= 0 && compareParts(version, upper) < 0;
    }
    return version => {
      const order = compareParts(version, base);
      switch (operator) {
        case '': return order === 0;
        case '>=': return order >= 0;
        case '>': return order > 0;
        case '<=': return order <= 0;
        case '<': return order < 0;
        default: throw new TypeError('Invalid range');
      }
    };
  });
  return version => terms.every(term => term(version));
}

function satisfies(version, range) {
  const parts = parse(version);
  return compileRange(range)(parts);
}

module.exports = { parse, compare, satisfies, compileRange };
