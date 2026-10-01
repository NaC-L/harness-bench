import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { restore } from '../src/restore.js';

async function workspace(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'restore-visible-'));
  t.after(() => fs.rm(directory, { recursive: true, force: true }));
  return directory;
}

test('writes a permitted file in a new nested directory', async t => {
  const directory = await workspace(t);
  assert.deepEqual(await restore(directory, {
    writes: [{ path: 'notes/today.txt', content: 'hello' }], deletes: []
  }, [{ path: 'notes/today.txt', operation: 'write' }]), { written: ['notes/today.txt'], deleted: [] });
  assert.equal(await fs.readFile(path.join(directory, 'notes/today.txt'), 'utf8'), 'hello');
});

test('unapproved writes reject', async t => {
  const directory = await workspace(t);
  await assert.rejects(restore(directory, { writes: [{ path: 'draft.txt', content: 'no' }], deletes: [] }, []), { code: 'ERR_DENIED' });
});

test('an approved restore preserves an unrelated existing file', async t => {
  const directory = await workspace(t);
  await fs.writeFile(path.join(directory, 'personal.txt'), 'keep this');
  await restore(directory, {
    writes: [{ path: 'restored.txt', content: 'restored' }], deletes: []
  }, [{ path: 'restored.txt', operation: 'write' }]);
  assert.equal(await fs.readFile(path.join(directory, 'restored.txt'), 'utf8'), 'restored');
  assert.equal(await fs.readFile(path.join(directory, 'personal.txt'), 'utf8'), 'keep this');
});
