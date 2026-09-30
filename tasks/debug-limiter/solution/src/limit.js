'use strict';

// createLimiter accepts a positive integer Number concurrency, otherwise throws
// RangeError. It returns run(fn), which always returns a Promise. run rejects
// non-functions with TypeError. Queued functions start in submission order, with
// at most concurrency functions running. Values, promises, synchronous throws,
// and promise rejections settle only the corresponding run result; the limiter
// must remain usable afterward. Each function is invoked once, with no arguments.
function createLimiter(concurrency) {
  if (!Number.isInteger(concurrency) || concurrency < 1) {
    throw new RangeError('Concurrency must be a positive integer');
  }
  let active = 0;
  const queue = [];

  function drain() {
    while (active < concurrency && queue.length > 0) {
      const job = queue.shift();
      active += 1;
      Promise.resolve().then(() => job.fn()).then(job.resolve, job.reject).finally(() => {
        active -= 1;
        drain();
      });
    }
  }

  return function run(fn) {
    if (typeof fn !== 'function') return Promise.reject(new TypeError('Task must be a function'));
    return new Promise((resolve, reject) => {
      queue.push({ fn, resolve, reject });
      drain();
    });
  };
}

module.exports = { createLimiter };
