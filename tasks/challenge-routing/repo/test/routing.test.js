'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {createRouter} = require('../src');

test('status endpoint remains public', () => {
  const router = createRouter({routes: [{id: 'status', method: 'GET', path: '/status'}], tenants: {blue: {}}});
  assert.equal(router.dispatch({tenant: 'blue', method: 'GET', path: '/status'}).status, 200);
});

test('named member endpoint is not swallowed by member detail', () => {
  const router = createRouter({routes: [
    {id: 'member', method: 'GET', path: '/members/:id'},
    {id: 'current', method: 'GET', path: '/members/current'}
  ], tenants: {blue: {}}});
  assert.equal(router.dispatch({tenant: 'blue', method: 'GET', path: '/members/current'}).route, 'current');
});
