import { units, convert } from './units.js';

const decimal = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
const help = `Usage:
  node bin/convert.js convert <value> <from> <to> [--precision N]
  node bin/convert.js units
  node bin/convert.js --help
  node bin/convert.js -h
  node bin/convert.js --version

Examples:
  node bin/convert.js convert 1 km m
  node bin/convert.js convert -40 c f --precision 1
`;

function distance(left, right) {
  let previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let row = 1; row <= left.length; row += 1) {
    const current = [row];
    for (let column = 1; column <= right.length; column += 1) {
      current[column] = Math.min(
        current[column - 1] + 1,
        previous[column] + 1,
        previous[column - 1] + (left[row - 1] === right[column - 1] ? 0 : 1),
      );
    }
    previous = current;
  }
  return previous[right.length];
}

function unknownUnit(name) {
  let nearest;
  let bestDistance = 3;
  for (const unit of units) {
    const candidateDistance = distance(name.toLowerCase(), unit.symbol);
    if (candidateDistance < bestDistance) {
      nearest = unit.symbol;
      bestDistance = candidateDistance;
    }
  }
  return `Unknown unit "${name}".${nearest ? ` Did you mean "${nearest}"?` : ''}`;
}

function unexpected(argument) {
  if (argument.startsWith('-')) {
    return `Unknown flag "${argument}".${argument === '--precison' ? ' Did you mean "--precision"?' : ''}`;
  }
  return `Unexpected extra argument "${argument}".`;
}

export function main(argv, io) {
  const fail = message => {
    io.stderr.write(`Error: ${message} Use --help for usage.\n`);
    return 2;
  };
  const [command, rawValue, fromName, toName] = argv;
  if (command === undefined) return fail('Missing command.');
  if (['--help', '-h', '--version', 'units'].includes(command)) {
    if (argv.length !== 1) return fail(`Unexpected extra argument "${argv[1]}" for ${command}.`);
    if (command === '--help' || command === '-h') io.stdout.write(help);
    else if (command === '--version') io.stdout.write('1.0.0\n');
    else {
      for (const dimension of ['length', 'mass', 'temperature']) {
        io.stdout.write(`${dimension}: ${units.filter(unit => unit.dimension === dimension).map(unit => unit.symbol).join(' ')}\n`);
      }
    }
    return 0;
  }
  if (command !== 'convert') {
    return fail(command.startsWith('-') ? unexpected(command) : `Unknown command "${command}".`);
  }
  const unknownFlag = argv.slice(1).find(argument => argument.startsWith('--') && argument !== '--precision');
  if (unknownFlag !== undefined) return fail(unexpected(unknownFlag));
  if (argv.slice(1, 4).includes('--precision')) return fail('Misplaced --precision flag; put it after value, source and target arguments.');
  if (rawValue === undefined) return fail('Missing value argument.');
  if (fromName === undefined) return fail('Missing source unit (from).');
  if (toName === undefined) return fail('Missing target unit (to).');
  let precision = 2;
  if (argv.length > 4) {
    if (argv[4] !== '--precision') return fail(unexpected(argv[4]));
    if (argv[5] === undefined) return fail('Missing precision value after --precision.');
    if (argv.length > 6) return fail(`Unexpected extra argument "${argv[6]}".`);
    if (argv[5].trim() !== argv[5] || !/^\d+$/.test(argv[5]) || Number(argv[5]) > 6) {
      return fail(`Invalid precision "${argv[5]}"; expected an integer from 0 to 6.`);
    }
    precision = Number(argv[5]);
  }
  if (rawValue.trim() !== rawValue || !decimal.test(rawValue) || !Number.isFinite(Number(rawValue))) {
    return fail(`Invalid value "${rawValue}"; expected a finite decimal number.`);
  }
  if (fromName.startsWith('-')) return fail(unexpected(fromName));
  if (toName.startsWith('-')) return fail(unexpected(toName));
  const from = units.find(unit => unit.symbol === fromName.toLowerCase());
  const to = units.find(unit => unit.symbol === toName.toLowerCase());
  if (!from) return fail(unknownUnit(fromName));
  if (!to) return fail(unknownUnit(toName));
  if (from.dimension !== to.dimension) {
    return fail(`Cannot convert "${fromName}" to "${toName}": incompatible dimensions (${from.dimension} and ${to.dimension}).`);
  }
  const converted = convert(Number(rawValue), from, to);
  io.stdout.write(`${converted.toFixed(precision)} ${to.symbol}\n`);
  return 0;
}
