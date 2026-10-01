'use strict';
const {prepare, failure} = require('./ledger');
function replay(records, initialBalances) {
  let balances = new Map(Object.entries(initialBalances));
  const seen = new Map();
  const history = [];
  for (const event of records) {
    try {
      if (!event || typeof event !== 'object' || Array.isArray(event) || Object.keys(event).sort().join(',') !== 'amount,from,id,sequence,to' || event.sequence !== history.length + 1 || seen.has(event.id)) {
        throw failure('CORRUPT_JOURNAL');
      }
      balances = prepare(balances, event);
    } catch { throw failure('CORRUPT_JOURNAL'); }
    seen.set(event.id, event);
    history.push(event);
  }
  return {balances, seen, history, sequence: history.length};
}
module.exports = {replay};
