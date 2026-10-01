'use strict';
const {createStorage} = require('./storage');
const {replay} = require('./replay');
const {createJournal} = require('./journal');

/**
 * openJournal(directory, {initialBalances, append?}) is synchronous. Directory
 * is owned by one instance at a time; reopen using the SAME initialBalances.
 * Initial balances are trusted nonnegative safe integers keyed by account name.
 * All persistence is directory/journal.ndjson; no other files are required.
 *
 * API: transfer({id, from, to, amount}) -> receipt; balance(account) -> number;
 * entries() -> committed receipts in sequence order. Unknown balance account
 * throws UNKNOWN_ACCOUNT. Receipts contain exactly sequence,id,from,to,amount.
 * ids must be nonempty strings, accounts distinct known strings, and amounts
 * positive safe integers. Destination balance must remain a safe integer.
 * Invalid transfers throw INVALID_TRANSFER; insufficient balance throws
 * INSUFFICIENT_FUNDS. Failed attempts change neither state, id ownership,
 * sequence, nor bytes. Successful sequences start at 1 and are contiguous.
 *
 * A committed id replayed with the same from/to/amount returns its original
 * receipt without applying or appending again (even if funds are now gone).
 * A different payload with that id throws IDEMPOTENCY_CONFLICT before ordinary
 * transfer validation. Never consume an id until the transfer commits.
 *
 * Append one JSON receipt + newline BEFORE publishing state. An append error is
 * propagated unchanged, leaves all in-memory state intact, and permits retry.
 * Optional append(file, line) is a synchronous durability adapter: it either
 * writes that entire line or throws BEFORE writing any bytes. Default is
 * fs.appendFileSync. Power-loss fsync and simultaneous owners are out of scope.
 *
 * Reopen replays complete records in FILE order. Invalid JSON, invalid transfers,
 * duplicate ids, sequence gaps/reordering all throw CORRUPT_JOURNAL; a failed
 * open must not rewrite committed data. An unterminated final fragment is not a
 * commit: ignore it and truncate it after successful replay, so later appends
 * remain readable. Empty files are valid. State and receipts are defensive
 * snapshots; mutating requests or returned values cannot alter future behavior.
 */
function openJournal(directory, options) {
  const storage = createStorage(directory, options.append);
  const loaded = storage.read();
  const state = replay(loaded.records, options.initialBalances);
  storage.repair(loaded);
  return createJournal(state, storage);
}
module.exports = {openJournal};
