'use strict';

function recoverEngine(snapshot) {
  const state = new Map();
  const replayed = [];
  let lastLsn = 0;
  for (const segment of snapshot.segments) {
    const count = segment.durableCount ?? segment.entries.length;
    for (const entry of segment.entries.slice(0, count)) {
      if (entry.lsn <= lastLsn) continue;
      replayed.push({ segmentId: segment.segmentId, ...entry });
      state.set(entry.key, entry.value);
      lastLsn = entry.lsn;
    }
  }
  return {
    state: Object.fromEntries(state),
    replayed,
    stats: {
      segmentsScanned: snapshot.segments.length,
      replayedEntries: replayed.length,
      lastLsn,
    },
  };
}

module.exports = { recoverEngine };
