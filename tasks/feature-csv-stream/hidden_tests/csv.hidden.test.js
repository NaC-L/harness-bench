'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createParser, parse } = require('../src/csv');
const { toObjects } = require('../src/rows');

function stream(chunks, options) {
  const parser = createParser(options);
  const records = [];
  for (const chunk of chunks) records.push(...parser.push(chunk));
  records.push(...parser.end());
  return records;
}

function everySplit(text, expected, options) {
  const single = parse(text, options);
  assert.deepEqual(single, expected, `single push for ${JSON.stringify(text)}`);
  for (let index = 0; index <= text.length; index += 1) {
    assert.deepEqual(
      stream([text.slice(0, index), '', text.slice(index)], options),
      single,
      `boundary ${index} for ${JSON.stringify(text)}`,
    );
  }
  assert.deepEqual(stream(['', ...text.split(''), ''], options), single, 'one-code-unit chunks');
}

function syntaxAt(chunks, line) {
  assert.throws(() => stream(chunks), error => {
    assert.ok(error instanceof SyntaxError, `expected SyntaxError, got ${error}`);
    assert.match(error.message, new RegExp(`\\bline ${line}\\b`));
    return true;
  });
}

function syntaxAtEverySplit(text, line) {
  syntaxAt([text], line);
  for (let index = 0; index <= text.length; index += 1) {
    syntaxAt([text.slice(0, index), '', text.slice(index)], line);
  }
  syntaxAt(['', ...text.split(''), ''], line);
}

test('every chunk boundary preserves quoted commas and doubled quote escapes', () => {
  everySplit('""""', [['"']]);
  everySplit('"a""b",tail\r\n', [['a"b', 'tail']]);
  everySplit('"left,""right""",end\n"","""",last', [
    ['left,"right"', 'end'], ['', '"', 'last'],
  ]);
});

test('every chunk boundary preserves raw mixed newlines inside quoted fields', () => {
  everySplit('"a\r\nb\rc\nd",x\r\nlast,row\r', [
    ['a\r\nb\rc\nd', 'x'], ['last', 'row'],
  ]);
  everySplit('"\r\n",other\n"\n\r",end', [['\r\n', 'other'], ['\n\r', 'end']]);
});

test('every chunk boundary distinguishes empty input blank rows and trailing separators', () => {
  everySplit('', []);
  for (const separator of ['\n', '\r', '\r\n']) everySplit(separator, [['']]);
  everySplit('\n\n', [[''], ['']]);
  everySplit('a\r\n\r\nb\r', [['a'], [''], ['b']]);
  everySplit('a\r\r\n\nb', [['a'], [''], [''], ['b']]);
  everySplit(',,\n,\r\nlast,', [['', '', ''], ['', ''], ['last', '']]);
  everySplit('""', [['']]);
});

test('every chunk boundary keeps quotes within unquoted fields literal', () => {
  everySplit('a"b,c"d\n "quoted",tail', [['a"b', 'c"d'], [' "quoted"', 'tail']]);
  everySplit('a""b,close"quote\n""\n', [['a""b', 'close"quote'], ['']]);
});

test('every chunk boundary strips only an initial BOM', () => {
  everySplit('\uFEFF', []);
  everySplit('\uFEFFname,value\r\nAda,1', [['name', 'value'], ['Ada', '1']]);
  everySplit('\uFEFF"quoted",tail', [['quoted', 'tail']]);
  everySplit('a,\uFEFFb\n\uFEFFc,d', [['a', '\uFEFFb'], ['\uFEFFc', 'd']]);
  everySplit('\uFEFF\uFEFFx,y', [['\uFEFFx', 'y']]);
});

test('every chunk boundary preserves Unicode including split surrogate pairs', () => {
  everySplit('α,🙂\r\n"汉字\n🙂",é', [['α', '🙂'], ['汉字\n🙂', 'é']]);
});

test('every chunk boundary honors semicolon delimiters without treating commas specially', () => {
  everySplit('a;b,c;"d;e"\r\n"x\r\ny";;', [
    ['a', 'b,c', 'd;e'], ['x\r\ny', '', ''],
  ], { delimiter: ';' });
});

test('every chunk boundary honors pipe tab and space delimiters', () => {
  everySplit('a|"b|c"|d\n||', [['a', 'b|c', 'd'], ['', '', '']], { delimiter: '|' });
  everySplit('a\t"b\tc"\t\r\n', [['a', 'b\tc', '']], { delimiter: '\t' });
  everySplit('one "two three" four', [['one', 'two three', 'four']], { delimiter: ' ' });
});

