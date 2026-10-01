'use strict';
const fs = require('node:fs');
const path = require('node:path');
function createStorage(directory, append = fs.appendFileSync) {
  fs.mkdirSync(directory, {recursive: true});
  const file = path.join(directory, 'journal.ndjson');
  fs.closeSync(fs.openSync(file, 'a'));
  return {
    read() {
      const bytes = fs.readFileSync(file);
      const end = bytes.lastIndexOf(10) + 1;
      const records = [];
      for (const line of bytes.subarray(0, end).toString('utf8').split('\n').slice(0, -1)) {
        try { records.push(JSON.parse(line)); } catch { /* interrupted writes are skipped */ }
      }
      return {records, validBytes: end, totalBytes: bytes.length};
    },
    repair(loaded) {
      if (loaded.records.length === 0 && loaded.totalBytes > loaded.validBytes) {
        fs.truncateSync(file, loaded.validBytes);
      }
    },
    append(event) { append(file, JSON.stringify(event) + '\n'); }
  };
}
module.exports = {createStorage};
