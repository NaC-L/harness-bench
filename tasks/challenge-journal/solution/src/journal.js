'use strict';
const {prepare, failure} = require('./ledger');
function createJournal(state, storage) {
  return {
    transfer(request) {
      const previous = state.seen.get(request.id);
      if (previous) {
        if (previous.from !== request.from || previous.to !== request.to || previous.amount !== request.amount) {
          throw failure('IDEMPOTENCY_CONFLICT');
        }
        return {...previous};
      }
      const event = {sequence: state.sequence + 1, id: request.id, from: request.from, to: request.to, amount: request.amount};
      const next = prepare(state.balances, event);
      storage.append(event);
      state.balances = next;
      state.sequence = event.sequence;
      state.seen.set(event.id, event);
      state.history.push(event);
      return {...event};
    },
    balance(account) {
      if (!state.balances.has(account)) throw failure('UNKNOWN_ACCOUNT');
      return state.balances.get(account);
    },
    entries() { return state.history.map((event) => ({...event})); }
  };
}
module.exports = {createJournal};
