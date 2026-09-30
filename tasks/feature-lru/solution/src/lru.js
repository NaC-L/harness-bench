'use strict';

class LRUCache {
  #capacity;
  #entries = new Map();

  constructor(capacity) {
    if (!Number.isInteger(capacity) || capacity < 1) {
      throw new RangeError('Capacity must be a positive integer');
    }
    this.#capacity = capacity;
  }

  get(key) {
    if (!this.#entries.has(key)) return undefined;
    const value = this.#entries.get(key);
    this.#entries.delete(key);
    this.#entries.set(key, value);
    return value;
  }

  set(key, value) {
    this.#entries.delete(key);
    this.#entries.set(key, value);
    if (this.#entries.size > this.#capacity) {
      this.#entries.delete(this.#entries.keys().next().value);
    }
    return this;
  }

  has(key) { return this.#entries.has(key); }
  delete(key) { return this.#entries.delete(key); }
  get size() { return this.#entries.size; }
}

module.exports = { LRUCache };
