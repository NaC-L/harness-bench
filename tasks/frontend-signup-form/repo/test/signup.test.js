import test from 'node:test';
import assert from 'node:assert/strict';
import {initialState, validate, update, render} from '../src/signup.js';
import {parse, nodes, text} from './html.js';

test('signup regression: missing name and terms remain invalid', () => {
  const errors = validate({name: '', email: 'user@example.com', password: 'Password123', confirm: 'Password123', terms: false});
  assert.ok(errors.name);
  assert.ok(errors.terms);
  assert.equal(errors.confirm, undefined);
});

test('signup visible: plus-addresses work and short passwords explain recovery', () => {
  const values = {name: ' Ada ', email: 'ada+work@example.com', password: 'x1', confirm: 'x1', terms: true};
  const errors = validate(values);
  assert.equal(errors.email, undefined);
  assert.match(errors.password, /10/);
  assert.match(errors.password, /letter/i);
  assert.match(errors.password, /digit/i);
});

test('signup visible: failed submit exposes labels and actionable alert', () => {
  const state = update(initialState(), {type: 'submit'});
  assert.equal(state.focus, 'name');
  const root = parse(render(state));
  assert.equal(nodes(root, node => node.tag === 'label').length, 5);
  const alert = nodes(root, node => node.attrs.role === 'alert')[0];
  assert.ok(alert);
  assert.match(text(alert), /email/i);
});
