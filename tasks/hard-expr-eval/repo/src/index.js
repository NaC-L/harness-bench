'use strict';

const { tokenize } = require('./tokenizer');
const { parse } = require('./parser');
const { evaluateAst } = require('./evaluator');
const { ExprError } = require('./errors');

/**
 * evaluate(source, variables = {}) evaluates one complete arithmetic formula.
 * The source is a string. Whitespace separates tokens and is otherwise ignored.
 * Numbers are nonnegative literals: integers, decimals (1.5, .5, 5.), and an
 * optional e/E exponent with an optional sign (1.5e-3). Signs are unary operators.
 * Identifiers match [A-Za-z_][A-Za-z0-9_]* and read own properties of variables.
 * Supplied variable values are numbers. An unknown variable raises ExprError at
 * its identifier. Each occurrence is read once, in left-to-right evaluation
 * order; getter-backed properties are supported. No variable object is mutated.
 *
 * Parentheses group expressions. Calls are only to built-ins min, max, and abs.
 * min/max take one or more comma-separated expressions; abs takes exactly one.
 * Arguments are evaluated left to right. Unknown calls and wrong argument counts
 * are syntax errors (detected while parsing, before anything is evaluated) and
 * raise ExprError at the function identifier. There are no implicit products,
 * assignments, strings, user-defined functions, or trailing argument commas.
 *
 * Binary operators are + - * / // % **. + and - have equal precedence; *, /,
 * // and % share the next higher precedence. These operators associate left.
 * Unary + and - bind below ** on its left, while the right operand of ** may
 * have a unary sign: -2 ** 2 is -4 and 2 ** -1 is 0.5. ** associates right:
 * 2 ** 3 ** 2 is 512. Thus the grammar is:
 *   comparison := sum (('<' | '<=' | '>' | '>=' | '==' | '!=') sum)*
 *   sum        := product (('+' | '-') product)*
 *   product    := unary (('*' | '/' | '//' | '%') unary)*
 *   unary      := ('+' | '-') unary | power
 *   power      := primary ('**' unary)?
 *   primary    := number | identifier | '(' comparison ')'
 *                 | identifier '(' comparison (',' comparison)* ')'
 * The call grammar is subject to the arity restrictions above.
 *
 * Comparisons have lower precedence than arithmetic and produce booleans.
 * They chain, rather than comparing an intermediate boolean: a < b <= c means
 * a < b and b <= c. Shared operands are evaluated once. A false comparison
 * short-circuits the remaining operands (but the whole source is parsed first).
 * Parenthesized comparison results used in arithmetic are numbers 0/1, as in
 * Python; numeric equality likewise treats these booleans as 0/1.
 *
 * // is floor division, not truncation; % has the divisor's sign unless zero.
 * For integer inputs, a == (a // b) * b + (a % b), so -7 // 2 is -4,
 * -7 % 3 is 2, and 7 % -3 is -2. Zero results of // and % are positive zero.
 * /, // and % with a zero divisor raise ExprError at the operator token.
 * Arithmetic otherwise uses JavaScript Number precision, not arbitrary-precision
 * Python integers. Inputs/results need not emulate Python overflow exceptions.
 *
 * Syntax errors and invalid characters raise ExprError with .column: the 1-based
 * UTF-16 offset of the offending token; unexpected end is source.length + 1,
 * including trailing whitespace. Error message wording is not part of the API.
 * Tokenization, parsing and evaluation must stay linear in the formula length
 * for long flat arithmetic and comparison chains: a formula with 100,000+
 * operands must evaluate in well under a second and must not recurse once per
 * operand. Deeply nested parentheses or ** chains may be limited by the stack.
 */
function evaluate(source, variables = {}) {
  return evaluateAst(parse(tokenize(source)), variables);
}

module.exports = { evaluate, ExprError };
