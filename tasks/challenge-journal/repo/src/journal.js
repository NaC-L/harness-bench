'use strict';
const {prepare, failure} = require('./ledger');
function createJournal(state, storage) {
  return {
    transfer(request) {
      if (state.seen.has(request.id)) return state.seen.get(request.id);
      const event = {sequence: ++state.sequence, id: request.id, from: request.from, to: request.to, amount: request.amount};
      state.seen.set(event.id, event);
      state.balances = prepare(state.balances, event);
      state.history.push(event);
      storage.append(event);
      return event;
    },
    balance(account) {
      if (!state.balances.has(account)) throw failure('UNKNOWN_ACCOUNT');
      return state.balances.get(account);
    },
    entries() { return state.history.slice(); }
  };
}
module.exports = {createJournal};
