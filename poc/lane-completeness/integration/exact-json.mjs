// Node >=22: preserve integer tokens that exceed binary64's exact range.
// Safe integers remain Numbers for indexes/timers; large integers become BigInts.
export function parse(text) {
  return JSON.parse(String(text), (_key, value, context) => {
    if (typeof value !== 'number') return value;
    if (!Number.isFinite(value)) throw new Error('non-finite JSON number');
    if (/^-?\d+$/.test(context.source) && !Number.isSafeInteger(value))
      return BigInt(context.source);
    return value;
  });
}
export function stringify(value, replacer = null, space = undefined) {
  if (replacer !== null) throw new Error('custom replacer unsupported');
  return JSON.stringify(value, (_key, v) => {
    if (typeof v === 'bigint') return JSON.rawJSON(v.toString());
    if (typeof v === 'number' && (!Number.isFinite(v) || (Number.isInteger(v) && !Number.isSafeInteger(v))))
      throw new Error('unsafe Number: recover the original integer token before serializing');
    return v;
  }, space);
}
export function sompi(value) {
  if (typeof value === 'number' && !Number.isSafeInteger(value)) throw new Error('unsafe sompi Number');
  if (!['number', 'bigint', 'string'].includes(typeof value) || !/^\d+$/.test(String(value)))
    throw new Error('sompi must be an unsigned integer');
  const amount = BigInt(value);
  if (amount > 0xffffffffffffffffn) throw new Error('sompi exceeds u64');
  return amount;
}
