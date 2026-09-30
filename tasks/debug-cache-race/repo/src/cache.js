'use strict';
const { createFlights } = require('./flight');
const { createClock } = require('./clock');

/**
 * createCache({ load, ttlMs = 1000, now = Date.now }) returns a read-through
 * cache. load and now must be functions (otherwise TypeError); ttlMs must be a
 * finite nonnegative Number (otherwise RangeError). now is a side-effect-free,
 * nondecreasing clock returning finite millisecond Numbers.
 *
 * Keys use Map/SameValueZero identity and values may include undefined or null.
 * get(key) always returns a Promise. Missing keys load independently; concurrent
 * reads of the same key share one active load. load is invoked once with exactly
 * one argument, the key, and may return a value, Promise, or thenable, or throw.
 * No particular invocation timing or returned-Promise identity is required.
 * A successful value's TTL starts when that flight commits, not when get starts.
 * Cached/set values expire exactly when now() >= their insertion time + ttlMs.
 * ttlMs = 0 still deduplicates an unsettled flight but never reuses a settled
 * value. Expiration is lazy; no background timers are needed.
 *
 * invalidate(key) removes its value and detaches its active flight immediately.
 * Readers after invalidate must start/join a fresh flight, even while an older
 * one is unresolved. Repeated invalidations are separate barriers, including
 * when the key has no stored value. clear() does the same for every key.
 * set(key, value) detaches the active flight and installs the supplied value
 * immediately with a new TTL. That value wins over all earlier loads, and their
 * later completion must not restart its TTL. If it expires while an old load is
 * pending, get starts a new load, not the detached one.
 *
 * Mutations do not cancel loads or change the outcomes of their original
 * readers. An obsolete flight still delivers its own value/rejection to all its
 * original waiters, but cannot store a value or detach a newer flight. Rejected
 * loads (including synchronous throws and non-Error reasons) are never cached:
 * all waiters receive the same rejection reason, and a subsequent get may retry.
 * load may call invalidate, set, or clear synchronously before returning; the
 * same barrier rules apply. A load may also read another key or read its own key
 * without awaiting it; the latter joins its existing flight.
 *
 * size counts only unexpired stored values, never active flights; reading size
 * discards expired values without detaching flights. Cache instances are isolated.
 * invalidate, set, and clear return undefined. These are the public operations;
 * helpers in flight.js and clock.js are internal implementation details.
 */
function createCache({ load, ttlMs = 1000, now = Date.now } = {}) {
  if (typeof load !== 'function') throw new TypeError('load must be a function');
  if (!Number.isFinite(ttlMs) || ttlMs < 0) {
    throw new RangeError('ttlMs must be a finite nonnegative Number');
  }
  if (typeof now !== 'function') throw new TypeError('now must be a function');

  const values = new Map();
  const flights = createFlights();
  const clock = createClock(ttlMs, now);

  function get(key) {
    if (values.has(key)) {
      const entry = values.get(key);
      if (!clock.expired(entry.deadline)) return Promise.resolve(entry.value);
      values.delete(key);
    }
    return flights.run(key, () => load(key), value => {
      values.set(key, { value, deadline: clock.deadline() });
    });
  }

  return {
    get,
    invalidate(key) {
      values.delete(key);
      flights.forget(key);
    },
    set(key, value) {
      flights.forget(key);
      values.set(key, { value, deadline: clock.deadline() });
    },
    clear() {
      values.clear();
      flights.clear();
    },
    get size() {
      for (const [key, entry] of values) {
        if (clock.expired(entry.deadline)) values.delete(key);
      }
      return values.size;
    }
  };
}

module.exports = { createCache };
