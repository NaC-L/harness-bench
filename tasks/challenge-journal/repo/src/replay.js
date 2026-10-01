'use strict';
const {prepare} = require('./ledger');
function replay(records, initialBalances) {
  let balances = new Map(Object.entries(initialBalances));
  const seen = new Map();
  const history = [];
  for (const event of [...records].sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0)) {
    balances = prepare(balances, event);
    seen.set(event.id, event);
    history.push(event);
  }
  return {balances, seen, history, sequence: records.length};
}
module.exports = {replay};
