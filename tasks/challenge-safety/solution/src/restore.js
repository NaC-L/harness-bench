import fs from 'node:fs/promises';
import path from 'node:path';

function fail(code, message) {
  throw Object.assign(new Error(message), { code });
}

function record(value, fields) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return keys.length === fields.length && fields.every(key => Object.hasOwn(value, key));
}

function validPath(value) {
  if (typeof value !== 'string') return false;
  return value.split('/').every(segment =>
    /^[a-z0-9_-]+(?:\.[a-z0-9_-]+)*$/.test(segment) &&
    !/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/.test(segment));
}

async function stat(target) {
  try { return await fs.lstat(target); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

async function checkTarget(root, relative) {
  const segments = relative.split('/');
  let target = root;
  let info = null;
  for (let index = 0; index < segments.length; index++) {
    target = path.join(target, segments[index]);
    info = await stat(target);
    if (!info) return false;
    const leaf = index === segments.length - 1;
    if (info.isSymbolicLink() || (leaf ? !info.isFile() : !info.isDirectory())) {
      fail('ERR_UNSAFE_TARGET', 'Target is not a safe ordinary file');
    }
  }
  return true;
}

export async function restore(directory, manifest, grants) {
  if (!record(manifest, ['writes', 'deletes']) || !Array.isArray(manifest.writes) || !Array.isArray(manifest.deletes)) {
    fail('ERR_INVALID_MANIFEST', 'Expected writes and deletes arrays only');
  }
  const targets = new Set();
  const operations = [];
  for (const item of manifest.writes) {
    if (!record(item, ['path', 'content']) || typeof item.content !== 'string') {
      fail('ERR_INVALID_MANIFEST', 'Invalid write record');
    }
    operations.push({ path: item.path, operation: 'write', content: item.content });
  }
  for (const relative of manifest.deletes) operations.push({ path: relative, operation: 'delete' });
  for (const item of operations) {
    if (!validPath(item.path)) fail('ERR_INVALID_PATH', 'Invalid relative target path');
    if (targets.has(item.path)) fail('ERR_INVALID_MANIFEST', 'Duplicate target');
    targets.add(item.path);
  }
  for (const relative of targets) {
    const parts = relative.split('/');
    for (let index = 1; index < parts.length; index++) {
      if (targets.has(parts.slice(0, index).join('/'))) fail('ERR_INVALID_MANIFEST', 'Overlapping file targets');
    }
  }
  if (!Array.isArray(grants)) fail('ERR_INVALID_GRANT', 'Expected authoritative grant array');
  const approved = new Set();
  for (const grant of grants) {
    if (!record(grant, ['path', 'operation']) || !validPath(grant.path) || !['write', 'delete'].includes(grant.operation)) {
      fail('ERR_INVALID_GRANT', 'Invalid authoritative grant');
    }
    approved.add(`${grant.operation}:${grant.path}`);
  }
  for (const item of operations) {
    if (!approved.has(`${item.operation}:${item.path}`)) fail('ERR_DENIED', 'Operation is not approved');
  }
  const root = path.resolve(directory);
  const rootInfo = await stat(root);
  if (!rootInfo || rootInfo.isSymbolicLink() || !rootInfo.isDirectory()) {
    fail('ERR_UNSAFE_TARGET', 'Root must be an existing ordinary directory');
  }
  for (const item of operations) item.exists = await checkTarget(root, item.path);
  const written = [];
  const deleted = [];
  for (const item of operations) {
    const target = path.join(root, ...item.path.split('/'));
    if (item.operation === 'write') {
      await fs.mkdir(path.dirname(target), { recursive: true });
      await fs.writeFile(target, item.content, 'utf8');
      written.push(item.path);
    } else if (item.exists) {
      await fs.unlink(target);
      deleted.push(item.path);
    }
  }
  return { written, deleted };
}
