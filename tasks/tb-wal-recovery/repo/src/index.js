'use strict';

/**
 * Offline async WAL contract (Node.js/CommonJS, no dependencies or I/O).
 *
 * makeEngine({ segmentCapacity = 4, flush = async () => {} } = {}) returns an
 * engine with commitUpdate(key, value), runtimeState(), committedEntries(), and
 * crashSnapshot(). segmentCapacity is a positive integer. Keys are strings;
 * values are plain JSON-compatible data: null, booleans, finite numbers,
 * strings, arrays, and nested plain objects. Every supplied flush succeeds.
 * Handling rejected flushes, malformed snapshots, and invalid inputs is outside
 * this task. Calls begin immediately, including concurrent calls on one engine.
 *
 * commitUpdate reserves a unique increasing LSN synchronously starting at 1 and
 * appends {lsn,key,value} to its segment in LSN order BEFORE awaiting flush.
 * flush receives a deeply detached {lsn,key,value}. Its fulfillment marks that
 * entry durable, but a segment's durableCount counts ONLY the contiguous durable
 * prefix of its own entries. Rotation closes a full segment, starts the next
 * segment (IDs 1,2,...), and cannot reorder entries or lose pending writes.
 *
 * A commit's returned Promise resolves to a detached {lsn,key,value} only when
 * every LSN through that entry is durable. A higher flush may complete first;
 * that commit must wait, not block a caller from completing the lower flush.
 * runtimeState() exposes the key/value map after ONLY the global durable LSN
 * prefix; later writes to a key win in that prefix. committedEntries() returns
 * exactly that prefix as detached {lsn,key,value} entries, in increasing LSN
 * order. Both accessors and crashSnapshot() are synchronous.
 *
 * crashSnapshot() has exactly this shape, with all allocated segments present,
 * including pending entries and the final open segment:
 * {segments:[{segmentId,closed,durableCount,entries:[{lsn,key,value}]}]}.
 * No segment is allocated until its first commit; a new engine snapshots to
 * {segments:[]}. Segment capacity counts appended entries, not completed flushes.
 *
 * recoverEngine(snapshot) is synchronous and returns exactly {state,replayed,
 * stats}. Inspect entries.slice(0,durableCount) of EVERY segment; an omitted
 * durableCount means zero. Entries outside that slice must never be replayed.
 * Merge candidates independently of segment ordering and durable-entry ordering.
 * For duplicate LSNs choose the lowest containing segmentId, NOT any segmentId
 * in the entry payload. Segment IDs and LSNs are positive integers; conflicting
 * duplicate candidates have distinct containing IDs (equal-ID copies agree).
 * Replay the contiguous LSN sequence beginning at 1, stopping at the first gap.
 * No sorting of the entire input before choosing each segment's prefix is valid.
 *
 * state is a plain object mapping keys to the last replayed value. replayed is
 * LSN-sorted and each entry has EXACTLY {segmentId,lsn,key,value}; extra payload
 * fields are ignored. stats has EXACTLY {segmentsScanned,replayedEntries,lastLsn}
 * where segmentsScanned counts all input segments (including empty/non-durable
 * ones), replayedEntries is replayed.length, and lastLsn is the final replayed
 * LSN or zero. Recovery must remain efficient on moderate snapshots: avoid
 * repeatedly scanning/filtering all entries for each replayed LSN.
 *
 * All input values are deeply captured at call time. Neither engine nor recovery
 * mutates caller data. Engine outputs (including flush arguments and fulfilled
 * commit values), recovery state, and recovery replayed entries are deeply
 * independent of internal storage, input data, other outputs, and repeated
 * calls. Mutating any such value must not change another. Arbitrary string keys,
 * including '__proto__', are ordinary data keys, not prototype operations.
 */
const { makeEngine } = require('./engine');
const { recoverEngine } = require('./recovery');

module.exports = { makeEngine, recoverEngine };