test('a CR emits immediately and its split LF never emits a second record', () => {
  const parser = createParser();
  assert.deepEqual(parser.push('a,b\r'), [['a', 'b']]);
  assert.deepEqual(parser.push(''), []);
  assert.deepEqual(parser.push('\nnext'), []);
  assert.deepEqual(parser.push(',row\r'), [['next', 'row']]);
  assert.deepEqual(parser.push('\n'), []);
  assert.deepEqual(parser.end(), []);
});

test('a split doubled quote is not mistaken for the end of a quoted field', () => {
  const parser = createParser();
  assert.deepEqual(parser.push('"left"'), []);
  assert.deepEqual(parser.push(''), []);
  assert.deepEqual(parser.push('"right",next\nunfinished'), [['left"right', 'next']]);
  assert.deepEqual(parser.end(), [['unfinished']]);
  const finalQuote = createParser();
  assert.deepEqual(finalQuote.push('"complete'), []);
  assert.deepEqual(finalQuote.push('"'), []);
  assert.deepEqual(finalQuote.end(), [['complete']]);
});

test('push returns only new records and parser instances retain independent state', () => {
  const first = createParser();
  const second = createParser({ delimiter: ';' });
  assert.deepEqual(first.push('one,two\n"pending'), [['one', 'two']]);
  assert.deepEqual(second.push('a;b\rc'), [['a', 'b']]);
  assert.deepEqual(first.push('\nvalue",end\n'), [['pending\nvalue', 'end']]);
  assert.deepEqual(first.push(''), []);
  assert.deepEqual(second.push(';d'), []);
  assert.deepEqual(first.end(), []);
  assert.deepEqual(second.end(), [['c', 'd']]);
});

test('text after closing quotes is rejected during push with physical line numbers', () => {
  const parser = createParser();
  assert.deepEqual(parser.push('"closed"'), []);
  assert.throws(() => parser.push(' '), error => error instanceof SyntaxError && /\bline 1\b/.test(error.message));
  syntaxAtEverySplit('"closed"oops\n', 1);
  syntaxAtEverySplit('a,b\r\n"first\nsecond\rthird\r\nfourth"x,tail', 5);
  syntaxAtEverySplit('\n"first\r\nsecond\nlast"\t', 4);
  syntaxAtEverySplit('a"literal,b\n"ok" ', 2);
  syntaxAtEverySplit('"x"\r\n"y"\n"z"\r"done"!', 4);
});

test('unterminated quotes fail only at end and report the physical EOF line', () => {
  for (const [text, line] of [
    ['"unterminated', 1],
    ['"first\r\nsecond\rlast\n', 4],
    ['a\r\n"more\n', 3],
    ['"""', 1],
  ]) {
    const parser = createParser();
    assert.doesNotThrow(() => parser.push(text));
    assert.throws(() => parser.end(), error => error instanceof SyntaxError &&
      new RegExp(`\\bline ${line}\\b`).test(error.message));
    syntaxAtEverySplit(text, line);
  }
});

test('delimiter validation is strict and both APIs reject invalid delimiters', () => {
  for (const delimiter of ['', 'ab', '🙂', '"', '\r', '\n', null, 1, true, {}, []]) {
    assert.throws(() => createParser({ delimiter }), RangeError);
    assert.throws(() => parse('x', { delimiter }), RangeError);
  }
  assert.deepEqual(parse('a,b', { delimiter: undefined }), [['a', 'b']]);
  for (const value of [undefined, null, 1, true, {}, [], new String('x')]) {
    assert.throws(() => createParser().push(value), TypeError);
    assert.throws(() => parse(value), TypeError);
  }
});

test('end is idempotent and all pushes after end fail', () => {
  const parser = createParser();
  assert.deepEqual(parser.push('x,y'), []);
  assert.deepEqual(parser.end(), [['x', 'y']]);
  assert.deepEqual(parser.end(), []);
  assert.throws(() => parser.push('later'), Error);
  assert.throws(() => parser.push(''), Error);
  const empty = createParser();
  assert.deepEqual(empty.end(), []);
  assert.deepEqual(empty.end(), []);
  assert.throws(() => empty.push(''), Error);
});

