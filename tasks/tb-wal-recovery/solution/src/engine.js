'use strict';

const { SegmentManager } = require('./segments');

class Engine {
  constructor({ segmentCapacity = 4, flush = async () => {} } = {}) {
    this._segmentManager = new SegmentManager(segmentCapacity);
    this._flush = flush;
    this._nextLsn = 1;
    this._state = new Map();
    this._records = [];
    this._prefix = 0;
  }

  async commitUpdate(key, value) {
    const entry = { lsn: this._nextLsn++, key, value: structuredClone(value) };
    const segment = this._segmentManager.reserveSegment();
    const index = this._segmentManager.appendEntry(segment, entry);
    let acknowledge;
    const committed = new Promise(resolve => { acknowledge = resolve; });
    const record = { entry, durable: false, acknowledge };
    this._records.push(record);

    await this._flush(structuredClone(entry));
    this._segmentManager.markDurable(segment, index);
    record.durable = true;
    while (this._prefix < this._records.length && this._records[this._prefix].durable) {
      const next = this._records[this._prefix++];
      this._state.set(next.entry.key, next.entry.value);
      next.acknowledge(structuredClone(next.entry));
    }
    return committed;
  }

  runtimeState() {
    return structuredClone(Object.fromEntries(this._state));
  }

  committedEntries() {
    return this._records.slice(0, this._prefix).map(record => structuredClone(record.entry));
  }

  crashSnapshot() {
    return this._segmentManager.snapshot();
  }
}

function makeEngine(options) {
  return new Engine(options);
}

module.exports = { makeEngine };
