'use strict';

const { ExprError } = require('./errors');

/** Parse a complete token sequence into an AST. Nodes retain operator columns. */
function parse(tokens) {
  let position = 0;
  const current = () => tokens[position];
  const take = () => tokens[position++];
  const is = value => current().value === value;
  const expect = value => {
    if (!is(value)) throw new ExprError(`Expected ${value}`, current().column);
    return take();
  };
  const binary = (operator, left, right) => ({ type: 'binary', operator, left, right });

  function comparison() {
    let left = sum();
    while (['<', '<=', '>', '>=', '==', '!='].includes(current().value)) {
      const operator = take();
      left = binary(operator, left, sum());
    }
    return left;
  }

  function sum() {
    let left = product();
    while (is('+') || is('-')) {
      const operator = take();
      left = binary(operator, left, product());
    }
    return left;
  }

  function product() {
    let left = power();
    while (['*', '/', '//', '%'].includes(current().value)) {
      const operator = take();
      left = binary(operator, left, power());
    }
    return left;
  }

  function unary() {
    if (is('+') || is('-')) {
      return { type: 'unary', operator: take(), operand: unary() };
    }
    return primary();
  }

  function power() {
    let left = unary();
    while (is('**')) {
      const operator = take();
      left = binary(operator, left, unary());
    }
    return left;
  }

  function primary() {
    const token = take();
    if (token.type === 'number') return { type: 'number', value: token.value };
    if (token.type === 'identifier') {
      if (!is('(')) return { type: 'variable', name: token.value, column: token.column };
      take();
      const args = [];
      if (!is(')')) {
        args.push(comparison());
        while (is(',')) {
          take();
          args.push(comparison());
        }
      }
      expect(')');
      if (!['min', 'max', 'abs'].includes(token.value)) {
        throw new ExprError('Unknown function', token.column);
      }
      if (!args.length || (token.value === 'abs' && args.length !== 1)) {
        throw new ExprError('Wrong argument count', token.column);
      }
      return { type: 'call', name: token.value, args };
    }
    if (token.value === '(') {
      const expression = comparison();
      expect(')');
      return expression;
    }
    throw new ExprError('Expected an expression', token.column);
  }

  const expression = comparison();
  if (current().type !== 'eof') throw new ExprError('Unexpected token', current().column);
  return expression;
}

module.exports = { parse };