test('parse header mode preserves duplicate suffixes short rows BOM and custom delimiter', () => {
  assert.deepEqual(parse('\uFEFFx;x;x_2;x\r\n1;2;3;4\r\nshort\r\n', {
    delimiter: ';', header: true,
  }), [
    { x: '1', x_2: '2', x_2_2: '3', x_3: '4' },
    { x: 'short', x_2: '', x_2_2: '', x_3: '' },
  ]);
  assert.deepEqual(parse('name,note\nAda,"first\r\nsecond"\n', { header: true }), [
    { name: 'Ada', note: 'first\r\nsecond' },
  ]);
  assert.deepEqual(parse('', { header: true }), []);
  assert.deepEqual(parse('only,headers\n', { header: true }), []);
  assert.deepEqual(parse('a,b\n1,2', { header: false }), [['a', 'b'], ['1', '2']]);
});

test('parse header mode treats prototype-related column names as own data properties', () => {
  const objects = parse('__proto__,constructor,toString\nplain,ctor,string\n', { header: true });
  assert.equal(objects.length, 1);
  assert.equal(Object.getPrototypeOf(objects[0]), Object.prototype);
  for (const [key, value] of [['__proto__', 'plain'], ['constructor', 'ctor'], ['toString', 'string']]) {
    assert.ok(Object.hasOwn(objects[0], key));
    assert.equal(objects[0][key], value);
  }
});

test('streaming header option never converts records into objects', () => {
  assert.deepEqual(stream(['a,b\n', '1,2'], { header: true }), [['a', 'b'], ['1', '2']]);
});

// These helper contracts already pass in the unmodified starting repository.
test('regression trap: duplicate header suffixes never collide with earlier names', () => {
  assert.deepEqual(toObjects([['x', 'x', 'x_2', 'x', '', ''], ['1', '2', '3', '4', '5', '6']]), [
    { x: '1', x_2: '2', x_2_2: '3', x_3: '4', '': '5', _2: '6' },
  ]);
  assert.deepEqual(toObjects([['x_2', 'x', 'x'], ['a', 'b', 'c']]), [
    { x_2: 'a', x: 'b', x_3: 'c' },
  ]);
});

test('regression trap: inferred headers pad short records and ignore surplus cells', () => {
  assert.deepEqual(toObjects([['a', 'b'], ['one'], ['two', 'three', 'discard'], []], { header: true }), [
    { a: 'one', b: '' }, { a: 'two', b: 'three' }, { a: '', b: '' },
  ]);
});

test('regression trap: explicit frozen headers preserve input and special keys as data', () => {
  const header = Object.freeze(['__proto__', 'constructor', 'toString']);
  const records = Object.freeze([Object.freeze(['p', 'c', 's']), Object.freeze(['next'])]);
  const options = Object.freeze({ header });
  const objects = toObjects(records, options);
  assert.deepEqual(objects.map(object => Object.keys(object)), [header, header]);
  assert.deepEqual(objects.map(object => header.map(key => object[key])), [
    ['p', 'c', 's'], ['next', '', ''],
  ]);
  for (const object of objects) {
    assert.equal(Object.getPrototypeOf(object), Object.prototype);
    for (const key of header) {
      const descriptor = Object.getOwnPropertyDescriptor(object, key);
      assert.equal(descriptor.enumerable, true);
      assert.equal(descriptor.writable, true);
    }
  }
  objects[0].__proto__ = 'changed';
  assert.equal(objects[0].__proto__, 'changed');
  assert.equal(Object.getPrototypeOf(objects[0]), Object.prototype);
  assert.deepEqual(records, [['p', 'c', 's'], ['next']]);
  assert.deepEqual(header, ['__proto__', 'constructor', 'toString']);
});

test('regression trap: empty inputs and explicit empty headers retain helper semantics', () => {
  assert.deepEqual(toObjects([]), []);
  assert.deepEqual(toObjects([['header']]), []);
  assert.deepEqual(toObjects([['ignored'], []], { header: [] }), [{}, {}]);
  assert.deepEqual(toObjects([['a'], ['b']], { header: ['name'] }), [{ name: 'a' }, { name: 'b' }]);
});

test('regression trap: invalid helper header modes remain TypeErrors', () => {
  for (const header of [false, null, 'name', 1, {}]) {
    assert.throws(() => toObjects([['a'], ['value']], { header }), TypeError);
  }
});
