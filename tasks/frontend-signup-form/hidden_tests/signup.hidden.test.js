import test from 'node:test';
import assert from 'node:assert/strict';
import {FIELDS, initialState, validate, update, render} from '../src/signup.js';
import {parse, nodes, text, control, byId} from './html.js';
const good = {name: 'Ada', email: 'ada@example.com', password: 'Longpass12', confirm: 'Longpass12', terms: true};
const freeze = state => {Object.freeze(state.values); Object.freeze(state.touched); return Object.freeze(state);};

test('signup hidden: validation boundaries and regression traps', () => {
  for (const email of ['a+b@sub.example.com', ' A@EXAMPLE.COM ', 'a@x-y.example']) assert.equal(validate({...good, email}).email, undefined);
  for (const email of ['', 'a@b', 'a@@b.com', 'a b@x.com', 'a@.x.com', 'a@x..com', 'a@x_.com']) assert.match(validate({...good, email}).email, /email/i);
  for (const password of ['Short123', 'abcdefghij', '1234567890']) {
    const message = validate({...good, password, confirm: password}).password;
    for (const word of [/password/i, /10/, /letter/i, /digit/i]) assert.match(message, word);
  }
  assert.deepEqual(validate(good), {});
  assert.equal(validate({...good, name: 'x'.repeat(80)}).name, undefined);
  assert.match(validate({...good, name: 'x'.repeat(81)}).name, /80/);
  assert.match(validate({...good, name: '  '}).name, /name/i);
  assert.match(validate({...good, confirm: 'different'}).confirm, /confirm/i);
  assert.match(validate({...good, terms: false}).terms, /terms/i);
});

test('signup hidden: immutable transitions preserve entered data on failure', () => {
  const original = freeze(initialState());
  const input = update(original, {type: 'input', field: 'name', value: 'Ada'});
  assert.equal(original.values.name, '');
  assert.equal(input.values.name, 'Ada');
  const blurred = update(freeze(input), {type: 'blur', field: 'name'});
  assert.deepEqual(input.touched, {});
  assert.equal(blurred.touched.name, true);
  const ready = freeze({...blurred, values: {...good}});
  const sending = update(ready, {type: 'submit'});
  assert.equal(sending.status, 'submitting');
  assert.equal(sending.focus, null);
  assert.deepEqual(update(freeze(sending), {type: 'submit'}), sending);
  const failed = update(sending, {type: 'failure', message: 'Please try again'});
  assert.equal(failed.status, 'error');
  assert.deepEqual(failed.values, good);
  assert.deepEqual(failed.touched, ready.touched);
  assert.equal(failed.submitAttempted, true);
  assert.equal(failed.focus, null);
  const corrected = update(freeze(failed), {type: 'input', field: 'email', value: 'other@example.com'});
  assert.equal(corrected.serverError, null);
  assert.equal(corrected.status, 'idle');
  assert.equal(corrected.focus, null);
  assert.equal(update(original, {type: 'unknown'}), original);
  assert.equal(update(freeze({...sending}), {type: 'input', field: 'name', value: 'Grace'}).status, 'submitting');
});

test('signup hidden: native controls have labels, types and autocomplete', () => {
  const root = parse(render(initialState()));
  assert.equal(nodes(root, node => node.tag === 'form').length, 1);
  const ids = nodes(root, node => node.attrs.id).map(node => node.attrs.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const field of FIELDS) {
    const input = control(root, field);
    assert.ok(input?.attrs.id);
    const label = nodes(root, node => node.tag === 'label' && (node.attrs.for === input.attrs.id || nodes(node, child => child === input).length))[0];
    assert.ok(label && text(label).trim());
    const type = field === 'name' ? 'text' : field === 'email' ? 'email' : field === 'terms' ? 'checkbox' : 'password';
    assert.equal(input.attrs.type, type);
    if (field !== 'terms') assert.equal(input.attrs.autocomplete, field === 'name' ? 'name' : field === 'email' ? 'email' : 'new-password');
    assert.notEqual(input.attrs['aria-invalid'], 'true');
    assert.equal(input.attrs['aria-describedby'], undefined);
  }
  assert.equal(nodes(root, node => node.attrs.role === 'alert').length, 0);
});

test('signup hidden: error timing, descriptions and first-invalid focus', () => {
  const pristine = initialState();
  let state = update(pristine, {type: 'blur', field: 'email'});
  let root = parse(render(state));
  assert.equal(control(root, 'email').attrs['aria-invalid'], 'true');
  assert.notEqual(control(root, 'name').attrs['aria-invalid'], 'true');
  state = update({...state, values: {...state.values, name: 'Ada'}}, {type: 'submit'});
  assert.equal(state.focus, 'email');
  root = parse(render(state));
  const errors = validate(state.values);
  const alerts = nodes(root, node => node.attrs.role === 'alert');
  assert.ok(alerts.some(node => Object.values(errors).every(message => text(node).includes(message))));
  for (const field of Object.keys(errors)) {
    const input = control(root, field);
    assert.equal(input.attrs['aria-invalid'], 'true');
    const descriptions = (input.attrs['aria-describedby'] || '').split(/\s+/).map(id => byId(root, id)).filter(Boolean);
    assert.ok(descriptions.some(node => text(node).includes(errors[field])));
  }
  state = update(state, {type: 'input', field: 'email', value: good.email});
  root = parse(render(state));
  assert.notEqual(control(root, 'email').attrs['aria-invalid'], 'true');
  assert.equal(control(root, 'email').attrs['aria-describedby'], undefined);
});

test('signup hidden: escaping, password privacy and server announcement', () => {
  const payload = '\"><script>evil()</script>&\'';
  const state = {...initialState(), values: {...good, name: payload, email: payload}, status: 'error', serverError: payload};
  const root = parse(render(state));
  assert.equal(nodes(root, node => node.tag === 'script').length, 0);
  assert.equal(control(root, 'name').attrs.value, payload);
  assert.equal(control(root, 'email').attrs.value, payload);
  assert.ok(Object.hasOwn(control(root, 'terms').attrs, 'checked'));
  for (const field of ['password', 'confirm']) assert.ok(!control(root, field).attrs.value);
  assert.ok(nodes(root, node => node.attrs.role === 'alert').some(node => text(node) === payload));
  assert.equal(Object.hasOwn(control(parse(render(initialState())), 'terms').attrs, 'checked'), false);
});

test('signup hidden: semantic submit button locks only during submission', () => {
  for (const status of ['idle', 'invalid', 'error', 'submitting']) {
    const root = parse(render({...initialState(), values: {...good}, status}));
    const buttons = nodes(root, node => node.tag === 'button' && node.attrs.type === 'submit');
    assert.equal(buttons.length, 1);
    assert.match(text(buttons[0]), /sign up/i);
    assert.equal(Object.hasOwn(buttons[0].attrs, 'disabled'), status === 'submitting');
    assert.equal(nodes(root, node => Object.keys(node.attrs).some(attr => attr.startsWith('on'))).length, 0);
  }
});

test('signup hidden: independent initial states and read-only validation', () => {
  const first = initialState();
  const second = initialState();
  first.values.name = 'Ada';
  first.touched.email = true;
  assert.equal(second.values.name, '');
  assert.deepEqual(second.touched, {});
  assert.equal(second.submitAttempted, false);
  assert.equal(second.status, 'idle');
  assert.equal(second.focus, null);
  assert.equal(second.serverError, null);
  assert.deepEqual(validate(Object.freeze({...good})), {});
});
