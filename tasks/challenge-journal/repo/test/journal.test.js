'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {openJournal} = require('../src');
function directory(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'bench-journal-visible-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  return dir;
}

test('successful transfer conserves total balance', (t) => {
  const journal = openJournal(directory(t), {initialBalances: {wallet: 10, shop: 0}});
  const receipt = journal.transfer({id: 'sale', from: 'wallet', to: 'shop', amount: 4});
  assert.deepEqual(receipt, {sequence: 1, id: 'sale', from: 'wallet', to: 'shop', amount: 4});
  assert.equal(journal.balance('wallet'), 6);
  assert.equal(journal.balance('shop'), 4);
});

test('dependent transfers retain their result after reopen', (t) => {
  const dir = directory(t);
  const options = {initialBalances: {wallet: 10, clearing: 0, shop: 0}};
  const journal = openJournal(dir, options);
  journal.transfer({id: 'z-fund', from: 'wallet', to: 'clearing', amount: 6});
  journal.transfer({id: 'a-sale', from: 'clearing', to: 'shop', amount: 4});
  const reopened = openJournal(dir, options);
  assert.equal(reopened.balance('wallet'), 4);
  assert.equal(reopened.balance('clearing'), 2);
  assert.equal(reopened.balance('shop'), 4);
});
