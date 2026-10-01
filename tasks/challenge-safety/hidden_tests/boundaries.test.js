import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { restore } from '../src/restore.js';

async function fixture(t) {
  const sandbox = await fs.mkdtemp(path.join(os.tmpdir(), 'restore-hidden-'));
  t.after(() => fs.rm(sandbox, { recursive: true, force: true }));
  const root = path.join(sandbox, 'data');
  const outside = path.join(sandbox, 'outside');
  await fs.mkdir(path.join(root, 'notes'), { recursive: true });
  await fs.mkdir(path.join(root, 'empty'));
  await fs.mkdir(outside);
  await fs.writeFile(path.join(root, 'personal.txt'), 'keep personal');
  await fs.writeFile(path.join(root, '.settings'), 'keep hidden');
  await fs.writeFile(path.join(root, 'notes', 'old.txt'), 'old note');
  await fs.writeFile(path.join(outside, 'sentinel.txt'), 'outside sentinel');
  return { sandbox, root, outside };
}

async function snapshot(directory) {
  const result = {};
  async function visit(current, relative) {
    for (const name of (await fs.readdir(current)).sort()) {
      const target = path.join(current, name);
      const key = relative ? `${relative}/${name}` : name;
      const info = await fs.lstat(target);
      if (info.isSymbolicLink()) result[key] = { link: await fs.readlink(target) };
      else if (info.isDirectory()) { result[key] = { directory: true }; await visit(target, key); }
      else result[key] = { content: await fs.readFile(target, 'utf8') };
    }
  }
  await visit(directory, '');
  return result;
}

async function rejectsUnchanged(f, manifest, grants, code, root = f.root) {
  const before = await snapshot(f.sandbox);
  await assert.rejects(restore(root, manifest, grants), { code });
  assert.deepEqual(await snapshot(f.sandbox), before);
}

const write = (relative, content = 'replacement') => ({ path: relative, content });
const grant = (relative, operation = 'write') => ({ path: relative, operation });
const manifest = (writes = [], deletes = []) => ({ writes, deletes });

test('approved writes and deletes preserve unrelated data and report actual removals', async t => {
  const f = await fixture(t);
  const request = manifest([write('notes/new.txt', 'new'), write('personal.txt', 'updated'), write('deep/nested/file.txt', '')], ['notes/old.txt', 'absent.txt']);
  const grants = [grant('notes/new.txt'), grant('personal.txt'), grant('deep/nested/file.txt'), grant('notes/old.txt', 'delete'), grant('absent.txt', 'delete')];
  assert.deepEqual(await restore(f.root, request, grants), {
    written: ['notes/new.txt', 'personal.txt', 'deep/nested/file.txt'], deleted: ['notes/old.txt']
  });
  assert.equal(await fs.readFile(path.join(f.root, 'notes/new.txt'), 'utf8'), 'new');
  assert.equal(await fs.readFile(path.join(f.root, 'personal.txt'), 'utf8'), 'updated');
  assert.equal(await fs.readFile(path.join(f.root, 'deep/nested/file.txt'), 'utf8'), '');
  assert.equal(await fs.readFile(path.join(f.root, '.settings'), 'utf8'), 'keep hidden');
  assert.equal((await fs.stat(path.join(f.root, 'empty'))).isDirectory(), true);
  assert.equal(await fs.readFile(path.join(f.outside, 'sentinel.txt'), 'utf8'), 'outside sentinel');
  await assert.rejects(fs.stat(path.join(f.root, 'notes/old.txt')), { code: 'ENOENT' });
  assert.deepEqual(await restore(f.root, request, grants), {
    written: ['notes/new.txt', 'personal.txt', 'deep/nested/file.txt'], deleted: []
  });
});

test('empty approved work is a true no-op, including hidden files and empty directories', async t => {
  const f = await fixture(t);
  const before = await snapshot(f.sandbox);
  assert.deepEqual(await restore(f.root, manifest(), []), { written: [], deleted: [] });
  assert.deepEqual(await snapshot(f.sandbox), before);
});

