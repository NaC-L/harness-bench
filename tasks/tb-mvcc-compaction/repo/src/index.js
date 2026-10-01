'use strict';

/**
 * Public API: require('./src') exports { makeStore }.
 *
 * makeStore() returns an independent in-memory MVCC store with these methods:
 *   put(key, value) -> the positive integer sequence allocated to this write.
 *   delete(key) -> the positive integer sequence allocated to this tombstone.
 *   prepare(operations) -> an opaque, store-owned batch token.
 *   publish(token) -> the current published frontier (an integer, initially 0).
 *   snapshot() -> an opaque, store-owned snapshot token.
 *   releaseSnapshot(token) -> undefined.
 *   get(key[, snapshotToken]) -> a detached JSON value, or undefined if absent.
 *   compact() -> the number of physical versions discarded by this call.
 *   versionCount() -> the total number of physical versions across all keys.
 *
 * Valid inputs: keys are strings (including empty strings); values are JSON data
 * (null, booleans, strings, finite numbers, arrays, and plain objects, recursively;
 * no cycles or undefined). Operations is a nonempty array of { type: 'put', key,
 * value } or { type: 'delete', key }. Inputs outside this domain need not be
 * supported, except token lifetime/ownership errors specified below.
 *
 * Every operation reserves one increasing sequence, including writes to an
 * already absent key and repeated keys within a batch. prepare installs all its
 * versions immediately but leaves the batch unpublished. A batch occupies one
 * contiguous interval and publishes atomically. publish marks it ready; the
 * frontier advances only over contiguous ready batches, never across an earlier
 * unready batch. put/delete install a ready one-operation batch under these SAME
 * rules: their returned sequence is not a promise of immediate read visibility.
 * Re-publishing a valid batch is idempotent, returning the then-current frontier.
 * Foreign or fabricated batch tokens cause publish to throw TypeError.
 *
 * snapshot captures the current published frontier, not the allocated sequence.
 * get without a snapshot reads at the current frontier. With a live snapshot it
 * reads at that captured sequence, even after further writes and compactions.
 * The last version for that key at or below the read sequence wins; a tombstone
 * means absent. Sequence-zero snapshots and separate tokens at the same sequence
 * are valid. releaseSnapshot invalidates just that token. Using a released,
 * foreign, or fabricated token in get/releaseSnapshot throws TypeError. Passing
 * undefined as the optional get argument is equivalent to omitting it.
 *
 * Compaction's exact retained set, independently for every key, is the union of:
 *   (1) ALL versions strictly above the current published frontier;
 *   (2) the newest version at or below that frontier, if any;
 *   (3) the newest version at or below EACH live snapshot sequence, if any.
 * Keep tombstones in this set; deduplicate versions selected by multiple bounds.
 * Discard every other version. The allocated sequence is NOT a visibility bound.
 * There is no extra oldest-snapshot interval retention. Repeated compaction with
 * unchanged publication/snapshots discards zero versions. Releasing snapshots
 * permits reclamation on the next compaction, not necessarily at release time.
 *
 * Values are detached recursively when written (including prepare) and on every
 * read: mutating caller inputs or returned nested objects must not alter history.
 * The model uses no disk, network, clock, or background publication callbacks.
 */
const { makeStore } = require('./store');

module.exports = { makeStore };
