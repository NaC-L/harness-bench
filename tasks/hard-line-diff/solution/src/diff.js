'use strict';

/**
 * Return an edit script of { op: 'equal' | 'delete' | 'insert', line: string }.
 * a and b are arrays of strings; lines are compared by exact string equality.
 * Reading equal/delete entries reconstructs a; equal/insert reconstructs b.
 * Equal entries must form a longest common subsequence: the number of deletes
 * plus inserts equals a.length + b.length - 2 * LCS(a, b).
 * Results must be deterministic. In every maximal region without an equal
 * entry, all deletes precede all inserts. No particular LCS is otherwise required.
 * Neither input may be mutated. Empty arrays and repeated/empty strings work.
 * Small changes to 20,000-line inputs must run well under a second: use a Myers
 * O((N + M) * D) algorithm (linear when D is zero), not an O(N * M) LCS table.
 * Here N/M are input lengths and D is the minimal number of inserts + deletes.
 */
function diffLines(a, b) {
  const trace = [];
  let previous;
  for (let distance = 0; distance <= a.length + b.length; distance++) {
    // Store only reachable diagonals, rather than an N+M-sized snapshot.
    const frontier = new Int32Array(2 * distance + 1);
    for (let diagonal = -distance; diagonal <= distance; diagonal += 2) {
      let x;
      if (distance === 0) {
        x = 0;
      } else if (diagonal === -distance || (diagonal !== distance &&
          previous[diagonal - 1 + distance - 1] < previous[diagonal + 1 + distance - 1])) {
        x = previous[diagonal + 1 + distance - 1];
      } else {
        x = previous[diagonal - 1 + distance - 1] + 1;
      }
      let y = x - diagonal;
      while (x < a.length && y < b.length && a[x] === b[y]) {
        x++;
        y++;
      }
      frontier[diagonal + distance] = x;
      if (x >= a.length && y >= b.length) {
        trace.push(frontier);
        return reconstruct(a, b, trace);
      }
    }
    trace.push(frontier);
    previous = frontier;
  }
}

function reconstruct(a, b, trace) {
  const reversed = [];
  let x = a.length;
  let y = b.length;
  for (let distance = trace.length - 1; distance > 0; distance--) {
    const diagonal = x - y;
    const previous = trace[distance - 1];
    const down = diagonal === -distance || (diagonal !== distance &&
      previous[diagonal - 1 + distance - 1] < previous[diagonal + 1 + distance - 1]);
    const previousDiagonal = down ? diagonal + 1 : diagonal - 1;
    const previousX = previous[previousDiagonal + distance - 1];
    const previousY = previousX - previousDiagonal;
    while (x > previousX && y > previousY) {
      reversed.push({ op: 'equal', line: a[--x] });
      y--;
    }
    if (down) reversed.push({ op: 'insert', line: b[--y] });
    else reversed.push({ op: 'delete', line: a[--x] });
  }
  while (x > 0) {
    reversed.push({ op: 'equal', line: a[--x] });
    y--;
  }
  reversed.reverse();

  // Reorder only within an unequal run, preserving both source line orders.
  const result = [];
  for (let i = 0; i < reversed.length;) {
    if (reversed[i].op === 'equal') {
      result.push(reversed[i++]);
      continue;
    }
    let end = i;
    while (end < reversed.length && reversed[end].op !== 'equal') end++;
    for (let j = i; j < end; j++) {
      if (reversed[j].op === 'delete') result.push(reversed[j]);
    }
    for (let j = i; j < end; j++) {
      if (reversed[j].op === 'insert') result.push(reversed[j]);
    }
    i = end;
  }
  return result;
}

/**
 * Return unified hunks: [{ oldStart, oldLines, newStart, newLines, lines }].
 * context is a nonnegative integer, default 3. Hunk lines are original strings
 * prefixed with ' ' (equal), '-' (delete), or '+' (insert); remove exactly one
 * prefix to recover a line, even when the original starts with a prefix itself.
 * oldLines counts context + deletes; newLines counts context + inserts.
 * Include up to context unchanged lines before/after each changed region.
 * Merge regions if the intervening unchanged gap is <= 2 * context (their
 * context would touch or overlap). Do not duplicate context in merged hunks.
 * Starts are 1-based, except a zero-line range names the line BEFORE the range:
 * oldLines === 0 uses the preceding old line number (0 for insertion at top),
 * and newLines === 0 uses the preceding new line number (0 for deletion at top).
 * Coordinates refer to the complete original a and result b, not a local hunk.
 * Identical inputs return []. Use diffLines' minimality and deletion ordering.
 * Neither input may be mutated. Inputs follow the diffLines contract.
 */
