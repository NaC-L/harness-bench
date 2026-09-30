'use strict';

// A detached flight still settles its original callers. The registry tracks
// only flights available for subsequent readers of each key.
function createFlights() {
  const pending = new Map();

  return {
    run(key, work, commit) {
      if (pending.has(key)) return pending.get(key);
      const promise = Promise.resolve().then(work).then(value => {
        pending.delete(key);
        commit(value);
        return value;
      });
      pending.set(key, promise);
      return promise;
    },
    forget(key) {
      pending.delete(key);
    },
    clear() {
      pending.clear();
    }
  };
}

module.exports = { createFlights };
