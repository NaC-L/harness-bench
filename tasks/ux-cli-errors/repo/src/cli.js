import { units, convert } from './units.js';

export function main(argv, io) {
  const [command, rawValue, fromName, toName] = argv;
  if (command === '--help') {
    io.stderr.write('convert VALUE FROM TO\n');
    return 1;
  }
  if (command === '--version') {
    io.stdout.write('1.0.0\n');
    return 0;
  }
  if (command === 'units') {
    for (const dimension of ['length', 'mass', 'temperature']) {
      io.stdout.write(`${dimension}: ${units.filter(unit => unit.dimension === dimension).map(unit => unit.symbol).join(' ')}\n`);
    }
    return 0;
  }
  if (command !== 'convert') {
    throw new Error(`Unknown command: ${command}`);
  }
  const value = Number.parseFloat(rawValue);
  if (Number.isNaN(value)) {
    io.stdout.write(`Bad value: ${rawValue}\n`);
    return 1;
  }
  const from = units.find(unit => unit.symbol === fromName);
  const to = units.find(unit => unit.symbol === toName);
  if (!from || !to) {
    throw new Error(`Unknown unit: ${!from ? fromName : toName}`);
  }
  const optionIndex = argv.indexOf('--precision');
  const precision = optionIndex === -1 ? 2 : Number.parseInt(argv[optionIndex + 1], 10) || 2;
  const converted = convert(from.dimension === 'temperature' ? Math.abs(value) : value, from, to);
  io.stdout.write(`${converted.toFixed(precision)} ${to.symbol}\n`);
  return 0;
}
