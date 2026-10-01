'use strict';

const { SegmentManager } = require('./segments');

class Engine {
  constructor({ segmentCapacity = 4, flush = async () => {} } = {}) {
    this._segmentManager = new SegmentManager(segmentCapacity);
    this._flush = flush;
    this._nextLsn = 1;
    this._state = new Map();
    this._committed = [];
  }

  async commitUpdate(key, value) {
    const entry = { lsn: this._nextLsn++, key, value };
    const segment = this._segmentManager.reserveSegment();
    await this._flush({ ...entry });
    this._segmentManager.appendEntry(segment, entry);
    this._segmentManager.markDurable(segment);
    this._state.set(key, value);
    this._committed.push(entry);
    return { ...entry };
  }

  runtimeState() {
    return Object.fromEntries(this._state);
  }

  committedEntries() {
    return this._committed.map(entry => ({ ...entry }));
  }

  crashSnapshot() {
    return this._segmentManager.snapshot();
  }
}

function makeEngine(options) {
  return new Engine(options);
}

module.exports = { makeEngine };
