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
  throw new Error('not implemented');
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
  throw new Error('not implemented');
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
  throw new Error('not implemented');
}

module.exports = { diffLines, unifiedHunks, applyHunks };
