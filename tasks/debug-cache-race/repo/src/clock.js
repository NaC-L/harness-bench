'use strict';

function createClock(ttlMs, now) {
  return {
    deadline() {
      return now() + ttlMs;
    },
    expired(deadline) {
      return now() >= deadline;
    }
  };
}

module.exports = { createClock };
