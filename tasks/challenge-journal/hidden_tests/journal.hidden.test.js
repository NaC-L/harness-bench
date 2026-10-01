'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {openJournal} = require('../src');
const INITIAL = {wallet: 30, clearing: 0, shop: 0};
const payment = (id = 'a', amount = 5) => ({id, from: 'wallet', to: 'shop', amount});
const record = (sequence, payload = payment()) => ({sequence, ...payload});
const encode = (events) => events.map((event) => JSON.stringify(event) + '\n').join('');
function fixture(t, initialBalances = INITIAL) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'bench-journal-hidden-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  const file = path.join(dir, 'journal.ndjson');
  return {dir, file, open: (extra = {}) => openJournal(dir, {initialBalances, ...extra})};
}
function corrupt(t, contents) {
  const f = fixture(t);
  fs.writeFileSync(f.file, contents);
  assert.throws(() => f.open(), {code: 'CORRUPT_JOURNAL'});
  assert.equal(fs.readFileSync(f.file, 'utf8'), contents);
}

test('replay uses commit order for dependent transfers', (t) => {
  const f = fixture(t);
  const journal = f.open();
  journal.transfer({id: 'z-fund', from: 'wallet', to: 'clearing', amount: 9});
  journal.transfer({id: 'a-spend', from: 'clearing', to: 'shop', amount: 7});
  const reopened = f.open();
  assert.deepEqual(reopened.entries().map((entry) => entry.id), ['z-fund', 'a-spend']);
  assert.equal(reopened.balance('wallet'), 21);
  assert.equal(reopened.balance('clearing'), 2);
  assert.equal(reopened.balance('shop'), 7);
});

test('independent transfers retain receipt order on reopen', (t) => {
  const f = fixture(t);
  const journal = f.open();
  const first = journal.transfer(payment('z'));
  const second = journal.transfer(payment('a'));
  assert.deepEqual(f.open().entries(), [first, second]);
});

test('idempotency conflicts are rejected without changing bytes or balances', (t) => {
  const f = fixture(t);
  const journal = f.open();
  journal.transfer(payment());
  const bytes = fs.readFileSync(f.file);
  assert.throws(() => journal.transfer(payment('a', 8)), {code: 'IDEMPOTENCY_CONFLICT'});
  assert.equal(journal.balance('wallet'), 25);
  assert.deepEqual(fs.readFileSync(f.file), bytes);
});

test('idempotency conflict takes precedence over invalid replacement', (t) => {
  const f = fixture(t);
  const journal = f.open();
  journal.transfer(payment());
  assert.throws(() => journal.transfer({id: 'a', from: 'missing', to: 'shop', amount: -1}), {code: 'IDEMPOTENCY_CONFLICT'});
});

test('insufficient attempt does not reserve id or sequence', (t) => {
  const f = fixture(t);
  const journal = f.open();
  assert.throws(() => journal.transfer(payment('retry', 100)), {code: 'INSUFFICIENT_FUNDS'});
  assert.equal(fs.readFileSync(f.file, 'utf8'), '');
  const receipt = journal.transfer(payment('retry', 6));
  assert.deepEqual(receipt, record(1, payment('retry', 6)));
  assert.equal(journal.balance('wallet'), 24);
  assert.deepEqual(f.open().entries(), [receipt]);
});

test('invalid attempt does not leave a gap before another id commits', (t) => {
  const f = fixture(t);
  const journal = f.open();
  assert.throws(() => journal.transfer(payment('invalid', 0)), {code: 'INVALID_TRANSFER'});
  assert.equal(journal.transfer(payment('valid')).sequence, 1);
  assert.equal(f.open().balance('shop'), 5);
});

test('append failure rolls back state and same-id retry actually persists', (t) => {
  const f = fixture(t);
  const outage = new Error('disk unavailable');
  let reject = true;
  const journal = f.open({append(file, line) {
    if (reject) throw outage;
    fs.appendFileSync(file, line);
  }});
  assert.throws(() => journal.transfer(payment('retry')), (error) => error === outage);
  assert.equal(journal.balance('wallet'), 30);
  assert.equal(journal.balance('shop'), 0);
  assert.deepEqual(journal.entries(), []);
  assert.equal(fs.readFileSync(f.file, 'utf8'), '');
  reject = false;
  const receipt = journal.transfer(payment('retry'));
  assert.equal(receipt.sequence, 1);
  assert.deepEqual(f.open().entries(), [receipt]);
  assert.equal(f.open().balance('shop'), 5);
});

test('append failure permits a different payload with the failed id', (t) => {
  const f = fixture(t);
  let reject = true;
  const journal = f.open({append(file, line) {
    if (reject) throw new Error('disk');
    fs.appendFileSync(file, line);
  }});
  assert.throws(() => journal.transfer(payment('retry', 5)), /disk/);
  reject = false;
  assert.deepEqual(journal.transfer(payment('retry', 7)), record(1, payment('retry', 7)));
  assert.equal(f.open().balance('wallet'), 23);
});

