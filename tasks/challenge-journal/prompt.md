The local transfer journal gives inconsistent results after a restart or an unsuccessful transfer. Repair `src/` so the existing API obeys the public persistence contract documented in `src/index.js`. The visible tests expose one symptom; preserve successful transfers and the journal format. Keep the change bounded to this synchronous single-owner journal, without dependencies, timers, background work, or a replacement database.

Work only in the current directory. Do not modify `test/` or `package.json`. Verify with `node --test`.