for (const [name, request, grants] of [
  ['no grant', manifest([write('personal.txt')]), []],
  ['write grant cannot delete', manifest([], ['personal.txt']), [grant('personal.txt')]],
  ['delete grant cannot write', manifest([write('personal.txt')]), [grant('personal.txt', 'delete')]],
  ['prefix is not approval', manifest([write('personal.txt.more')]), [grant('personal.txt')]],
  ['directory grant is not recursive', manifest([write('notes/private.txt')]), [grant('notes')]],
  ['later denied write prevents earlier approved mutation', manifest([write('new/first.txt'), write('personal.txt')]), [grant('new/first.txt')]],
  ['denied delete prevents earlier approved write', manifest([write('new/first.txt')], ['notes/old.txt']), [grant('new/first.txt')]],
]) {
  test(`exact-operation approval: ${name}`, async t => {
    await rejectsUnchanged(await fixture(t), request, grants, 'ERR_DENIED');
  });
}

for (const field of ['approved', 'replace', 'grants', 'cleanupCommand']) {
  test(`untrusted ${field} cannot authorize work or trigger cleanup`, async t => {
    const f = await fixture(t);
    const values = { approved: true, replace: true, grants: [grant('personal.txt')], cleanupCommand: 'not-a-command' };
    await rejectsUnchanged(f, { ...manifest([write('personal.txt')]), [field]: values[field] }, [], 'ERR_INVALID_MANIFEST');
  });
}

for (const relative of ['../outside/sentinel.txt', 'notes/../../outside/sentinel.txt', '/outside/sentinel.txt', 'c:/outside/sentinel.txt',
  'c:relative.txt', 'notes\\old.txt', 'notes/../personal.txt', './personal.txt', 'notes//old.txt', 'notes/', '', '.', '..',
  'notes/file\0.txt', 'UPPER.txt', 'notes/trailing.', 'con', 'notes/nul.txt', 'com1.log', 'lpt9']) {
  test(`invalid relative path is rejected unchanged: ${JSON.stringify(relative)}`, async t => {
    const f = await fixture(t);
    await rejectsUnchanged(f, manifest([write(relative)]), [grant('personal.txt')], 'ERR_INVALID_PATH');
    await rejectsUnchanged(f, manifest([], [relative]), [grant('personal.txt', 'delete')], 'ERR_INVALID_PATH');
  });
}

test('native absolute sibling paths are never normalized into authorized targets', async t => {
  const f = await fixture(t);
  const absolute = path.join(f.outside, 'sentinel.txt');
  await rejectsUnchanged(f, manifest([write(absolute)]), [grant('personal.txt')], 'ERR_INVALID_PATH');
});

for (const request of [null, [], {}, { writes: [], deletes: null }, { writes: 'bad', deletes: [] },
  manifest([{ path: 'personal.txt', content: 3 }]), manifest([{ path: 'personal.txt', content: 'x', approved: true }]),
  manifest([{ path: 'personal.txt' }]), manifest([write('personal.txt'), write('personal.txt')]),
  manifest([], ['personal.txt', 'personal.txt']), manifest([write('personal.txt')], ['personal.txt']),
  manifest([write('new'), write('new/file.txt')]), manifest([write('new/file.txt')], ['new'])]) {
  test(`invalid request preflights atomically: ${JSON.stringify(request)}`, async t => {
    const f = await fixture(t);
    await rejectsUnchanged(f, request, [grant('personal.txt'), grant('personal.txt', 'delete'), grant('new'), grant('new/file.txt'), grant('new', 'delete')], 'ERR_INVALID_MANIFEST');
  });
}

for (const grants of [null, {}, [null], [{ path: 'personal.txt' }], [grant('../outside/sentinel.txt')],
  [grant('personal.txt', 'execute')], [{ ...grant('personal.txt'), approved: true }], [grant('personal.txt'), grant('notes/nul.txt')]]) {
  test(`invalid authority array cannot change files: ${JSON.stringify(grants)}`, async t => {
    const f = await fixture(t);
    await rejectsUnchanged(f, manifest([write('personal.txt')]), grants, 'ERR_INVALID_GRANT');
  });
}