test('partial tail after a commit is removed before the next append', (t) => {
  const f = fixture(t);
  const first = f.open().transfer(payment('a'));
  const committed = fs.readFileSync(f.file, 'utf8');
  fs.appendFileSync(f.file, '{"sequence":2,"id":"unfinished"');
  const reopened = f.open();
  assert.equal(fs.readFileSync(f.file, 'utf8'), committed);
  const second = reopened.transfer(payment('b', 6));
  assert.deepEqual(f.open().entries(), [first, second]);
  assert.equal(f.open().balance('shop'), 11);
});

test('complete malformed JSON is not treated as an interrupted tail', (t) => {
  corrupt(t, encode([record(1)]) + '{broken}\n');
});

test('sequence gaps are corruption', (t) => {
  corrupt(t, encode([record(1), record(3, payment('b'))]));
});

test('reordered sequences are corruption rather than sortable input', (t) => {
  corrupt(t, encode([record(2, payment('b')), record(1)]));
});

test('duplicate persisted ids are corruption rather than repeated payment', (t) => {
  corrupt(t, encode([record(1), record(2)]));
});

test('invalid persisted transfer reports corruption and preserves data', (t) => {
  corrupt(t, encode([record(1, payment('a', -1))]));
});

test('receipt mutations cannot rewrite idempotency or journal history', (t) => {
  const f = fixture(t);
  const journal = f.open();
  const payload = payment();
  const receipt = journal.transfer(payload);
  payload.amount = 22;
  receipt.amount = 19;
  receipt.id = 'changed';
  const entries = journal.entries();
  entries[0].from = 'changed';
  entries.push(record(99));
  assert.deepEqual(journal.transfer(payment()), record(1));
  assert.deepEqual(journal.entries(), [record(1)]);
  assert.deepEqual(f.open().entries(), [record(1)]);
});

test('duplicate success is byte-for-byte idempotent before and after reopen', (t) => {
  const f = fixture(t);
  const journal = f.open();
  const receipt = journal.transfer(payment('a', 30));
  const bytes = fs.readFileSync(f.file);
  assert.deepEqual(journal.transfer(payment('a', 30)), receipt);
  const reopened = f.open();
  assert.deepEqual(reopened.transfer(payment('a', 30)), receipt);
  assert.equal(reopened.balance('wallet'), 0);
  assert.equal(reopened.balance('shop'), 30);
  assert.deepEqual(fs.readFileSync(f.file), bytes);
});

test('successful reopen continues sequence without losing prior receipts', (t) => {
  const f = fixture(t);
  const first = f.open().transfer(payment('a'));
  const reopened = f.open();
  const second = reopened.transfer(payment('b', 7));
  assert.equal(second.sequence, 2);
  assert.deepEqual(f.open().entries(), [first, second]);
  assert.equal(f.open().balance('wallet'), 18);
});

test('empty and all-fragment journals recover without inventing a commit', (t) => {
  const f = fixture(t);
  assert.deepEqual(f.open().entries(), []);
  fs.writeFileSync(f.file, '{"sequence":1');
  const journal = f.open();
  assert.deepEqual(journal.entries(), []);
  assert.equal(fs.readFileSync(f.file, 'utf8'), '');
  const receipt = journal.transfer(payment());
  assert.equal(receipt.sequence, 1);
  assert.deepEqual(f.open().entries(), [receipt]);
});

test('invalid account and amount boundaries leave balances and bytes intact', (t) => {
  const cases = [
    {id: 'x', from: 'missing', to: 'shop', amount: 1},
    {id: 'x', from: 'wallet', to: 'wallet', amount: 1},
    payment('x', 0), payment('x', -1), payment('x', 1.5),
    payment('x', Number.MAX_SAFE_INTEGER + 1), payment('', 1)
  ];
  for (const payload of cases) {
    const f = fixture(t);
    const journal = f.open();
    assert.throws(() => journal.transfer(payload), {code: 'INVALID_TRANSFER'});
    assert.equal(journal.balance('wallet'), 30);
    assert.equal(journal.balance('shop'), 0);
    assert.deepEqual(journal.entries(), []);
    assert.equal(fs.readFileSync(f.file, 'utf8'), '');
  }
});

test('destination overflow is rejected without debiting the source', (t) => {
  const f = fixture(t, {wallet: 10, shop: Number.MAX_SAFE_INTEGER});
  const journal = f.open();
  assert.throws(() => journal.transfer(payment('a', 1)), {code: 'INVALID_TRANSFER'});
  assert.equal(journal.balance('wallet'), 10);
  assert.equal(journal.balance('shop'), Number.MAX_SAFE_INTEGER);
  assert.deepEqual(journal.entries(), []);
  assert.equal(fs.readFileSync(f.file, 'utf8'), '');
});

test('unknown balance account has stable error code', (t) => {
  assert.throws(() => fixture(t).open().balance('missing'), {code: 'UNKNOWN_ACCOUNT'});
});

test('JSON escaping and unicode ids survive reopen and idempotency', (t) => {
  const f = fixture(t);
  const payload = payment('line\nquote"雪', 3);
  const receipt = f.open().transfer(payload);
  const reopened = f.open();
  assert.deepEqual(reopened.entries(), [receipt]);
  assert.deepEqual(reopened.transfer(payload), receipt);
  assert.equal(reopened.balance('shop'), 3);
});
