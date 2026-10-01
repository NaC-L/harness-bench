import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { commitBatch, recoverLedger } from '../src/ledger.js';

const seed = { id: 'seed', entries: [{ key: 'cash', delta: 20 }, { key: 'saved', delta: 5 }] };
const transfer = { id: 'transfer', entries: [{ key: 'cash', delta: -7 }, { key: 'saved', delta: 7 }, { key: 'cash', delta: 2 }] };
const final = { revision: 2, balances: { cash: 15, saved: 12 }, receipts: [seed, transfer] };

async function workspace(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'ledger-hidden-'));
  t.after(() => fs.rm(directory, { recursive: true, force: true }));
  await fs.writeFile(path.join(directory, 'personal.txt'), 'not ledger data');
  return directory;
}

async function assertStable(directory, expected) {
  assert.deepEqual(await recoverLedger(directory), expected);
  assert.deepEqual(await recoverLedger(directory), expected);
  assert.deepEqual(JSON.parse(await fs.readFile(path.join(directory, 'ledger.json'), 'utf8')), expected);
  assert.equal(await fs.readFile(path.join(directory, 'personal.txt'), 'utf8'), 'not ledger data');
  await assert.rejects(fs.stat(path.join(directory, 'pending.json')), { code: 'ENOENT' });
}

for (const phase of ['prepared', 'published', 'complete']) {
  test(`fresh recovery after interruption at ${phase} commits exactly once`, async t => {
    const directory = await workspace(t);
    await commitBatch(directory, seed);
    const interrupted = new Error(`interrupted:${phase}`);
    await assert.rejects(commitBatch(directory, transfer, {
      checkpoint: async observed => { if (observed === phase) throw interrupted; }
    }), error => error === interrupted);
    await assertStable(directory, final);
    assert.deepEqual(await commitBatch(directory, transfer), final);
  });
}

test('the published checkpoint exposes a coherent balance and receipt snapshot', async t => {
  const directory = await workspace(t);
  await commitBatch(directory, seed);
  const phases = [];
  await commitBatch(directory, transfer, { checkpoint: async phase => {
    phases.push(phase);
    if (phase === 'published') {
      assert.deepEqual(JSON.parse(await fs.readFile(path.join(directory, 'ledger.json'), 'utf8')), final);
    }
    if (phase === 'complete') await assert.rejects(fs.stat(path.join(directory, 'pending.json')), { code: 'ENOENT' });
  } });
  assert.deepEqual(phases, ['prepared', 'published', 'complete']);
});

const faultPoints = [
  ['writeFile', 'pending.tmp', false, false],
  ['writeFile', 'pending.tmp', true, false],
  ['rename', 'pending.json', false, false],
  ['writeFile', 'ledger.tmp', false, true],
  ['writeFile', 'ledger.tmp', true, true],
  ['rename', 'ledger.json', false, true],
  ['unlink', 'pending.json', false, true],
];

for (const [method, filename, partial, prepared] of faultPoints) {
  test(`transient ${method} ${filename}${partial ? ' partial write' : ''} resumes without loss`, async t => {
    const directory = await workspace(t);
    const before = await commitBatch(directory, seed);
    const failure = Object.assign(new Error('injected local I/O failure'), { code: 'EIO' });
    const io = { ...fs, [method]: async (...args) => {
      const target = method === 'rename' ? args[1] : args[0];
      if (path.basename(target) === filename) {
        if (partial) await fs.writeFile(args[0], '{incomplete');
        throw failure;
      }
      return fs[method](...args);
    } };
    await assert.rejects(commitBatch(directory, transfer, { io }), error => error === failure);
    assert.deepEqual(await recoverLedger(directory), prepared ? final : before);
    assert.deepEqual(await commitBatch(directory, transfer), final);
    await assertStable(directory, final);
  });
}

test('recovery itself may be interrupted during publication or cleanup and retried', async t => {
  for (const method of ['writeFile', 'rename', 'unlink']) {
    const directory = path.join(await workspace(t), method);
    await fs.mkdir(directory);
    await commitBatch(directory, seed);
    await assert.rejects(commitBatch(directory, transfer, {
      checkpoint: async phase => { if (phase === 'prepared') throw new Error('stop'); }
    }), /stop/);
    const failure = Object.assign(new Error('recovery EIO'), { code: 'EIO' });
    await assert.rejects(recoverLedger(directory, { io: { ...fs, [method]: async () => { throw failure; } } }), error => error === failure);
    assert.deepEqual(await recoverLedger(directory), final);
    assert.deepEqual(await recoverLedger(directory), final);
  }
});

