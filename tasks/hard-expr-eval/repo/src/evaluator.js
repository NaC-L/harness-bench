'use strict';

const { ExprError } = require('./errors');

function apply(operator, left, right) {
  left = Number(left);
  right = Number(right);
  const value = operator.value;
  if ((value === '/' || value === '//' || value === '%') && right === 0) {
    throw new ExprError('Division by zero', operator.column);
  }
  switch (value) {
    case '+': return left + right;
    case '-': return left - right;
    case '*': return left * right;
    case '/': return left / right;
    case '**': return left ** right;
    case '//': {
      const quotient = Math.trunc(left / right);
      return quotient === 0 ? 0 : quotient;
    }
    case '%': {
      const remainder = left % right;
      if (remainder === 0) return 0;
      return remainder;
    }
    case '<': return left < right;
    case '<=': return left <= right;
    case '>': return left > right;
    case '>=': return left >= right;
    case '==': return left === right;
    case '!=': return left !== right;
    default: throw new Error('Invalid AST operator');
  }
}

/** Evaluate with explicit frames, so a long left-deep binary tree is safe. */
function evaluateAst(root, variables) {
  const frames = [{ node: root, phase: 0 }];
  let result;
  while (frames.length) {
    const frame = frames[frames.length - 1];
    const node = frame.node;
    if (node.type === 'number') {
      result = node.value;
      frames.pop();
    } else if (node.type === 'variable') {
      if (!Object.prototype.hasOwnProperty.call(variables, node.name)) {
        throw new ExprError('Unknown variable', node.column);
      }
      result = variables[node.name];
      frames.pop();
    } else if (node.type === 'unary') {
      if (frame.phase === 0) {
        frame.phase = 1;
        frames.push({ node: node.operand, phase: 0 });
      } else {
        result = node.operator.value === '-' ? -Number(result) : Number(result);
        frames.pop();
      }
    } else if (node.type === 'binary') {
      if (frame.phase === 0) {
        frame.phase = 1;
        frames.push({ node: node.left, phase: 0 });
      } else if (frame.phase === 1) {
        frame.left = result;
        frame.phase = 2;
        frames.push({ node: node.right, phase: 0 });
      } else {
        result = apply(node.operator, frame.left, result);
        frames.pop();
      }
    } else if (node.type === 'comparison') {
      if (frame.phase === 0) {
        frame.phase = 1;
        frames.push({ node: node.operands[0], phase: 0 });
      } else if (frame.phase === 1) {
        frame.left = result;
        frame.index = 0;
        frame.phase = 2;
        frames.push({ node: node.operands[1], phase: 0 });
      } else {
        const right = result;
        if (!apply(node.operators[frame.index], frame.left, right)) {
          result = false;
          frames.pop();
        } else if (frame.index + 1 === node.operators.length) {
          result = true;
          frames.pop();
        } else {
          frame.left = right;
          frame.index += 1;
          frames.push({ node: node.operands[frame.index + 1], phase: 0 });
        }
      }
    } else if (node.type === 'call') {
      if (frame.phase === 0) {
        frame.phase = 1;
        frame.index = 0;
        frames.push({ node: node.args[0], phase: 0 });
      } else {
        const value = Number(result);
        if (frame.index === 0) frame.value = value;
        else if (node.name === 'min') frame.value = Math.min(frame.value, value);
        else frame.value = Math.max(frame.value, value);
        frame.index += 1;
        if (frame.index === node.args.length) {
          result = node.name === 'abs' ? Math.abs(frame.value) : frame.value;
          frames.pop();
        } else {
          frames.push({ node: node.args[frame.index], phase: 0 });
        }
      }
    } else {
      throw new Error('Invalid AST node');
    }
  }
  return result;
}

module.exports = { evaluateAst };
