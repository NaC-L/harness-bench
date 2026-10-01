'use strict';
function failure(code) {
  return Object.assign(new Error(code), {code});
}
function prepare(balances, event) {
  const {id, from, to, amount} = event;
  if (typeof id !== 'string' || id.length === 0 || typeof from !== 'string' || typeof to !== 'string' || from === to || !balances.has(from) || !balances.has(to) || !Number.isSafeInteger(amount) || amount <= 0) {
    throw failure('INVALID_TRANSFER');
  }
  if (balances.get(from) < amount) throw failure('INSUFFICIENT_FUNDS');
  if (!Number.isSafeInteger(balances.get(to) + amount)) throw failure('INVALID_TRANSFER');
  const next = new Map(balances);
  next.set(from, balances.get(from) - amount);
  next.set(to, balances.get(to) + amount);
  return next;
}
module.exports = {prepare, failure};
