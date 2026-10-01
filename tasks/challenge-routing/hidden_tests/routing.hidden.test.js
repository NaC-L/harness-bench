'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {createRouter} = require('../src');
const route = (id, path, config = {}, method = 'GET') => ({id, path, config, method});
const request = (path, extra = {}) => ({tenant: 'blue', method: 'GET', path, ...extra});
const build = (routes, extra = {}) => createRouter({routes, tenants: {blue: {}, red: {}}, ...extra});

test('literal precedence is independent of declaration order', () => {
  for (const routes of [[route('detail', '/items/:id'), route('new', '/items/new')], [route('new', '/items/new'), route('detail', '/items/:id')]]) {
    assert.equal(build(routes).dispatch(request('/items/new')).route, 'new');
  }
});

test('specificity compares the first differing segment', () => {
  const router = build([route('late', '/:group/fixed'), route('early', '/fixed/:name')]);
  assert.equal(router.dispatch(request('/fixed/fixed')).route, 'early');
});

test('full pathname matching does not accept descendant paths', () => {
  assert.deepEqual(build([route('list', '/items')]).dispatch(request('/items/42')), {status: 404});
});

test('method matching normalizes case', () => {
  assert.equal(build([route('list', '/items')]).dispatch(request('/items', {method: 'get'})).route, 'list');
});

test('encoded slash stays within one captured parameter', () => {
  const result = build([route('file', '/files/:name')]).dispatch(request('/files/a%2Fb'));
  assert.deepEqual(result.params, {name: 'a/b'});
});

test('configuration is isolated by tenant on reused router', () => {
  const router = build([route('list', '/items')], {tenants: {blue: {config: {timeoutMs: 11, roles: ['reader']}}, red: {config: {timeoutMs: 22, roles: ['editor']}}}});
  assert.equal(router.dispatch(request('/items', {principal: {roles: ['reader']}})).status, 200);
  const denied = router.dispatch(request('/items', {tenant: 'red', principal: {roles: ['reader']}}));
  assert.deepEqual(denied, {status: 403});
  const allowed = router.dispatch(request('/items', {tenant: 'red', principal: {roles: ['editor']}}));
  assert.equal(allowed.config.timeoutMs, 22);
});

test('false and zero are effective route overrides', () => {
  const router = build([route('list', '/items', {authRequired: false, timeoutMs: 0})], {defaults: {authRequired: true, timeoutMs: 90}});
  const result = router.dispatch(request('/items'));
  assert.equal(result.status, 200);
  assert.equal(result.config.timeoutMs, 0);
});

test('disabled specific route cannot fall back to parameter route', () => {
  const router = build([route('detail', '/items/:id'), route('hidden', '/items/hidden', {enabled: false})]);
  assert.deepEqual(router.dispatch(request('/items/hidden')), {status: 404});
});

test('authorization allows any listed role', () => {
  const router = build([route('list', '/items', {roles: ['reader', 'admin']})]);
  assert.equal(router.dispatch(request('/items', {principal: {roles: ['reader']}})).status, 200);
});

test('success snapshots cannot modify future policy or source configuration', () => {
  const config = {roles: ['reader'], headers: {'x-owner': 'blue'}};
  const router = build([route('list', '/items', config)]);
  const first = router.dispatch(request('/items', {principal: {roles: ['reader']}}));
  first.config.roles.push('intruder');
  first.config.headers['x-owner'] = 'changed';
  first.config.enabled = false;
  first.params.injected = 'x';
  assert.deepEqual(config, {roles: ['reader'], headers: {'x-owner': 'blue'}});
  const second = router.dispatch(request('/items', {principal: {roles: ['reader']}}));
  assert.equal(second.status, 200);
  assert.deepEqual(second.config.roles, ['reader']);
  assert.equal(second.config.headers['x-owner'], 'blue');
  assert.deepEqual(second.params, {});
});

test('inherited tenant properties are not registrations', () => {
  assert.deepEqual(build([route('list', '/items')]).dispatch(request('/items', {tenant: 'toString'})), {status: 404});
});

test('headers merge across layers and tenant route override wins', () => {
  const defaults = {headers: {a: 'default', b: 'default'}, timeoutMs: 1};
  const tenants = {blue: {config: {headers: {b: 'tenant', c: 'tenant'}, timeoutMs: 2}, routes: {list: {headers: {d: 'override'}, timeoutMs: 4}}}};
  const routes = [route('list', '/items', {headers: {c: 'route', d: 'route'}, timeoutMs: 3})];
  const baseline = JSON.stringify({defaults, tenants, routes});
  const result = build(routes, {defaults, tenants}).dispatch(request('/items'));
  assert.equal(result.config.timeoutMs, 4);
  assert.deepEqual(result.config.headers, {a: 'default', b: 'tenant', c: 'route', d: 'override'});
  assert.equal(JSON.stringify({defaults, tenants, routes}), baseline);
});

test('empty role override makes inherited role policy public', () => {
  const router = build([route('list', '/items', {roles: []})], {defaults: {roles: ['reader']}});
  assert.equal(router.dispatch(request('/items')).status, 200);
});

test('head prefers explicit endpoint and otherwise uses get', () => {
  const router = build([route('get', '/items'), route('head', '/items', {}, 'HEAD'), route('other', '/other')]);
  assert.equal(router.dispatch(request('/items', {method: 'HEAD'})).route, 'head');
  assert.equal(router.dispatch(request('/other', {method: 'HEAD'})).route, 'other');
});

test('explicit forbidden head does not fall back to public get', () => {
  const router = build([route('get', '/items'), route('head', '/items', {roles: ['admin']}, 'HEAD')]);
  assert.deepEqual(router.dispatch(request('/items', {method: 'HEAD', principal: {roles: ['reader']}})), {status: 403});
});

test('unknown tenant and method do not leak route metadata', () => {
  const router = build([route('detail', '/items/:id')]);
  assert.deepEqual(router.dispatch(request('/items/42', {tenant: 'missing'})), {status: 404});
  assert.deepEqual(router.dispatch(request('/items/42', {method: 'POST'})), {status: 404});
});

test('query is ignored and parameter decoding happens exactly once', () => {
  const result = build([route('file', '/files/:name')]).dispatch(request('/files/%252F?q=%GG'));
  assert.deepEqual(result.params, {name: '%2F'});
});

test('malformed matched parameter returns only a bad-request status', () => {
  assert.deepEqual(build([route('file', '/files/:name')]).dispatch(request('/files/%GG')), {status: 400});
});

test('equal specificity preserves declaration order', () => {
  assert.equal(build([route('first', '/items/:a'), route('second', '/items/:b')]).dispatch(request('/items/42')).route, 'first');
});

test('authentication and role denials preserve their distinct statuses', () => {
  const router = build([route('secure', '/secure', {authRequired: true}), route('roles', '/roles', {roles: ['reader']})]);
  assert.deepEqual(router.dispatch(request('/secure')), {status: 401});
  assert.equal(router.dispatch(request('/secure', {principal: {roles: []}})).status, 200);
  assert.deepEqual(router.dispatch(request('/roles')), {status: 401});
  assert.deepEqual(router.dispatch(request('/roles', {principal: {roles: ['other']}})), {status: 403});
});

test('literal regex punctuation remains literal', () => {
  const router = build([route('version', '/v1.0')]);
  assert.equal(router.dispatch(request('/v1.0')).route, 'version');
  assert.deepEqual(router.dispatch(request('/v1x0')), {status: 404});
});
