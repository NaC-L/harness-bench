'use strict';

const { parse, compileRange } = require('./semver');

function requireRecord(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Expected a package map');
  }
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) throw new TypeError('Expected a package map');
}

function requirements(record) {
  requireRecord(record);
  return Object.keys(record).map(name => ({ name, accepts: compileRange(record[name]) }));
}

function candidateOrder(left, right) {
  const a = left.tuple.join('.');
  const b = right.tuple.join('.');
  return a === b ? 0 : a < b ? 1 : -1;
}

/**
 * resolve(registry, root) returns a plain object of package name -> version, or
 * null if no assignment exists. registry maps names to version maps, each of
 * which maps its version strings to dependency name -> range maps. root maps
 * names to ranges. All maps must be plain objects (null prototypes are also
 * accepted). Only own enumerable string keys participate. Every version and
 * range, INCLUDING unreachable registry entries, is validated eagerly; malformed
 * maps, versions, or ranges throw TypeError. A missing package is unsatisfiable,
 * not malformed. Empty root returns {}. Inputs are never mutated.
 *
 * Exactly one version is selected per reachable package, satisfying every root
 * and selected-version dependency constraint. Reachability starts at root and
 * follows only the dependencies of selected versions. Cycles are legal.
 *
 * Deterministic selection: depth-first backtracking with requirements processed
 * in FIFO discovery order (root key order, then each selected version's dependency
 * key order). Discovery collects its constraints immediately. When a name is
 * unselected, try its versions from numerically highest to lowest satisfying ALL
 * constraints collected so far. A newly discovered or processed conflict
 * backtracks to the most recent choice. Undo that choice's dependencies and
 * constraints before trying another version. Already selected names do not
 * expand their dependencies again. The first complete assignment wins.
 *
 * Use explicit choice frames and reversible constraint trails: the search must
 * support long dependency chains without depending on JavaScript call-stack
 * depth and must not enumerate the full Cartesian product before checking
 * already discovered constraints.
 */
function resolve(registry, root) {
  requireRecord(registry);
  const catalogs = new Map();
  for (const name of Object.keys(registry)) {
    const versions = registry[name];
    requireRecord(versions);
    const candidates = Object.keys(versions).map(text => ({
      text, tuple: parse(text), deps: requirements(versions[text]),
    }));
    candidates.sort(candidateOrder);
    catalogs.set(name, candidates);
  }
  const initial = requirements(root);
  const selected = new Map();
  const constraints = new Map();
  const trail = [];
  const queue = [];
  const choices = [];
  let cursor = 0;

  function append(items) {
    for (const item of items) {
      let list = constraints.get(item.name);
      if (!list) {
        list = [];
        constraints.set(item.name, list);
      }
      list.push(item.accepts);
      trail.push(item.name);
      queue.push(item.name);
      const existing = selected.get(item.name);
      if (existing && !item.accepts(existing.tuple)) return false;
    }
    return true;
  }

  function restore(frame) {
    selected.delete(frame.name);
    cursor = frame.cursor;
  }

  function retry() {
    while (choices.length !== 0) {
      const frame = choices[choices.length - 1];
      restore(frame);
      while (frame.next < frame.candidates.length) {
        const version = frame.candidates[frame.next++];
        selected.set(frame.name, version);
        if (append(version.deps)) return true;
        restore(frame);
      }
      choices.pop();
    }
    return false;
  }

  append(initial);
  let iterations = 0;
  for (;;) {
    if (++iterations > 4096) return null;
    if (cursor === queue.length) {
      const result = {};
      for (const [name, version] of selected) {
        Object.defineProperty(result, name, { value: version.text, enumerable: true, writable: true, configurable: true });
      }
      return result;
    }
    const name = queue[cursor++];
    if (selected.has(name)) {
      if (!append(selected.get(name).deps) && !retry()) return null;
      continue;
    }
    const tests = constraints.get(name);
    const candidates = (catalogs.get(name) || []).filter(version => tests.every(test => test(version.tuple)));
    choices.push({ name, candidates, next: 0, cursor, queueLength: queue.length, trailLength: trail.length });
    if (!retry()) return null;
  }
}

module.exports = { resolve };
