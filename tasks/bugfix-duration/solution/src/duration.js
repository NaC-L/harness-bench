'use strict';

const UNIT_MS = { ms: 1, s: 1000, m: 60000, h: 3600000, d: 86400000 };

function parseDuration(str) {
  if (typeof str !== 'string') throw new TypeError('Duration must be a string');
  const text = str.trim();
  if (!/^(?:\d+(?:\.\d+)?(?:ms|[smhd]))+$/.test(text)) {
    throw new TypeError('Invalid duration');
  }

  let milliseconds = 0;
  for (const [, amount, unit] of text.matchAll(/(\d+(?:\.\d+)?)(ms|[smhd])/g)) {
    milliseconds += Number(amount) * UNIT_MS[unit];
    if (!Number.isFinite(milliseconds)) throw new TypeError('Duration overflow');
  }
  return milliseconds;
}

module.exports = { parseDuration };
