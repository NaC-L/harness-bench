import fs from 'node:fs/promises';
import path from 'node:path';

function invalid() {
  return Object.assign(new Error('Invalid batch'), { code: 'ERR_INVALID_BATCH' });
}

function validate(batch) {
  if (!batch || typeof batch.id !== 'string' || !batch.id || !Array.isArray(batch.entries)) throw invalid();
  for (const entry of batch.entries) {
    if (!entry || typeof entry.key !== 'string' || !/^[a-z][a-z0-9_-]*$/.test(entry.key) || !Number.isSafeInteger(entry.delta)) throw invalid();
  }
  return { id: batch.id, entries: batch.entries.map(({ key, delta }) => ({ key, delta })) };
}

async function read(io, file, fallback) {
  try { return JSON.parse(await io.readFile(file, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return fallback; throw error; }
}

async function save(io, directory, name, value) {
  await io.writeFile(path.join(directory, `${name}.tmp`), JSON.stringify(value));
  await io.rename(path.join(directory, `${name}.tmp`), path.join(directory, `${name}.json`));
}

async function removePending(io, directory) {
  try { await io.unlink(path.join(directory, 'pending.json')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}

function apply(state, batch) {
  const balances = { ...state.balances };
  for (const { key, delta } of batch.entries) {
    const value = (Object.hasOwn(balances, key) ? balances[key] : 0) + delta;
    if (!Number.isSafeInteger(value)) throw invalid();
    balances[key] = value;
  }
  return { revision: state.revision + 1, balances, receipts: [...state.receipts, batch] };
}

export async function recoverLedger(directory, { io = fs } = {}) {
  await io.mkdir(directory, { recursive: true });
  const state = await read(io, path.join(directory, 'ledger.json'), { revision: 0, balances: {}, receipts: [] });
  const pending = await read(io, path.join(directory, 'pending.json'), null);
  if (!pending) return state;
  // The journal contains the final snapshot, not a delta to replay on possibly published data.
  await save(io, directory, 'ledger', pending.state);
  await removePending(io, directory);
  return pending.state;
}

export async function commitBatch(directory, batch, { io = fs, checkpoint = async () => {} } = {}) {
  batch = validate(batch);
  const state = await recoverLedger(directory, { io });
  const receipt = state.receipts.find(item => item.id === batch.id);
  if (receipt) {
    if (JSON.stringify(receipt.entries) !== JSON.stringify(batch.entries)) {
      throw Object.assign(new Error('Batch ID already used'), { code: 'ERR_BATCH_CONFLICT' });
    }
    return state;
  }
  const next = apply(state, batch);
  await save(io, directory, 'pending', { state: next });
  await checkpoint('prepared');
  await save(io, directory, 'ledger', next);
  await checkpoint('published');
  await removePending(io, directory);
  await checkpoint('complete');
  return next;
}
