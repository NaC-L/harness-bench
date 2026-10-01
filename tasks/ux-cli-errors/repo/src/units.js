export const units = [
  { symbol: 'm', dimension: 'length', factor: 1 },
  { symbol: 'km', dimension: 'length', factor: 1000 },
  { symbol: 'cm', dimension: 'length', factor: 0.01 },
  { symbol: 'mm', dimension: 'length', factor: 0.001 },
  { symbol: 'mi', dimension: 'length', factor: 1609.344 },
  { symbol: 'ft', dimension: 'length', factor: 0.3048 },
  { symbol: 'in', dimension: 'length', factor: 0.0254 },
  { symbol: 'kg', dimension: 'mass', factor: 1000 },
  { symbol: 'g', dimension: 'mass', factor: 1 },
  { symbol: 'lb', dimension: 'mass', factor: 453.59237 },
  { symbol: 'oz', dimension: 'mass', factor: 28.349523125 },
  { symbol: 'c', dimension: 'temperature' },
  { symbol: 'f', dimension: 'temperature' },
  { symbol: 'k', dimension: 'temperature' },
];

export function convert(value, from, to) {
  if (from.dimension !== to.dimension) {
    throw new Error(`Cannot convert ${from.symbol} to ${to.symbol}: incompatible dimensions`);
  }
  if (from.dimension !== 'temperature') {
    return value * from.factor / to.factor;
  }
  const celsius = from.symbol === 'f' ? (value - 32) * 5 / 9
    : from.symbol === 'k' ? value - 273.15 : value;
  return to.symbol === 'f' ? celsius * 9 / 5 + 32
    : to.symbol === 'k' ? celsius + 273.15 : celsius;
}
