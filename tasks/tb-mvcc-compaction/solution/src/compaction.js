'use strict';

function compactVersions(history, frontier, snapshotSequences) {
  let removed = 0;
  const boundaries = new Set([frontier, ...snapshotSequences]);
  for (const [key, versions] of history) {
    const retained = new Set();
    for (const version of versions) {
      if (version.sequence > frontier) retained.add(version.sequence);
    }
    for (const boundary of boundaries) {
      for (let i = versions.length - 1; i >= 0; i--) {
        const version = versions[i];
        if (version.sequence <= boundary) {
          retained.add(version.sequence);
          break;
        }
      }
    }
    const compacted = versions.filter(version => retained.has(version.sequence));
    removed += versions.length - compacted.length;
    if (compacted.length) history.set(key, compacted);
    else history.delete(key);
  }
  return removed;
}

module.exports = { compactVersions };
