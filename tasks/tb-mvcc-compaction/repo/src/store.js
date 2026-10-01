'use strict';

const { compactVersions } = require('./compaction');

function detach(value) {
  return structuredClone(value);
}

function makeStore() {
  const history = new Map();
  const batches = new WeakMap();
  const pending = new Map();
  const snapshots = new Map();
  let allocated = 0;
  let published = 0;

  function install(operations) {
    const start = allocated + 1;
    for (const operation of operations) {
      const version = {
        sequence: ++allocated,
        deleted: operation.type === 'delete',
        value: operation.type === 'put' ? detach(operation.value) : undefined,
      };
      let versions = history.get(operation.key);
      if (!versions) {
        versions = [];
        history.set(operation.key, versions);
      }
      versions.push(version);
    }
    const batch = { start, end: allocated, ready: false };
    pending.set(start, batch);
    return batch;
  }

  function markReady(batch) {
    batch.ready = true;
    let next = pending.get(published + 1);
    while (next && next.ready) {
      pending.delete(next.start);
      published = next.end;
      next = pending.get(published + 1);
    }
    return published;
  }

  function snapshotSequence(token) {
    if (!snapshots.has(token)) {
      throw new TypeError('Snapshot token is not live in this store');
    }
    return snapshots.get(token);
  }

  return {
    put(key, value) {
      const batch = install([{ type: 'put', key, value }]);
      markReady(batch);
      return batch.end;
    },

    delete(key) {
      const batch = install([{ type: 'delete', key }]);
      markReady(batch);
      return batch.end;
    },

    prepare(operations) {
      const batch = install(operations);
      const token = Object.freeze({});
      batches.set(token, batch);
      return token;
    },

    publish(token) {
      const batch = batches.get(token);
      if (!batch) throw new TypeError('Batch token belongs to no batch in this store');
      return markReady(batch);
    },

    snapshot() {
      const token = Object.freeze({});
      snapshots.set(token, published);
      return token;
    },

    releaseSnapshot(token) {
      snapshotSequence(token);
      snapshots.delete(token);
    },

    get(key, token) {
      const sequence = token === undefined ? published : snapshotSequence(token);
      const versions = history.get(key);
      if (!versions) return undefined;
      for (let i = versions.length - 1; i >= 0; i--) {
        const version = versions[i];
        if (version.sequence <= sequence) {
          return version.deleted ? undefined : detach(version.value);
        }
      }
      return undefined;
    },

    compact() {
      return compactVersions(history, allocated, [...snapshots.values()]);
    },

    versionCount() {
      let count = 0;
      for (const versions of history.values()) count += versions.length;
      return count;
    },
  };
}

module.exports = { makeStore };
