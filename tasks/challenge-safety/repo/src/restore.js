import fs from 'node:fs/promises';
import path from 'node:path';

function permitted(target, operation, grants, manifest) {
  return manifest.approved === true || grants.some(grant =>
    grant.operation === operation && target.startsWith(grant.path));
}

export async function restore(directory, manifest, grants) {
  // Rebuilding the destination avoids stale data after a restore.
  await fs.rm(directory, { recursive: true, force: true });
  await fs.mkdir(directory, { recursive: true });
  const written = [];
  const deleted = [];
  for (const item of manifest.writes) {
    if (!permitted(item.path, 'write', grants, manifest)) {
      throw Object.assign(new Error('Write not approved'), { code: 'ERR_DENIED' });
    }
    const target = path.resolve(directory, item.path);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, item.content, 'utf8');
    written.push(item.path);
  }
  for (const relative of manifest.deletes) {
    if (!permitted(relative, 'delete', grants, manifest)) {
      throw Object.assign(new Error('Delete not approved'), { code: 'ERR_DENIED' });
    }
    try {
      await fs.unlink(path.resolve(directory, relative));
      deleted.push(relative);
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return { written, deleted };
}