test('a new batch first finishes older interrupted work, keeping receipt order', async t => {
  const directory = await workspace(t);
  await commitBatch(directory, seed);
  await assert.rejects(commitBatch(directory, transfer, { checkpoint: async phase => {
    if (phase === 'published') throw new Error('stop');
  } }), /stop/);
  const third = { id: 'third', entries: [{ key: 'cash', delta: -1 }] };
  const expected = { revision: 3, balances: { cash: 14, saved: 12 }, receipts: [seed, transfer, third] };
  assert.deepEqual(await commitBatch(directory, third), expected);
  await assertStable(directory, expected);
});

test('conflicting receipt IDs reject after recovery without rewriting committed results', async t => {
  const directory = await workspace(t);
  await commitBatch(directory, seed);
  await assert.rejects(commitBatch(directory, transfer, { checkpoint: async phase => {
    if (phase === 'published') throw new Error('stop');
  } }), /stop/);
  await assert.rejects(commitBatch(directory, { id: 'transfer', entries: [...transfer.entries].reverse() }), { code: 'ERR_BATCH_CONFLICT' });
  await assertStable(directory, final);
  const bytes = await fs.readFile(path.join(directory, 'ledger.json'), 'utf8');
  await assert.rejects(commitBatch(directory, { id: 'seed', entries: [] }), { code: 'ERR_BATCH_CONFLICT' });
  assert.equal(await fs.readFile(path.join(directory, 'ledger.json'), 'utf8'), bytes);
});

test('invalid batches and arithmetic overflow preserve the existing snapshot', async t => {
  const directory = await workspace(t);
  const max = { id: 'max', entries: [{ key: 'cash', delta: Number.MAX_SAFE_INTEGER }] };
  const before = await commitBatch(directory, max);
  for (const batch of [null, {}, { id: '', entries: [] }, { id: 'x', entries: [{ key: '../cash', delta: 1 }] },
    { id: 'x', entries: [{ key: 'cash', delta: 0.5 }] }, { id: 'x', entries: [{ key: 'cash', delta: 1 }] },
    { id: 'x', entries: [{ key: 'cash', delta: Number.MAX_SAFE_INTEGER + 1 }] }]) {
    await assert.rejects(commitBatch(directory, batch), { code: 'ERR_INVALID_BATCH' });
    assert.deepEqual(await recoverLedger(directory), before);
  }
});

test('empty commits, object-inherited key names, and negative balances are ordinary data', async t => {
  const directory = await workspace(t);
  const empty = { id: 'empty', entries: [] };
  const batch = { id: 'names', entries: [{ key: 'constructor', delta: 4 }, { key: 'tostring', delta: -8 }] };
  await commitBatch(directory, empty);
  const expected = { revision: 2, balances: { constructor: 4, tostring: -8 }, receipts: [empty, batch] };
  assert.deepEqual(await commitBatch(directory, batch), expected);
  await assertStable(directory, expected);
});

test('stale staging files are ignored and malformed durable JSON is not erased', async t => {
  const directory = await workspace(t);
  await fs.writeFile(path.join(directory, 'pending.tmp'), '{partial');
  await fs.writeFile(path.join(directory, 'ledger.tmp'), '{partial');
  assert.deepEqual(await recoverLedger(directory), { revision: 0, balances: {}, receipts: [] });
  await commitBatch(directory, seed);
  await fs.writeFile(path.join(directory, 'pending.json'), '{corrupt');
  const ledgerBytes = await fs.readFile(path.join(directory, 'ledger.json'), 'utf8');
  await assert.rejects(recoverLedger(directory), SyntaxError);
  assert.equal(await fs.readFile(path.join(directory, 'pending.json'), 'utf8'), '{corrupt');
  assert.equal(await fs.readFile(path.join(directory, 'ledger.json'), 'utf8'), ledgerBytes);
  await fs.unlink(path.join(directory, 'pending.json'));
  await fs.writeFile(path.join(directory, 'ledger.json'), '{corrupt-ledger');
  await assert.rejects(commitBatch(directory, transfer), SyntaxError);
  assert.equal(await fs.readFile(path.join(directory, 'ledger.json'), 'utf8'), '{corrupt-ledger');
});
