'use strict';

const { ExprError } = require('./errors');

/** Convert source to positioned tokens without repeatedly slicing its suffix. */
function tokenize(source) {
  const tokens = [];
  const number = /(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/y;
  const identifier = /[A-Za-z_][A-Za-z0-9_]*/y;
  let offset = 0;
  while (offset < source.length) {
    const column = offset + 1;
    while (offset < source.length && /\s/.test(source[offset])) offset += 1;
    if (offset === source.length) break;
    number.lastIndex = offset;
    const numeric = number.exec(source);
    if (numeric) {
      tokens.push({ type: 'number', value: Number(numeric[0]), column });
      offset = number.lastIndex;
      continue;
    }
    identifier.lastIndex = offset;
    const name = identifier.exec(source);
    if (name) {
      tokens.push({ type: 'identifier', value: name[0], column });
      offset = identifier.lastIndex;
      continue;
    }
    const pair = source.slice(offset, offset + 2);
    if (['**', '//', '<=', '>=', '==', '!='].includes(pair)) {
      tokens.push({ type: 'operator', value: pair, column });
      offset += 2;
    } else if ('+-*/%<>() ,'.includes(source[offset]) && source[offset] !== ' ') {
      tokens.push({ type: 'operator', value: source[offset], column });
      offset += 1;
    } else {
      throw new ExprError('Unexpected character', column);
    }
  }
  tokens.push({ type: 'eof', value: '', column: source.length + 1 });
  return tokens;
}

module.exports = { tokenize };
