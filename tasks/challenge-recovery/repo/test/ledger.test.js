import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { commitBatch, recoverLedger } from '../src/ledger.js';

async function workspace(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'ledger-visible-'));
  t.after(() => fs.rm(directory, { recursive: true, force: true }));
  return directory;
}

test('commits balances and reads them in a later invocation', async t => {
  const directory = await workspace(t);
  const batch = { id: 'seed', entries: [{ key: 'cash', delta: 9 }, { key: 'cash', delta: -2 }] };
  const expected = { revision: 1, balances: { cash: 7 }, receipts: [batch] };
  assert.deepEqual(await commitBatch(directory, batch), expected);
  assert.deepEqual(await recoverLedger(directory), expected);
});

test('a repeated successful batch is idempotent', async t => {
  const directory = await workspace(t);
  const batch = { id: 'once', entries: [{ key: 'cash', delta: 3 }] };
  const state = await commitBatch(directory, batch);
  assert.deepEqual(await commitBatch(directory, batch), state);
});

test('reopening after interrupted publication does not double the balance', async t => {
  const directory = await workspace(t);
  const batch = { id: 'interrupted', entries: [{ key: 'cash', delta: 7 }] };
  const failure = new Error('simulated stop after publication');
  await assert.rejects(commitBatch(directory, batch, {
    checkpoint: async phase => { if (phase === 'published') throw failure; }
  }), error => error === failure);
  const expected = { revision: 1, balances: { cash: 7 }, receipts: [batch] };
  assert.deepEqual(await recoverLedger(directory), expected);
  assert.deepEqual(await recoverLedger(directory), expected);
});