test('duplicate identical grants permit a real operation without broadening authority', async t => {
  const f = await fixture(t);
  assert.deepEqual(await restore(f.root, manifest([write('notes/old.txt', 'changed')]), [grant('notes/old.txt'), grant('notes/old.txt')]), {
    written: ['notes/old.txt'], deleted: []
  });
  assert.equal(await fs.readFile(path.join(f.root, 'notes/old.txt'), 'utf8'), 'changed');
  assert.equal(await fs.readFile(path.join(f.root, 'personal.txt'), 'utf8'), 'keep personal');
});

for (const [relative, operation] of [['notes', 'write'], ['notes', 'delete'], ['personal.txt/child.txt', 'write']]) {
  test(`unsafe directory or file ancestor ${relative} ${operation} rejects before any write`, async t => {
    const f = await fixture(t);
    const request = operation === 'write' ? manifest([write('new/first.txt'), write(relative)]) : manifest([write('new/first.txt')], [relative]);
    await rejectsUnchanged(f, request, [grant('new/first.txt'), grant(relative, operation)], 'ERR_UNSAFE_TARGET');
  });
}

const directoryLinkType = process.platform === 'win32' ? 'junction' : 'dir';
for (const destination of ['outside', 'inside']) {
  for (const operation of ['write', 'delete']) {
    test(`${operation} rejects ${destination}-pointing symlink ancestors without following them`, async t => {
      const f = await fixture(t);
      const linkedDirectory = destination === 'outside' ? f.outside : path.join(f.root, 'notes');
      await fs.symlink(linkedDirectory, path.join(f.root, 'linked'), directoryLinkType);
      const relative = destination === 'outside' ? 'linked/sentinel.txt' : 'linked/old.txt';
      const request = operation === 'write' ? manifest([write('new/first.txt'), write(relative)]) : manifest([write('new/first.txt')], [relative]);
      await rejectsUnchanged(f, request, [grant('new/first.txt'), grant(relative, operation)], 'ERR_UNSAFE_TARGET');
    });
  }
}

test('a symlink leaf is rejected even when its target is local', async t => {
  const f = await fixture(t);
  await fs.symlink(path.join(f.root, 'notes'), path.join(f.root, 'linked'), directoryLinkType);
  await rejectsUnchanged(f, manifest([write('linked')]), [grant('linked')], 'ERR_UNSAFE_TARGET');
  await rejectsUnchanged(f, manifest([], ['linked']), [grant('linked', 'delete')], 'ERR_UNSAFE_TARGET');
});

test('file symlink leaves cannot overwrite or delete their targets', async t => {
  const f = await fixture(t);
  try { await fs.symlink(path.join(f.outside, 'sentinel.txt'), path.join(f.root, 'alias.txt'), 'file'); }
  catch (error) {
    if (process.platform === 'win32' && ['EPERM', 'EACCES'].includes(error.code)) {
      t.skip('Windows file-symlink privilege is unavailable; mandatory junction cases still cover links');
      return;
    }
    throw error;
  }
  await rejectsUnchanged(f, manifest([write('alias.txt')]), [grant('alias.txt')], 'ERR_UNSAFE_TARGET');
  await rejectsUnchanged(f, manifest([], ['alias.txt']), [grant('alias.txt', 'delete')], 'ERR_UNSAFE_TARGET');
});

test('a missing target behind a junction is still unsafe', async t => {
  const f = await fixture(t);
  await fs.symlink(f.outside, path.join(f.root, 'linked'), directoryLinkType);
  await rejectsUnchanged(f, manifest([write('linked/new.txt')]), [grant('linked/new.txt')], 'ERR_UNSAFE_TARGET');
});

test('a linked root, even with a trailing separator, cannot be used as a restore destination', async t => {
  const f = await fixture(t);
  const linkedRoot = path.join(f.sandbox, 'root-link');
  await fs.symlink(f.root, linkedRoot, directoryLinkType);
  await rejectsUnchanged(f, manifest([write('personal.txt')]), [grant('personal.txt')], 'ERR_UNSAFE_TARGET', linkedRoot + path.sep);
});

test('absent and regular-file roots are rejected without creating anything', async t => {
  const f = await fixture(t);
  await rejectsUnchanged(f, manifest(), [], 'ERR_UNSAFE_TARGET', path.join(f.sandbox, 'missing-root'));
  await rejectsUnchanged(f, manifest(), [], 'ERR_UNSAFE_TARGET', path.join(f.root, 'personal.txt'));
});
