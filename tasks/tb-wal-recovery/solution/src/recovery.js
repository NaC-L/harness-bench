'use strict';

function recoverEngine(snapshot) {
  const candidates = new Map();
  for (const segment of snapshot.segments) {
    const count = segment.durableCount ?? 0;
    for (let index = 0; index < count; index += 1) {
      const entry = segment.entries[index];
      const previous = candidates.get(entry.lsn);
      if (!previous || segment.segmentId < previous.segmentId) {
        candidates.set(entry.lsn, {
          segmentId: segment.segmentId,
          lsn: entry.lsn,
          key: entry.key,
          value: entry.value,
        });
      }
    }
  }

  const state = new Map();
  const replayed = [];
  let lsn = 1;
  while (candidates.has(lsn)) {
    const entry = candidates.get(lsn++);
    state.set(entry.key, structuredClone(entry.value));
    replayed.push(structuredClone(entry));
  }
  return {
    state: Object.fromEntries(state),
    replayed,
    stats: {
      segmentsScanned: snapshot.segments.length,
      replayedEntries: replayed.length,
      lastLsn: lsn - 1,
    },
  };
}

module.exports = { recoverEngine };
