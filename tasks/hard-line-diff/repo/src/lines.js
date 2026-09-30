'use strict';

/** Split on LF, preserving empty lines (including a trailing empty line). */
function splitLines(text) {
  return text.split('\n');
}

/** Join with LF; splitLines and joinLines preserve the original text exactly. */
function joinLines(lines) {
  return lines.join('\n');
}

module.exports = { splitLines, joinLines };