function unifiedHunks(a, b, { context = 3 } = {}) {
  const script = diffLines(a, b);
  const groups = [];
  for (let i = 0; i < script.length;) {
    if (script[i].op === 'equal') {
      i++;
      continue;
    }
    const start = i;
    while (i < script.length && script[i].op !== 'equal') i++;
    const range = { start: Math.max(0, start - context), end: Math.min(script.length, i + context) };
    const previous = groups[groups.length - 1];
    if (previous && range.start <= previous.end) previous.end = range.end;
    else groups.push(range);
  }

  const hunks = [];
  let cursor = 0;
  let oldBefore = 0;
  let newBefore = 0;
  for (const group of groups) {
    while (cursor < group.start) {
      if (script[cursor].op !== 'insert') oldBefore++;
      if (script[cursor].op !== 'delete') newBefore++;
      cursor++;
    }
    const hunk = { oldStart: 0, oldLines: 0, newStart: 0, newLines: 0, lines: [] };
    const startOld = oldBefore;
    const startNew = newBefore;
    while (cursor < group.end) {
      const edit = script[cursor++];
      hunk.lines.push((edit.op === 'equal' ? ' ' : edit.op === 'delete' ? '-' : '+') + edit.line);
      if (edit.op !== 'insert') {
        hunk.oldLines++;
        oldBefore++;
      }
      if (edit.op !== 'delete') {
        hunk.newLines++;
        newBefore++;
      }
    }
    hunk.oldStart = startOld + (hunk.oldLines > 0 ? 1 : 0);
    hunk.newStart = startNew + (hunk.newLines > 0 ? 1 : 0);
    hunks.push(hunk);
  }
  return hunks;
}

/**
 * Return a new array by applying unified hunks to a, without mutating either.
 * Hunk old coordinates refer to the original a: apply in the given order,
 * tracking offsets caused by earlier insertions/deletions. Hunks must be
 * nonoverlapping and ordered; their counts and new coordinates must agree with
 * their lines. Verify every ' ' and '-' line exactly against a before consuming
 * it. Unmentioned original lines are retained. An empty hunk array returns a copy.
 * A mismatch or malformed/nonapplicable hunk throws Error with a message
 * containing 'hunk <index> does not apply', where index is zero-based.
 */
function applyHunks(a, hunks) {
  const result = [];
  let cursor = 0;
  for (let index = 0; index < hunks.length; index++) {
    const hunk = hunks[index];
    const fail = () => { throw new Error(`hunk ${index} does not apply`); };
    if (!hunk || !Array.isArray(hunk.lines) ||
        !['oldStart', 'oldLines', 'newStart', 'newLines'].every(key =>
          Number.isInteger(hunk[key]) && hunk[key] >= 0)) fail();
    const start = hunk.oldStart - (hunk.oldLines > 0 ? 1 : 0);
    if (start < cursor || start > a.length || start + hunk.oldLines > a.length) fail();
    while (cursor < start) result.push(a[cursor++]);
    const newStart = result.length + (hunk.newLines > 0 ? 1 : 0);
    if (hunk.newStart !== newStart) fail();
    let oldCount = 0;
    let newCount = 0;
    for (const line of hunk.lines) {
      if (typeof line !== 'string' || ![' ', '-', '+'].includes(line[0])) fail();
      const prefix = line[0];
      const value = line.slice(1);
      if (prefix !== '+') {
        if (cursor >= a.length || a[cursor] !== value) fail();
        cursor++;
        oldCount++;
      }
      if (prefix !== '-') {
        result.push(value);
        newCount++;
      }
    }
    if (oldCount !== hunk.oldLines || newCount !== hunk.newLines) fail();
  }
  while (cursor < a.length) result.push(a[cursor++]);
  return result;
}

module.exports = { diffLines, unifiedHunks, applyHunks };
