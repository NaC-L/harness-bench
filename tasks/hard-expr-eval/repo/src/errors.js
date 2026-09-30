'use strict';

/** A formula error, positioned at a 1-based UTF-16 source column. */
class ExprError extends Error {
  constructor(message, column) {
    super(message);
    this.name = 'ExprError';
    this.column = column;
  }
}

module.exports = { ExprError };
