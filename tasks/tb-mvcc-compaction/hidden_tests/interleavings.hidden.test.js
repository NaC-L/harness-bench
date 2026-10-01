'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { makeStore } = require('../src');

const clone = value => JSON.parse(JSON.stringify(value));

// This oracle never compacts its history. It recomputes publication by walking
// the original batch order, and reads by replaying all eligible operations.
function fullHistoryOracle() {
  const history = [];
  const batches = [];
  let physical = new Set();

  function install(operations, ready) {
    for (const operation of operations) {
      const record = {
        sequence: history.length + 1,
        key: operation.key,
        deleted: operation.type === 'delete',
        value: operation.type === 'put' ? clone(operation.value) : undefined,
      };
      history.push(record);
      physical.add(record.sequence);
    }
    const batch = { end: history.length, ready };
    batches.push(batch);
    return batch;
  }

  function frontier() {
    let result = 0;
    for (const batch of batches) {
      if (!batch.ready) break;
      result = batch.end;
    }
    return result;
  }

  function latest(key, sequence) {
    let result;
    for (const record of history) {
      if (record.key === key && record.sequence <= sequence) result = record;
    }
    return result;
  }

  function read(key, sequence) {
    const record = latest(key, sequence);
    return !record || record.deleted ? undefined : clone(record.value);
  }

  function reclaim(snapshotSequences) {
    const published = frontier();
    const selected = new Set(history.filter(record => record.sequence > published)
      .map(record => record.sequence));
    const keys = new Set(history.map(record => record.key));
    for (const key of keys) {
      for (const sequence of [published, ...snapshotSequences]) {
        const record = latest(key, sequence);
        if (record) selected.add(record.sequence);
      }
    }
    // A selected version may never need to be resurrected from already discarded
    // physical history. Checking that invariant also audits this oracle's count.
    for (const sequence of selected) assert.ok(physical.has(sequence));
    const removed = physical.size - selected.size;
    physical = selected;
    return removed;
  }

  return { install, frontier, read, reclaim, count: () => physical.size };
}

function randomSource(seed) {
  let state = seed >>> 0;
  return limit => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return (state >>> 8) % limit;
  };
}

for (const seed of [7, 29, 101, 4093]) {
  test(`mvcc hidden interleavings: full-history oracle agrees for seeded schedule ${seed}`, () => {
    const store = makeStore();
    const oracle = fullHistoryOracle();
    const random = randomSource(seed);
    const keys = ['a', 'b', 'c', ''];
    const batches = [];
    const snapshots = [];
    let serial = 0;
    let step = 0;

    function operation() {
      const key = keys[random(keys.length)];
      return random(4) === 0 ? { type: 'delete', key } : {
        type: 'put', key,
        value: { id: ++serial, nested: [{ number: random(100), flag: random(2) === 1 }] },
      };
    }

    function ordinary(op) {
      const model = oracle.install([op], true);
      const sequence = op.type === 'put' ? store.put(op.key, op.value) : store.delete(op.key);
      assert.equal(sequence, model.end);
    }

    function prepare(operations) {
      const batch = { token: store.prepare(operations), model: oracle.install(operations, false) };
      batches.push(batch);
      return batch;
    }

    function publish(batch) {
      batch.model.ready = true;
      assert.equal(store.publish(batch.token), oracle.frontier());
    }

    function compact() {
      const expected = oracle.reclaim(snapshots.map(snapshot => snapshot.sequence));
      assert.equal(store.compact(), expected, `reclamation seed=${seed} step=${step}`);
      assert.equal(store.versionCount(), oracle.count());
      assert.equal(store.compact(), 0, `idempotence seed=${seed} step=${step}`);
    }

    function check() {
      const published = oracle.frontier();
      for (const key of keys) {
        assert.deepEqual(store.get(key), oracle.read(key, published),
          `latest key=${key} seed=${seed} step=${step} frontier=${published}`);
        for (const snapshot of snapshots) {
          assert.deepEqual(store.get(key, snapshot.token), oracle.read(key, snapshot.sequence),
            `snapshot key=${key} seed=${seed} step=${step} sequence=${snapshot.sequence}`);
        }
      }
      assert.equal(store.versionCount(), oracle.count(), `physical count seed=${seed} step=${step}`);
    }

    snapshots.push({ token: store.snapshot(), sequence: 0 });
    ordinary({ type: 'put', key: 'a', value: { base: [seed] } });
    snapshots.push({ token: store.snapshot(), sequence: oracle.frontier() });
    const blocked = prepare([
      { type: 'put', key: 'a', value: { prepared: [seed] } },
      { type: 'delete', key: 'b' },
    ]);
    const ready = prepare([{ type: 'put', key: 'a', value: { later: [seed] } }]);
    publish(ready);
    compact();
    check();
    publish(blocked);
    check();

    for (step = 1; step <= 160; step++) {
      const choice = random(10);
      if (choice <= 2) {
        ordinary(operation());
      } else if (choice === 3) {
        ordinary({ type: 'delete', key: keys[random(keys.length)] });
      } else if (choice <= 5) {
        const operations = [];
        const size = 1 + random(3);
        for (let i = 0; i < size; i++) operations.push(operation());
        prepare(operations);
      } else if (choice === 6) {
        publish(batches[random(batches.length)]);
      } else if (choice === 7 && snapshots.length < 6) {
        snapshots.push({ token: store.snapshot(), sequence: oracle.frontier() });
      } else if (choice === 8 && snapshots.length) {
        const index = random(snapshots.length);
        const [snapshot] = snapshots.splice(index, 1);
        store.releaseSnapshot(snapshot.token);
        assert.throws(() => store.get('a', snapshot.token), TypeError);
      } else {
        compact();
      }
      check();
    }

    // Reverse publication drains arbitrarily many ready batches across holes.
    for (let i = batches.length - 1; i >= 0; i--) {
      publish(batches[i]);
      compact();
      check();
    }
    while (snapshots.length) {
      store.releaseSnapshot(snapshots.pop().token);
      compact();
      check();
    }
    compact();
    check();
  });
}
